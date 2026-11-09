"""Kết nối Google Sheets bằng service account và kiểm tra tab Trades."""

from __future__ import annotations

import json
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from src.config import get_credentials_path, get_setting, get_spreadsheet_id

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _create_client() -> gspread.Client:
    """Tạo client Google Sheets từ secrets hoặc file credentials cục bộ."""
    inline_credentials = get_setting("GOOGLE_SERVICE_ACCOUNT_JSON")
    if inline_credentials:
        try:
            credentials_info: dict[str, Any] = json.loads(inline_credentials)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON không phải JSON hợp lệ.") from exc
        credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
    else:
        path = get_credentials_path()
        if not path.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy credentials tại {path}. Hãy đặt file service account "
                "ở credentials/service-account.json hoặc cấu hình secrets."
            )
        credentials = Credentials.from_service_account_file(str(path), scopes=SCOPES)
    return gspread.authorize(credentials)


def open_spreadsheet() -> gspread.Spreadsheet:
    """Mở Google Sheet theo ID cấu hình và trả về workbook."""
    try:
        return _create_client().open_by_key(get_spreadsheet_id())
    except gspread.exceptions.GSpreadException as exc:
        raise RuntimeError(
            "Không mở được Google Sheet. Hãy kiểm tra Spreadsheet ID, quyền chia sẻ "
            "cho client_email của service account và kết nối mạng."
        ) from exc


def read_trades() -> list[list[Any]]:
    """Đọc Trades dạng thô để ngày giờ trả về serial ổn định theo vùng Sheet."""
    try:
        worksheet = open_spreadsheet().worksheet("Trades")
        return worksheet.get_all_values(
            value_render_option="UNFORMATTED_VALUE",
            date_time_render_option="SERIAL_NUMBER",
        )
    except gspread.exceptions.WorksheetNotFound as exc:
        raise RuntimeError("Không tìm thấy tab 'Trades' trong Google Sheet.") from exc


def read_worksheet(title: str) -> list[list[str]]:
    """Đọc dữ liệu dạng hàng từ một tab trong Google Sheet."""
    try:
        worksheet = open_spreadsheet().worksheet(title)
        return worksheet.get_all_values()
    except gspread.exceptions.WorksheetNotFound as exc:
        raise RuntimeError(f"Không tìm thấy tab '{title}' trong Google Sheet.") from exc


def upsert_prices_cache(records: list[dict[str, Any]]) -> tuple[int, int]:
    """Thêm/cập nhật OHLCV theo khóa (ticker, date) vào Prices_Cache.

    Đầu vào là các bản ghi đã chuẩn hóa gồm ticker, date, open, high, low,
    close, volume. Trả về (số dòng thêm, số dòng cập nhật); không đụng tới
    các tab Trades hoặc Watchlist.
    """
    if not records:
        return 0, 0

    headers = ["ticker", "date", "open", "high", "low", "close", "volume"]
    spreadsheet = open_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet("Prices_Cache")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Prices_Cache", rows=1000, cols=len(headers))

    values = worksheet.get_all_values()
    if not values:
        worksheet.update(range_name="A1:G1", values=[headers])
        values = [headers]
    actual_headers = [str(cell).strip().lower() for cell in values[0]]
    if actual_headers != headers:
        raise RuntimeError(
            "Tab Prices_Cache phải có đúng thứ tự cột: " + ", ".join(headers)
        )

    row_by_key: dict[tuple[str, str], int] = {}
    for row_number, row in enumerate(values[1:], start=2):
        if len(row) >= 2 and row[0].strip() and row[1].strip():
            row_by_key[(row[0].strip().upper(), row[1].strip()[:10])] = row_number

    additions: list[list[str]] = []
    updates: list[dict[str, Any]] = []
    for record in records:
        ticker = str(record["ticker"]).strip().upper()
        date_value = str(record["date"])[:10]
        row = [ticker, date_value] + [str(record[name]) for name in headers[2:]]
        key = (ticker, date_value)
        row_number = row_by_key.get(key)
        if row_number is None:
            additions.append(row)
        else:
            old_row = values[row_number - 1]
            normalized_old = old_row[:len(headers)] + [""] * max(0, len(headers) - len(old_row))
            if normalized_old != row:
                updates.append({"range": f"A{row_number}:G{row_number}", "values": [row]})

    if updates:
        worksheet.batch_update(updates, value_input_option="USER_ENTERED")
    if additions:
        worksheet.append_rows(additions, value_input_option="USER_ENTERED")
    return len(additions), len(updates)


def main() -> None:
    """Kiểm tra kết nối mà không in dữ liệu giao dịch riêng tư ra terminal."""
    rows = read_trades()
    if not rows:
        print("Connection successful. The Trades tab is empty.")
        return
    print(f"Connection successful. Rows read: {len(rows) - 1 if rows else 0}")
    print("Columns: " + ", ".join(rows[0]))


if __name__ == "__main__":
    main()
