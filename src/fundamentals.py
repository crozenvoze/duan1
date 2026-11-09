"""Lấy báo cáo Vnstock dạng thô và tính chỉ số từ dữ liệu đã ánh xạ VAS."""

from __future__ import annotations

from datetime import datetime, timezone
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

FUNDAMENTALS_HEADERS = [
    "ticker", "period", "revenue", "gross_profit", "net_income",
    "assets_beginning", "assets_ending", "equity_beginning", "equity_ending",
    "total_borrowings", "operating_cash_flow", "roe", "roa", "net_margin",
    "asset_turnover", "equity_multiplier", "debt_to_equity", "cash_conversion",
    "updated_at",
]


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
            "Vnstock chưa được cài. API thế hệ 5 hiện dùng Unified UI; xem hướng dẫn chính thức "
            "tại https://vnstocks.com/download và kiểm tra điều kiện sử dụng Community."
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
