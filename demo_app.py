"""Public-safe demonstration using only fictional sample transactions."""

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.journal import calculate_journal
from src.sample_data import SAMPLE_TRADES

st.set_page_config(page_title="Vietnam Equity Toolkit Demo", page_icon="📈", layout="wide")
st.title("Vietnam Equity Research Toolkit")
st.caption("Bản demo công khai chỉ dùng giao dịch giả lập, không kết nối Sheet cá nhân.")
st.info("Dữ liệu dưới đây hoàn toàn giả lập để minh họa cách tính journal.")

result = calculate_journal(SAMPLE_TRADES)
summary = result["summary"]
left, middle, right = st.columns(3)
left.metric("Lãi/lỗ đã thực hiện", f"{summary['realized_pnl']:,.0f} VND")
middle.metric("Tỷ lệ giao dịch thắng", f"{summary['win_rate']:.0%}")
right.metric("Profit factor", f"{summary['profit_factor']:.2f}")

st.subheader("Vị thế cuối kỳ")
positions = pd.DataFrame(
    [
        {"Mã": ticker, "Khối lượng": position["quantity"], "Giá vốn bình quân (VND)": position["average_cost"]}
        for ticker, position in result["positions"].items()
        if position["quantity"] > 0
    ]
)
st.dataframe(positions, hide_index=True, use_container_width=True)

st.subheader("Lãi/lỗ thực hiện cộng dồn")
curve = pd.DataFrame(result["equity_curve"])
if not curve.empty:
    figure = px.line(curve, x=curve.index + 1, y="cumulative_realized_pnl", markers=True,
                     labels={"x": "Lần bán", "cumulative_realized_pnl": "VND"})
    figure.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(figure, use_container_width=True)

st.caption("Giả định: giá vốn bình quân gia quyền; phí bằng 0 trong dữ liệu demo. Xem README để biết phương pháp và hạn chế.")
