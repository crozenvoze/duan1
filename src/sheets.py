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


def read_trades() -> list[list[str]]:
    """Đọc dữ liệu dạng hàng từ tab Trades; hàng đầu tiên thường là tiêu đề."""
    try:
        worksheet = open_spreadsheet().worksheet("Trades")
        return worksheet.get_all_values()
    except gspread.exceptions.WorksheetNotFound as exc:
        raise RuntimeError("Không tìm thấy tab 'Trades' trong Google Sheet.") from exc


def main() -> None:
    """Kiểm tra kết nối và in tiêu đề cùng tối đa năm hàng mẫu."""
    rows = read_trades()
    if not rows:
        print("Kết nối thành công. Tab Trades hiện chưa có dữ liệu.")
        return
    print(f"Kết nối thành công. Số hàng đọc được: {len(rows)}")
    for row in rows[:6]:
        print(" | ".join(row))


if __name__ == "__main__":
    main()
