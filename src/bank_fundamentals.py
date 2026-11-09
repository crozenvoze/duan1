"""Lưu lịch sử chỉ số ngân hàng đã nhập và đối chiếu thủ công."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

BANK_FUNDAMENTALS_HEADERS = [
    "ticker", "period", "net_interest_income_ttm", "average_interest_earning_assets",
    "operating_expenses", "operating_income", "non_performing_loans",
    "gross_customer_loans", "demand_deposits", "margin_escrow_deposits",
    "dedicated_deposits", "customer_deposits", "credit_loss_provision_ttm",
    "average_gross_customer_loans", "nim", "cir", "npl", "ldr", "casa",
    "provision_to_loans", "source_note", "saved_at",
]


def write_bank_fundamental(record: dict[str, Any]) -> None:
    """Thêm một bản ghi ngân hàng vào tab riêng; mỗi lần lưu giữ một phiên bản."""
    ticker = str(record.get("ticker", "")).strip().upper()
    period = str(record.get("period", "")).strip()
    if len(ticker) != 3 or not ticker.isalpha():
        raise ValueError("Mã ngân hàng phải gồm đúng ba chữ cái.")
    if not period:
        raise ValueError("Cần nhập kỳ báo cáo trước khi lưu.")

    from gspread.exceptions import WorksheetNotFound

    from src.sheets import open_spreadsheet

    spreadsheet = open_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet("Bank_Fundamentals")
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title="Bank_Fundamentals",
            rows=1000,
            cols=len(BANK_FUNDAMENTALS_HEADERS),
        )
    values = worksheet.get_all_values()
    if not values:
        worksheet.update(
            range_name=f"A1:V1",
            values=[BANK_FUNDAMENTALS_HEADERS],
        )
    elif [str(cell).strip().lower() for cell in values[0]] != BANK_FUNDAMENTALS_HEADERS:
        raise RuntimeError(
            "Tab Bank_Fundamentals có header khác schema; hãy sao lưu tab trước khi sửa header."
        )

    row = {**record, "ticker": ticker, "period": period}
    row["saved_at"] = datetime.now(timezone.utc).isoformat()
    worksheet.append_rows(
        [[row.get(header, "") if row.get(header) is not None else "" for header in BANK_FUNDAMENTALS_HEADERS]],
        value_input_option="USER_ENTERED",
    )


def read_bank_fundamentals() -> pd.DataFrame:
    """Đọc lịch sử ngân hàng; trả bảng rỗng nếu tab chưa được tạo."""
    from src.sheets import open_spreadsheet
    from gspread.exceptions import WorksheetNotFound

    try:
        rows = open_spreadsheet().worksheet("Bank_Fundamentals").get_all_values()
    except WorksheetNotFound:
        return pd.DataFrame(columns=BANK_FUNDAMENTALS_HEADERS)
    if not rows:
        return pd.DataFrame(columns=BANK_FUNDAMENTALS_HEADERS)
    if [str(cell).strip().lower() for cell in rows[0]] != BANK_FUNDAMENTALS_HEADERS:
        raise RuntimeError("Header tab Bank_Fundamentals chưa khớp schema hiện tại.")
    return pd.DataFrame(rows[1:], columns=rows[0])
