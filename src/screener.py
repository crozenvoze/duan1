"""Lọc và xếp hạng cổ phiếu trên bảng chỉ số đã chuẩn hóa."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any

import pandas as pd

REQUIRED_SCREEN_COLUMNS = {
    "ticker", "pe", "pb", "roe", "revenue_growth", "eps_growth",
    "debt_to_equity", "avg_value_traded", "market_cap", "industry",
}
SCREEN_NUMERIC_COLUMNS = (
    "pe", "pb", "roe", "revenue_growth", "eps_growth", "debt_to_equity",
    "avg_value_traded", "market_cap", "momentum",
)


def normalize_screener_data(data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa một snapshot Screener_Data hoặc CSV trước khi lọc/xếp hạng.

    Đầu vào cần một hàng cho mỗi mã, đủ các cột bắt buộc trong
    ``REQUIRED_SCREEN_COLUMNS``; ``momentum`` là tùy chọn. Ô số được để trống
    khi nguồn không có dữ liệu, nhưng giá trị chữ không hợp lệ và mã trùng bị từ
    chối. Đầu ra giữ các cột bổ sung để không làm mất metadata của người dùng.
    Tỷ lệ ROE/tăng trưởng dùng dạng thập phân (0.15 = 15%).
    """
    if not isinstance(data, pd.DataFrame):
        raise ValueError("Dữ liệu Screener phải là một bảng CSV hoặc DataFrame.")
    frame = data.copy()
    normalized_columns = [str(column).strip().lower() for column in frame.columns]
    if len(set(normalized_columns)) != len(normalized_columns):
        raise ValueError("Tên cột bị trùng sau khi chuẩn hóa chữ hoa/thường và khoảng trắng.")
    frame.columns = normalized_columns
    missing = REQUIRED_SCREEN_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc: {', '.join(sorted(missing))}.")
    if frame.empty:
        raise ValueError("File không có dòng dữ liệu cổ phiếu.")

    frame["ticker"] = frame["ticker"].fillna("").astype(str).str.strip().str.upper()
    invalid_tickers = [
        f"dòng {index + 2}: {ticker or '(trống)'}"
        for index, ticker in enumerate(frame["ticker"].tolist())
        if not re.fullmatch(r"[A-Z]{3}", ticker)
    ]
    if invalid_tickers:
        raise ValueError("Mã cổ phiếu phải gồm đúng 3 chữ cái; lỗi ở " + ", ".join(invalid_tickers[:5]) + ".")
    duplicate_tickers = frame.loc[frame["ticker"].duplicated(keep=False), "ticker"].drop_duplicates().tolist()
    if duplicate_tickers:
        raise ValueError("Mỗi snapshot chỉ được có một dòng cho mỗi mã; mã trùng: " + ", ".join(duplicate_tickers[:10]) + ".")

    if "momentum" not in frame.columns:
        frame["momentum"] = float("nan")
    for column in SCREEN_NUMERIC_COLUMNS:
        original = frame[column]
        converted = pd.to_numeric(original, errors="coerce")
        invalid = original.notna() & original.astype(str).str.strip().ne("") & converted.isna()
        invalid |= converted.notna() & ~converted.map(lambda value: pd.notna(value) and abs(float(value)) != float("inf"))
        if invalid.any():
            rows = [str(index + 2) for index in frame.index[invalid][:5]]
            raise ValueError(f"Cột {column} có giá trị không phải số hữu hạn tại dòng " + ", ".join(rows) + ".")
        frame[column] = converted.astype(float)

    frame["industry"] = frame["industry"].fillna("").astype(str).str.strip()
    return frame.reset_index(drop=True)


