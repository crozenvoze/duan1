"""Lấy báo cáo Vnstock dạng thô và tính chỉ số từ dữ liệu đã ánh xạ VAS."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
import re
from typing import Any

import pandas as pd

from src.metrics import (
    asset_turnover,
    cash_conversion,
    debt_to_equity,
    dupont_roe,
    net_margin,
    roa,
)

LEGACY_FUNDAMENTALS_HEADERS = [
    "ticker", "period", "revenue", "gross_profit", "net_income",
    "assets_beginning", "assets_ending", "equity_beginning", "equity_ending",
    "total_borrowings", "operating_cash_flow", "roe", "roa", "net_margin",
    "asset_turnover", "equity_multiplier", "debt_to_equity", "cash_conversion",
    "updated_at",
]
FUNDAMENTALS_HEADERS = LEGACY_FUNDAMENTALS_HEADERS + ["industry", "receivables_ending"]


def cash_conversion_quality_status(
    cash_conversion_values: list[Any],
    net_income_values: list[Any],
    *,
    threshold: float = 1.0,
    consecutive_periods: int = 2,
) -> tuple[str, str]:
    """Đánh dấu CFO/NI thấp kéo dài; đây là cảnh báo theo dõi, không kết luận.

    Chỉ đánh giá kỳ có lợi nhuận ròng dương. Ngưỡng mặc định CFO/NI < 1 trong
    hai kỳ liên tiếp là quy ước cảnh báo bảo thủ để người dùng xem lại BCTC.
    """
    if len(cash_conversion_values) != len(net_income_values):
        raise ValueError("Số kỳ cash conversion và lợi nhuận ròng phải bằng nhau.")
    if threshold <= 0 or consecutive_periods < 1:
        raise ValueError("Ngưỡng phải dương và số kỳ liên tiếp phải từ 1 trở lên.")

    def finite_number(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None

    valid_periods: list[tuple[float, float] | None] = []
    for cash_ratio, income in zip(cash_conversion_values, net_income_values):
        ratio_value, income_value = finite_number(cash_ratio), finite_number(income)
        if ratio_value is None or income_value is None or income_value <= 0:
            valid_periods.append(None)
        else:
            valid_periods.append((ratio_value, income_value))

    if not valid_periods or valid_periods[-1] is None:
        return "unknown", "Chưa đủ dữ liệu để đánh giá CFO/NI ở kỳ mới nhất (cần lợi nhuận ròng dương)."

    latest_ratio = valid_periods[-1][0]
    if latest_ratio >= threshold:
        return "ok", f"CFO/NI kỳ mới nhất là {latest_ratio:.2f}x; chưa chạm ngưỡng theo dõi {threshold:.2f}x."

    streak = 0
    for period in reversed(valid_periods):
        if period is None or period[0] >= threshold:
            break
        streak += 1
    if streak >= consecutive_periods:
        return (
            "warning",
            f"CFO/NI dưới {threshold:.2f}x trong {streak} kỳ liên tiếp; nên xem lại dòng tiền và thuyết minh.",
        )
    return "info", f"CFO/NI kỳ mới nhất dưới {threshold:.2f}x; một kỳ riêng lẻ chưa đủ kết luận, hãy tiếp tục theo dõi."


def _period_year_and_quarter(value: Any) -> tuple[int, int | None] | None:
    """Phân tích kỳ dạng YYYY, YYYYFY hoặc YYYYQn/YYY-Qn để so cùng kỳ năm trước."""
    text = str(value or "").strip().upper().replace(" ", "")
    match = re.fullmatch(r"(\d{4})(?:[-_/]?Q([1-4]))?", text)
    if match:
        return int(match.group(1)), int(match.group(2)) if match.group(2) else None
    match = re.fullmatch(r"(\d{4})[-_/]?FY", text)
    if match:
        return int(match.group(1)), None
    return None


def receivables_growth_status(records: list[dict[str, Any]]) -> tuple[str, str]:
    """So tăng trưởng phải thu với doanh thu ở cùng kỳ năm trước.

    Chỉ chạy khi người dùng đã ánh xạ `revenue` nhất quán theo cùng kỳ báo cáo
    và `receivables_ending` là tổng khoản phải thu cuối kỳ. Tỷ lệ tăng trưởng
    = số kỳ này / số cùng kỳ năm trước - 1.
    """
    by_period: dict[tuple[int, int | None], dict[str, Any]] = {}
    for record in records:
        period = _period_year_and_quarter(record.get("period"))
        if period is not None:
            by_period[period] = record
    if not by_period:
        return "unknown", "Không nhận diện được kỳ báo cáo để so khoản phải thu cùng kỳ năm trước."

    current_period = max(by_period, key=lambda period: (period[0], period[1] or 5))
    current = by_period[current_period]
    comparable = by_period.get((current_period[0] - 1, current_period[1]))
    if comparable is None:
        return "unknown", "Chưa có dữ liệu cùng kỳ năm trước để so khoản phải thu với doanh thu."

    def finite_number(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None

    revenue_now = finite_number(current.get("revenue"))
    revenue_before = finite_number(comparable.get("revenue"))
    receivables_now = finite_number(current.get("receivables_ending"))
    receivables_before = finite_number(comparable.get("receivables_ending"))
    values = (revenue_now, revenue_before, receivables_now, receivables_before)
    if any(value is None for value in values) or revenue_before == 0 or receivables_before <= 0:
        return "unknown", "Thiếu doanh thu hoặc số dư phải thu hợp lệ ở hai kỳ so sánh."

    revenue_growth = revenue_now / revenue_before - 1
    receivables_growth = receivables_now / receivables_before - 1
    if receivables_growth > revenue_growth:
        return (
            "warning",
            f"Phải thu tăng {receivables_growth:.2%}, nhanh hơn doanh thu {revenue_growth:.2%} so với cùng kỳ; cần xem thuyết minh và tuổi nợ.",
        )
    return (
        "ok",
        f"Phải thu tăng {receivables_growth:.2%}, không nhanh hơn doanh thu {revenue_growth:.2%} so với cùng kỳ.",
    )


def fetch_raw_statements(symbol: str, period: str = "quarter") -> dict[str, pd.DataFrame]:
    """Lấy BCTC thô từ Vnstock Unified UI; không tự đoán ánh xạ nhãn VAS.

    Đầu vào: mã cổ phiếu ba ký tự và kỳ 'quarter' hoặc 'year'.
    Đầu ra: income_statement, balance_sheet, cash_flow DataFrame nguyên bản.
    Cột/dòng báo cáo có thể đổi theo nguồn; cần kiểm tra raw trước khi ánh xạ.
    """
    ticker = symbol.strip().upper()
    if len(ticker) != 3 or not ticker.isalpha():
        raise ValueError("Mã cổ phiếu phải gồm đúng ba chữ cái.")
    if period not in {"quarter", "year"}:
        raise ValueError("period chỉ nhận 'quarter' hoặc 'year'.")
    try:
        from vnstock import Fundamental
    except ImportError as exc:
        raise RuntimeError(
            "Chưa cài Vnstock. Với v6, tạo môi trường riêng theo hướng dẫn chính thức tại "
            "https://www.vnstocks.com/docs/vnstock/v6/cai-dat; API BCTC hiện cần nguồn FHSC."
        ) from exc

    from src.config import get_setting

    fundamental = Fundamental()
    source = get_setting("VNSTOCK_FUNDAMENTAL_SOURCE", "fhsc")
    equity = getattr(fundamental, "equity", None)
    instrument = equity(ticker) if callable(equity) else None
    outputs: dict[str, pd.DataFrame] = {}
    for name in ("income_statement", "balance_sheet", "cash_flow"):
        try:
            if instrument is not None:
                # Vnstock v6: attach ticker first; each statement requires an explicit source.
                outputs[name] = pd.DataFrame(getattr(instrument, name)(period=period, source=source))
            else:
                # Vnstock v5 compatibility; keep raw labels for manual VAS review.
                getter = getattr(equity, name)
                outputs[name] = pd.DataFrame(getter(symbol=ticker, period=period))
        except Exception as exc:
            raise RuntimeError(f"Không lấy được {name} cho {ticker}: {exc}") from exc
    return outputs


def calculate_fundamental_row(row: dict[str, Any]) -> dict[str, Any]:
    """Tính DuPont và chỉ số từ một dòng đã chuẩn hóa theo schema nội bộ.

    Nguồn phải ánh xạ rõ doanh thu thuần, lợi nhuận ròng, tài sản/vốn chủ đầu
    và cuối kỳ, nợ vay, CFO. Không dùng tổng nợ phải trả thay nợ vay.
    """
    ticker = str(row.get("ticker", "")).strip().upper()
    period = str(row.get("period", "")).strip()
    required = [
        "revenue", "net_income", "assets_beginning", "assets_ending",
        "equity_beginning", "equity_ending", "total_borrowings", "operating_cash_flow",
    ]
    missing = [key for key in required if row.get(key) in (None, "")]
    if missing:
        raise ValueError(f"Thiếu trường đã ánh xạ cho {ticker} {period}: {', '.join(missing)}")
    values = {key: float(row[key]) for key in required}
    dupont = dupont_roe(
        values["net_income"], values["revenue"], values["assets_beginning"],
        values["assets_ending"], values["equity_beginning"], values["equity_ending"],
    )
    return {
        **row,
        **dupont,
        # Schema lưu trữ dùng tên roe; giữ ROE trực tiếp để dễ đối chiếu với VAS.
        "roe": dupont["roe_direct"],
        "roa": roa(values["net_income"], values["assets_beginning"], values["assets_ending"]),
        "net_margin": net_margin(values["net_income"], values["revenue"]),
        "asset_turnover": asset_turnover(values["revenue"], values["assets_beginning"], values["assets_ending"]),
        "debt_to_equity": debt_to_equity(values["total_borrowings"], values["equity_ending"]),
        "cash_conversion": cash_conversion(values["operating_cash_flow"], values["net_income"]),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_fundamentals(records: list[dict[str, Any]]) -> int:
    """Thêm các dòng chỉ số đã ánh xạ vào tab Fundamentals mà không xóa lịch sử."""
    if not records:
        return 0
    from src.sheets import open_spreadsheet

    sheet = open_spreadsheet()
    try:
        worksheet = sheet.worksheet("Fundamentals")
    except Exception:
        worksheet = sheet.add_worksheet(title="Fundamentals", rows=1000, cols=len(FUNDAMENTALS_HEADERS))
    existing = worksheet.get_all_values()
    if not existing:
        worksheet.append_row(FUNDAMENTALS_HEADERS)
        existing = [FUNDAMENTALS_HEADERS]
    headers = existing[0]
    if headers == LEGACY_FUNDAMENTALS_HEADERS:
        from gspread.utils import rowcol_to_a1

        last_column = rowcol_to_a1(1, len(FUNDAMENTALS_HEADERS))
        worksheet.update(
            range_name=f"A1:{last_column}",
            values=[FUNDAMENTALS_HEADERS],
        )
        headers = FUNDAMENTALS_HEADERS
    if headers != FUNDAMENTALS_HEADERS:
        raise RuntimeError(
            "Header tab Fundamentals chưa khớp schema hiện tại. Hãy lưu bản sao tab trước khi "
            "đổi header để giữ nguyên dữ liệu cũ."
        )
    known = {(row[0], row[1]) for row in existing[1:] if len(row) > 1}
    new_records = [r for r in records if (str(r.get("ticker", "")), str(r.get("period", ""))) not in known]
    if not new_records:
        return 0
    values = [[record.get(header, "") for header in FUNDAMENTALS_HEADERS] for record in new_records]
    worksheet.append_rows(values, value_input_option="USER_ENTERED")
    return len(values)


def read_fundamentals() -> pd.DataFrame:
    """Đọc tab Fundamentals thành bảng; trả bảng rỗng nếu tab chưa tồn tại."""
    from src.sheets import read_worksheet

    try:
        rows = read_worksheet("Fundamentals")
    except RuntimeError:
        return pd.DataFrame(columns=FUNDAMENTALS_HEADERS)
    if not rows:
        return pd.DataFrame(columns=FUNDAMENTALS_HEADERS)
    return pd.DataFrame(rows[1:], columns=rows[0])
