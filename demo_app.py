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
closed_pf = summary["closed_trade_profit_factor"]
closed_pf_text = "∞" if closed_pf == float("inf") else ("—" if closed_pf is None else f"{closed_pf:.2f}")
left, middle, right, last = st.columns(4)
left.metric("Lãi/lỗ đã thực hiện", f"{summary['realized_pnl']:,.0f} VND")
middle.metric("Vị thế đã đóng", f"{summary['closed_trade_count']:,}")
right.metric("Win rate / vị thế đóng", f"{summary['closed_trade_win_rate']:.0%}")
last.metric("Profit factor / vị thế đóng", closed_pf_text)

with st.expander("Thống kê theo từng lần bán"):
    event_pf = summary["profit_factor"]
    event_pf_text = "∞" if event_pf == float("inf") else ("—" if event_pf is None else f"{event_pf:.2f}")
    a, b, c, d = st.columns(4)
    a.metric("Sự kiện bán", f"{summary['closed_sell_events']:,}")
    b.metric("Win rate / lần bán", f"{summary['win_rate']:.0%}")
    c.metric("Profit factor / lần bán", event_pf_text)
    d.metric("Expectancy / lần bán", f"{summary['expectancy']:,.0f} VND")

st.subheader("Vị thế cuối kỳ")
positions = pd.DataFrame(
    [
        {"Mã": ticker, "Khối lượng": position["quantity"], "Giá vốn bình quân (VND)": position["average_cost"]}
        for ticker, position in result["positions"].items()
        if position["quantity"] > 0
    ]
)
st.dataframe(positions, hide_index=True, width="stretch")

st.subheader("Chu kỳ vị thế đã đóng")
closed = pd.DataFrame(
    [
        {
            "Mã": trade["ticker"],
            "Ngày mở": trade["entry_date"],
            "Ngày đóng": trade["exit_date"],
            "Số lệnh mua/bán": f"{trade['buy_events']}/{trade['sell_events']}",
            "Lãi/lỗ toàn chu kỳ (VND)": trade["realized_pnl"],
            "R-multiple": trade["r_multiple"],
        }
        for trade in result["closed_trades"]
    ]
)
st.dataframe(closed, hide_index=True, width="stretch")

st.subheader("Lãi/lỗ thực hiện cộng dồn")
curve = pd.DataFrame(result["equity_curve"])
if not curve.empty:
    figure = px.line(curve, x=curve.index + 1, y="cumulative_realized_pnl", markers=True,
                     labels={"x": "Lần bán", "cumulative_realized_pnl": "VND"})
    figure.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(figure, width="stretch")

st.caption("Giả định: giá vốn bình quân gia quyền; phí bằng 0 trong dữ liệu demo. Xem README để biết phương pháp và hạn chế.")
