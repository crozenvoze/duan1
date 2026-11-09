"""Tạo cấu hình cục bộ cho form mà không đưa token vào mã nguồn được theo dõi."""

from __future__ import annotations

import getpass
import json
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "web_form" / "config.local.js"
WEB_APP_URL_PATTERN = re.compile(r"^https://script\.google\.com/macros/s/[^/]+/exec$")


def render_form_config(apps_script_url: str, form_token: str) -> str:
    """Xác thực và mã hóa URL/token thành JavaScript hợp lệ cho trình duyệt."""
    url = apps_script_url.strip()
    if not WEB_APP_URL_PATTERN.fullmatch(url):
        raise ValueError("URL phải thuộc script.google.com và kết thúc bằng /exec.")
    if len(form_token) < 32:
        raise ValueError("FORM_TOKEN phải dài ít nhất 32 ký tự.")
    return (
        "window.APP_CONFIG = {\n"
        f"  appsScriptUrl: {json.dumps(url)},\n"
        f"  formToken: {json.dumps(form_token)}\n"
        "};\n"
    )


def configure_form() -> Path:
    """Nhập cấu hình cục bộ; token được nhận dạng ẩn và không in ra màn hình."""
    print("Tạo cấu hình riêng cho web_form; token không được hiển thị khi nhập.")
    url = input("Dán URL Web app kết thúc bằng /exec: ").strip()
    token = getpass.getpass("Nhập FORM_TOKEN đã đặt trong Script Properties: ")
    contents = render_form_config(url, token)
    if CONFIG_PATH.exists():
        answer = input("Đã có config.local.js. Ghi đè tệp này? (y/N): ").strip().lower()
        if answer != "y":
            print("Đã hủy; tệp cấu hình hiện có được giữ nguyên.")
            return CONFIG_PATH
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(contents, encoding="utf-8")
    print("Đã tạo web_form/config.local.js. Tệp này nằm trong .gitignore.")
    return CONFIG_PATH


if __name__ == "__main__":
    try:
        configure_form()
    except (ValueError, OSError) as exc:
        raise SystemExit(f"Không tạo được cấu hình form: {exc}") from exc
