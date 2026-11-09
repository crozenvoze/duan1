"""Giao diện Stock Screener lấy dữ liệu chuẩn hóa từ tab Screener_Data."""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.screener import filter_stocks, rank_stocks
from src.sheets import open_spreadsheet, read_worksheet

st.set_page_config(page_title="Stock Screener", page_icon="🔎", layout="wide")


@st.cache_data(ttl=300)
def load_screener_data() -> pd.DataFrame:
    """Đọc dữ liệu chuẩn hóa từ tab Screener_Data và cache 5 phút."""
    rows = read_worksheet("Screener_Data")
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows[1:], columns=rows[0])


def save_favorite_filter(name: str, criteria: dict) -> None:
    """Lưu cấu hình lọc vào tab Saved_Filters, không ghi đè bộ lọc cũ."""
    spreadsheet = open_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet("Saved_Filters")
    except Exception:
        worksheet = spreadsheet.add_worksheet(title="Saved_Filters", rows=500, cols=3)
    if worksheet.get_last_row() == 0:
        worksheet.append_row(["name", "criteria_json", "saved_at"])
    from datetime import datetime, timezone
    import json
    worksheet.append_row([name, json.dumps(criteria, ensure_ascii=False), datetime.now(timezone.utc).isoformat()])


st.title("🔎 Stock Screener")
st.caption("Nguồn dữ liệu là tab Screener_Data; kiểm tra kỳ và đơn vị trước khi diễn giải kết quả.")
if st.button("Làm mới screener"):
    load_screener_data.clear()

try:
    data = load_screener_data()
except Exception:
    st.error("Không đọc được tab Screener_Data trong Google Sheet.")
    st.stop()

if data.empty:
    st.info("Tạo tab Screener_Data với các cột: ticker, pe, pb, roe, revenue_growth, eps_growth, debt_to_equity, avg_value_traded, market_cap, industry, momentum.")
    st.stop()

with st.sidebar:
    st.subheader("Bộ lọc")
    industry_options = sorted(data["industry"].dropna().astype(str).unique()) if "industry" in data else []
    industries = st.multiselect("Ngành", industry_options)
    roe_min = st.number_input("ROE tối thiểu (%)", value=0.0, step=1.0) / 100
    pe_max = st.number_input("P/E tối đa", value=100.0, min_value=0.0, step=1.0)
    pb_max = st.number_input("P/B tối đa", value=20.0, min_value=0.0, step=0.5)
    debt_max = st.number_input("Nợ vay/VCSH tối đa", value=5.0, min_value=0.0, step=0.1)
    liquidity_min = st.number_input("GTGD TB tối thiểu (VND)", value=0.0, min_value=0.0, step=100000000.0)

criteria = {
    "roe_min": roe_min,
    "pe_max": pe_max,
    "pb_max": pb_max,
    "debt_to_equity_max": debt_max,
    "avg_value_traded_min": liquidity_min,
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
    st.dataframe(ranked, hide_index=True, use_container_width=True)
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
