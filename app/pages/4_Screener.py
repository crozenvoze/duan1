"""Giao diện Stock Screener lấy dữ liệu chuẩn hóa từ tab Screener_Data."""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.screener import filter_stocks, normalize_screener_data, rank_stocks, save_favorite_filter
from src.sheets import read_worksheet

st.set_page_config(page_title="Stock Screener", page_icon="🔎", layout="wide")


@st.cache_data(ttl=300)
def load_screener_data() -> pd.DataFrame:
    """Đọc dữ liệu chuẩn hóa từ tab Screener_Data và cache 5 phút."""
    rows = read_worksheet("Screener_Data")
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows[1:], columns=rows[0])


st.title("🔎 Stock Screener")
st.caption("Nguồn dữ liệu là tab Screener_Data; kiểm tra kỳ và đơn vị trước khi diễn giải kết quả.")
if st.button("Làm mới screener"):
    load_screener_data.clear()

sheet_error = None
try:
    data = load_screener_data()
except Exception:
    data = pd.DataFrame()
    sheet_error = "Không đọc được tab Screener_Data trong Google Sheet. Có thể nạp CSV ở đây để chạy bộ lọc trong phiên hiện tại."

st.caption("Dùng bảng trong Sheet hoặc nạp CSV. File CSV chỉ được dùng trong phiên này, không tự ghi vào Sheet.")
uploaded_csv = st.file_uploader(
    "Nạp snapshot Screener CSV",
    type=["csv"],
    help="Mẫu rỗng: data/screener_template.csv. ROE và tăng trưởng nhập dạng thập phân, ví dụ 0.15 = 15%.",
)
if uploaded_csv is not None:
    try:
        csv_data = pd.read_csv(uploaded_csv, encoding="utf-8-sig")
        data = normalize_screener_data(csv_data)
        st.success(f"Đã nạp {len(data)} mã từ CSV; file chưa được lưu vào Google Sheets.")
    except Exception as exc:
        st.error(f"Không dùng được CSV: {exc}")
        st.stop()
elif not data.empty:
    try:
        data = normalize_screener_data(data)
    except ValueError as exc:
        st.error(f"Dữ liệu trong tab Screener_Data chưa đúng: {exc}")
        st.stop()
elif sheet_error:
    st.error(sheet_error)
    st.stop()

if data.empty:
    st.info("Tab Screener_Data chưa có mã. Hãy nhập dữ liệu vào Sheet hoặc nạp CSV theo mẫu Screener.")
    st.stop()

with st.sidebar:
    st.subheader("Bộ lọc")
    industry_options = sorted(data["industry"].dropna().astype(str).unique()) if "industry" in data else []
    industries = st.multiselect("Ngành", industry_options)
    pe_min = st.number_input("P/E tối thiểu", value=0.0, min_value=0.0, step=1.0)
    pe_max = st.number_input("P/E tối đa", value=100.0, min_value=0.0, step=1.0)
    pb_min = st.number_input("P/B tối thiểu", value=0.0, min_value=0.0, step=0.5)
    pb_max = st.number_input("P/B tối đa", value=20.0, min_value=0.0, step=0.5)
    roe_min = st.number_input("ROE tối thiểu (%)", value=0.0, step=1.0) / 100
    roe_max = st.number_input("ROE tối đa (%)", value=100.0, step=1.0) / 100
    revenue_growth_min = st.number_input("Tăng trưởng doanh thu tối thiểu (%)", value=-100.0, step=1.0) / 100
    eps_growth_min = st.number_input("Tăng trưởng EPS tối thiểu (%)", value=-100.0, step=1.0) / 100
    debt_max = st.number_input("Nợ vay/VCSH tối đa", value=5.0, min_value=0.0, step=0.1)
    liquidity_min = st.number_input("GTGD TB tối thiểu (VND)", value=0.0, min_value=0.0, step=100000000.0)
    market_cap_min = st.number_input("Vốn hóa tối thiểu (VND)", value=0.0, min_value=0.0, step=100000000000.0)

criteria = {
    "roe_min": roe_min,
    "roe_max": roe_max,
    "pe_min": pe_min,
    "pe_max": pe_max,
    "pb_min": pb_min,
    "pb_max": pb_max,
    "revenue_growth_min": revenue_growth_min,
    "eps_growth_min": eps_growth_min,
    "debt_to_equity_max": debt_max,
    "avg_value_traded_min": liquidity_min,
    "market_cap_min": market_cap_min,
    "industries": industries,
}
criteria = {key: value for key, value in criteria.items() if value not in (None, [], "")}

try:
    filtered = filter_stocks(data, criteria)
    ranked = rank_stocks(filtered) if not filtered.empty else filtered
except Exception as exc:
    st.error(f"Không thể lọc dữ liệu: {exc}")
    st.stop()

st.write(f"Số mã phù hợp: **{len(ranked)}**")
if not ranked.empty:
    screen_column_config = {
        "pe": st.column_config.NumberColumn("P/E", format="%.2f"),
        "pb": st.column_config.NumberColumn("P/B", format="%.2f"),
        "roe": st.column_config.NumberColumn("ROE", format="percent"),
        "revenue_growth": st.column_config.NumberColumn("Tăng trưởng doanh thu", format="percent"),
        "eps_growth": st.column_config.NumberColumn("Tăng trưởng EPS", format="percent"),
        "debt_to_equity": st.column_config.NumberColumn("Nợ vay/VCSH", format="%.2f"),
        "avg_value_traded": st.column_config.NumberColumn("GTGD TB (VND/phiên)", format="localized"),
        "market_cap": st.column_config.NumberColumn("Vốn hóa (VND)", format="localized"),
        "composite_score": st.column_config.NumberColumn("Điểm tổng hợp", format="percent"),
        "value_score": st.column_config.NumberColumn("Điểm value", format="percent"),
        "quality_score": st.column_config.NumberColumn("Điểm quality", format="percent"),
        "growth_score": st.column_config.NumberColumn("Điểm growth", format="percent"),
        "momentum_score": st.column_config.NumberColumn("Điểm momentum", format="percent"),
    }
    st.dataframe(ranked, hide_index=True, width="stretch", column_config=screen_column_config)
    st.download_button(
        "Tải kết quả CSV",
        ranked.to_csv(index=False).encode("utf-8-sig"),
        file_name="stock_screen_results.csv",
        mime="text/csv",
    )
else:
    st.info("Không có mã phù hợp với bộ lọc hiện tại.")

with st.expander("Lưu bộ lọc yêu thích"):
    filter_name = st.text_input("Tên bộ lọc", max_chars=80)
    if st.button("Lưu bộ lọc"):
        if not filter_name.strip():
            st.error("Nhập tên bộ lọc trước khi lưu.")
        else:
            try:
                save_favorite_filter(filter_name.strip(), criteria)
                st.success("Đã lưu bộ lọc vào tab Saved_Filters.")
            except Exception:
                st.error("Không lưu được bộ lọc vào Google Sheets.")

st.caption("Điểm tổng hợp là trung bình percentile của value, quality, growth và momentum khi có đủ cột; dùng để sắp xếp nghiên cứu, không phải khuyến nghị đầu tư.")
