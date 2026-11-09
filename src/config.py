"""Đọc cấu hình ứng dụng từ biến môi trường hoặc Streamlit secrets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _streamlit_secret(name: str) -> Any | None:
    """Đọc một giá trị từ Streamlit secrets nếu ứng dụng đang có cấu hình đó."""
    try:
        import streamlit as st

        return st.secrets.get(name)
    except (ImportError, RuntimeError, FileNotFoundError):
        return None


def get_setting(name: str, default: str | None = None) -> str | None:
    """Lấy cấu hình ưu tiên biến môi trường, sau đó đến Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    secret = _streamlit_secret(name)
    return str(secret) if secret not in (None, "") else default


def get_credentials_path() -> Path:
    """Trả về đường dẫn credentials JSON đã cấu hình hoặc vị trí mặc định."""
    configured = get_setting("GOOGLE_APPLICATION_CREDENTIALS")
    path = Path(configured) if configured else PROJECT_ROOT / "credentials" / "service-account.json"
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def get_spreadsheet_id() -> str:
    """Lấy Spreadsheet ID; dừng với hướng dẫn rõ nếu chưa cấu hình."""
    value = get_setting("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not value:
        raise RuntimeError(
            "Chưa cấu hình GOOGLE_SHEETS_SPREADSHEET_ID. "
            "Hãy đặt biến môi trường hoặc thêm khóa này vào Streamlit secrets."
        )
    return value
