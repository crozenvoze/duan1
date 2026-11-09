"""Dashboard phân tích BCTC và DuPont từ tab Fundamentals đã chuẩn hóa."""

from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fundamentals import calculate_fundamental_row, fetch_raw_statements, read_fundamentals

st.set_page_config(page_title="Fundamentals", page_icon="📊", layout="wide")


@st.cache_data(ttl=300, show_spinner="Đang đọc tab Fundamentals...")
def load_fundamentals() -> pd.DataFrame:
    """Đọc bảng fundamentals, cache 5 phút để hạn chế gọi Sheets."""
    return read_fundamentals()


st.title("📊 Fundamental Dashboard")
st.caption("Chỉ tính từ dữ liệu đã ánh xạ rõ sang chỉ tiêu VAS; ngân hàng cần nhánh phân tích riêng.")

try:
    data = load_fundamentals()
except Exception:
    st.error("Không đọc được tab Fundamentals. Kiểm tra kết nối Google Sheets.")
    st.stop()

if data.empty or "ticker" not in data.columns:
    st.info("Tab Fundamentals chưa có dữ liệu chuẩn hóa. Chưa tự ánh xạ nhãn báo cáo vì schema nguồn Vnstock phụ thuộc nguồn/kỳ.")
    ticker_raw = st.text_input("Mã cần xem báo cáo thô", max_chars=3, placeholder="FPT").strip().upper()
    period = st.selectbox("Kỳ báo cáo", ["quarter", "year"], format_func=lambda value: "Quý" if value == "quarter" else "Năm")
    if st.button("Lấy báo cáo thô từ Vnstock"):
        if len(ticker_raw) != 3 or not ticker_raw.isalpha():
            st.error("Nhập mã gồm đúng 3 chữ cái.")
        else:
            try:
                raw = fetch_raw_statements(ticker_raw, period)
                for name, frame in raw.items():
                    st.markdown(f"#### {name}")
                    st.dataframe(frame, use_container_width=True)
                st.warning("Đối chiếu nhãn báo cáo với VAS và schema nội bộ trước khi ghi chỉ số.")
            except Exception as exc:
                st.error(str(exc))
    st.stop()

symbols = sorted(data["ticker"].dropna().astype(str).str.upper().unique())
ticker = st.selectbox("Chọn mã", symbols)
selected = data[data["ticker"].astype(str).str.upper() == ticker].copy()
if "period" in selected.columns:
    selected = selected.sort_values("period")

st.subheader(f"Chỉ số theo kỳ — {ticker}")
try:
    metric_rows = [calculate_fundamental_row(row) for row in selected.to_dict(orient="records")]
    metrics = pd.DataFrame(metric_rows)
except Exception as exc:
    st.error(f"Không thể tính chỉ số: {exc}")
    st.stop()

latest = metrics.iloc[-1]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Doanh thu thuần", f"{float(latest['revenue']):,.0f} VND")
col2.metric("Biên lợi nhuận ròng", "—" if pd.isna(latest["net_margin"]) else f"{latest['net_margin']:.2%}")
col3.metric("ROE", "—" if pd.isna(latest["roe_direct"]) else f"{latest['roe_direct']:.2%}")
col4.metric("Cash conversion", "—" if pd.isna(latest["cash_conversion"]) else f"{latest['cash_conversion']:.2f}x")

left, right = st.columns(2)
with left:
    fig = go.Figure()
    for column, label in (("net_margin", "Biên ròng"), ("roe_direct", "ROE"), ("roa", "ROA")):
        if column in metrics:
            fig.add_trace(go.Scatter(x=metrics["period"], y=metrics[column] * 100, mode="lines+markers", name=label))
    fig.update_layout(title="Xu hướng biên lợi nhuận, ROE và ROA", yaxis_title="%", height=340)
    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = go.Figure()
    for column, label in (("net_margin", "Net margin"), ("asset_turnover", "Asset turnover"), ("equity_multiplier", "Equity multiplier")):
        if column in metrics:
            fig.add_trace(go.Bar(x=metrics["period"], y=metrics[column], name=label))
    fig.update_layout(title="DuPont 3 bước", barmode="group", height=340)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Bảng chỉ số và đối chiếu DuPont")
display_columns = [column for column in (
    "period", "revenue", "net_income", "net_margin", "asset_turnover", "equity_multiplier",
    "roe_direct", "roe_dupont", "roa", "debt_to_equity", "cash_conversion",
) if column in metrics.columns]
st.dataframe(metrics[display_columns], hide_index=True, use_container_width=True)
if "industry" in metrics.columns:
    industry = metrics["industry"].iloc[-1]
    peers = data[data["industry"].astype(str) == str(industry)].copy()
    peer_columns = [column for column in (
        "revenue", "net_income", "total_assets", "total_equity", "net_cash_from_operating_activities",
    ) if column in peers.columns]
    peer_medians = peers[peer_columns].apply(pd.to_numeric, errors="coerce").median().dropna()
    if not peer_medians.empty:
        st.markdown(f"**Trung vị ngành {industry}** · {peers['ticker'].nunique()} mã trong dữ liệu hiện có")
        peer_frame = peer_medians.rename("Trung vị (VND)").rename_axis("Chỉ tiêu").reset_index()
        st.dataframe(peer_frame, hide_index=True, use_container_width=True)
    else:
        st.info(f"Đã có {len(peers)} dòng ngành {industry}, nhưng chưa đủ cột số liệu chung để tính trung vị.")
else:
    st.info("So sánh trung vị ngành sẽ hiển thị khi có dữ liệu ngành đã được ánh xạ và lưu trong tab.")

with st.expander("Chất lượng lợi nhuận — giới hạn dữ liệu hiện có"):
    st.markdown(
        "Cash conversion = dòng tiền HĐKD / lợi nhuận ròng. Muốn kiểm tra khoản phải thu tăng nhanh hơn doanh thu, "
        "cần bổ sung số dư phải thu đầu/cuối kỳ và doanh thu các kỳ so sánh. Không đánh giá khi thiếu những trường đó."
    )
