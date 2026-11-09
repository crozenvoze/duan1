"""Trang chủ Streamlit cho Vietnam Equity Research Toolkit."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(
    page_title="Vietnam Equity Toolkit",
    page_icon="📈",
    layout="wide",
)

st.title("Bộ công cụ nghiên cứu cổ phiếu Việt Nam")
st.caption("Nhật ký giao dịch, dữ liệu thị trường và công cụ phân tích danh mục.")

st.info("Chọn một mục ở thanh bên để mở trang phân tích. Dữ liệu thị trường cần cài và cấu hình Vnstock riêng.")
st.markdown(
    """
    ### Các trang trong ứng dụng
    - **Trading Journal:** vị thế, giá vốn bình quân và hiệu quả giao dịch đã thực hiện.
    - **Watchlist:** giá, biến động, thanh khoản và ngưỡng theo dõi.
    - **Fundamentals:** chuỗi chỉ số đã ánh xạ vào bảng dữ liệu chuẩn.
    - **Screener:** lọc và xếp hạng theo bộ tiêu chí.
    - **Backtest & Risk:** thử nghiệm chiến lược, rủi ro và phân bổ danh mục.

    Các kết quả phụ thuộc vào dữ liệu Sheet và nhà cung cấp. Hãy kiểm tra nguồn, kỳ báo cáo
    và giả định trước khi dùng để nghiên cứu đầu tư.
    """
)