def filter_stocks(data: pd.DataFrame, criteria: dict[str, Any]) -> pd.DataFrame:
    """Lọc theo khoảng chỉ tiêu; tiêu chí None được bỏ qua."""
    missing = REQUIRED_SCREEN_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Bảng screener thiếu cột: {', '.join(sorted(missing))}")
    result = data.copy()
    numeric_filters = {
        "pe": ("pe_min", "pe_max"),
        "pb": ("pb_min", "pb_max"),
        "roe": ("roe_min", "roe_max"),
        "revenue_growth": ("revenue_growth_min", "revenue_growth_max"),
        "eps_growth": ("eps_growth_min", "eps_growth_max"),
        "debt_to_equity": ("debt_to_equity_min", "debt_to_equity_max"),
        "avg_value_traded": ("avg_value_traded_min", "avg_value_traded_max"),
        "market_cap": ("market_cap_min", "market_cap_max"),
    }
    for column, (minimum_key, maximum_key) in numeric_filters.items():
        result[column] = pd.to_numeric(result[column], errors="coerce")
        minimum, maximum = criteria.get(minimum_key), criteria.get(maximum_key)
        if minimum is not None:
            result = result[result[column] >= minimum]
        if maximum is not None:
            result = result[result[column] <= maximum]
    industries = criteria.get("industries")
    if industries:
        result = result[result["industry"].isin(industries)]
    return result.reset_index(drop=True)


def rank_stocks(data: pd.DataFrame) -> pd.DataFrame:
    """Xếp hạng value/quality/growth/momentum bằng percentile rank trung bình.

    P/E và P/B thấp hơn được ưu tiên; ROE, doanh thu/EPS growth, momentum cao
    hơn được ưu tiên; nợ/vốn chủ thấp hơn được ưu tiên. Percentile hạn chế độ
    nhạy với đơn vị và outlier, nhưng không khắc phục sai lệch dữ liệu nguồn.
    """
    frame = data.copy()
    factors = {
        "value_score": {"pe": False, "pb": False},
        "quality_score": {"roe": True, "debt_to_equity": False},
        "growth_score": {"revenue_growth": True, "eps_growth": True},
        "momentum_score": {"momentum": True},
    }
    scores: list[str] = []
    for group, directions in factors.items():
        component_scores = []
        for column, higher_is_better in directions.items():
            if column not in frame.columns:
                continue
            numeric = pd.to_numeric(frame[column], errors="coerce")
            if column in {"pe", "pb"}:
                # P/E <= 0 do doanh nghiệp lỗ và P/B <= 0 do vốn chủ âm không
                # biểu thị một mức định giá thấp hơn; loại khỏi điểm value.
                numeric = numeric.where(numeric > 0)
            # ascending=True memberi percentile cao nhất cho giá trị lớn nhất;
            # với chỉ số thấp là tốt, đảo chiều xếp hạng.
            component_scores.append(numeric.rank(pct=True, ascending=higher_is_better))
        if component_scores:
            frame[group] = pd.concat(component_scores, axis=1).mean(axis=1)
            scores.append(group)
    if not scores:
        raise ValueError("Không có chỉ tiêu nào để xếp hạng.")
    frame["composite_score"] = frame[scores].mean(axis=1)
    return frame.sort_values("composite_score", ascending=False, na_position="last").reset_index(drop=True)


def save_favorite_filter(name: str, criteria: dict[str, Any]) -> None:
    """Ghi bộ lọc vào tab Saved_Filters, tạo tab/header khi chưa có.

    Đầu vào là tên bộ lọc và tiêu chí đã chuẩn hóa từ giao diện. Đầu ra là
    một dòng append-only gồm tên, JSON tiêu chí và thời điểm UTC; không thay
    thế các bộ lọc đã lưu. Dùng RAW để nội dung người dùng không bị hiểu là công thức.
    """
    filter_name = str(name or "").strip()
    if not filter_name:
        raise ValueError("Tên bộ lọc không được để trống.")
    if len(filter_name) > 80:
        raise ValueError("Tên bộ lọc không được dài quá 80 ký tự.")
    if not isinstance(criteria, dict):
        raise ValueError("Tiêu chí bộ lọc phải là một đối tượng.")

    from gspread.exceptions import WorksheetNotFound
    from src.sheets import open_spreadsheet

    spreadsheet = open_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet("Saved_Filters")
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Saved_Filters", rows=500, cols=3)

    headers = ["name", "criteria_json", "saved_at"]
    existing = worksheet.get_all_values()
    if not existing:
        worksheet.append_row(headers, value_input_option="RAW")
    elif existing[0][:len(headers)] != headers:
        raise RuntimeError("Header tab Saved_Filters không đúng; không ghi đè dữ liệu hiện có.")
    worksheet.append_row(
        [
            filter_name,
            json.dumps(criteria, ensure_ascii=False, allow_nan=False),
            datetime.now(timezone.utc).isoformat(),
        ],
        value_input_option="RAW",
    )
