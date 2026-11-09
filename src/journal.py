"""Tính vị thế và hiệu quả nhật ký giao dịch theo giá vốn bình quân gia quyền."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from math import inf
from typing import Any, Iterable


def _number(value: Any, field: str, trade_id: str) -> float:
    """Đổi một ô Sheet thành số hữu hạn; báo rõ giao dịch và cột lỗi."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Giao dịch {trade_id}: cột {field} không phải số hợp lệ.") from exc
    if number != number or number in (inf, -inf):
        raise ValueError(f"Giao dịch {trade_id}: cột {field} không phải số hữu hạn.")
    return number


def _parse_sheet_datetime(value: Any) -> datetime | None:
    """Đọc ngày ISO hoặc số serial ngày giờ mà Google Sheets trả về."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value >= 0 and value < 3_000_000:
            # Google Sheets dùng epoch 1899-12-30 cho ngày giờ dạng số serial.
            return datetime(1899, 12, 30) + timedelta(days=float(value))
        return None
    if value:
        text = str(value).strip()
        for pattern in (
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y",
        ):
            try:
                return datetime.strptime(text[:19], pattern)
            except ValueError:
                pass
        try:
            serial = float(text)
        except ValueError:
            return None
        if 0 <= serial < 3_000_000:
            return datetime(1899, 12, 30) + timedelta(days=serial)
    return None


def _trade_datetime(trade: dict[str, Any], index: int) -> tuple[datetime, datetime, int]:
    """Sắp xếp theo ngày khớp, rồi timestamp nhập lệnh và thứ tự hàng."""
    recorded_at = _parse_sheet_datetime(trade.get("timestamp")) or datetime.min
    trade_date = _parse_sheet_datetime(trade.get("trade_date")) or recorded_at
    return trade_date, recorded_at, index


def _clean_trade(trade: dict[str, Any], index: int) -> dict[str, Any]:
    """Kiểm tra và chuẩn hóa một lệnh đọc từ Google Sheets."""
    trade_id = str(trade.get("trade_id") or f"row-{index + 1}")
    ticker = str(trade.get("ticker") or "").strip().upper()
    side = str(trade.get("side") or "").strip().upper()
    if len(ticker) != 3 or not ticker.isalpha():
        raise ValueError(f"Giao dịch {trade_id}: ticker phải gồm đúng 3 chữ cái.")
    if side not in {"BUY", "SELL"}:
        raise ValueError(f"Giao dịch {trade_id}: side phải là BUY hoặc SELL.")

    price = _number(trade.get("price"), "price", trade_id)
    quantity_value = _number(trade.get("quantity"), "quantity", trade_id)
    fee = _number(trade.get("fee") or 0, "fee", trade_id)
    if price <= 0 or quantity_value <= 0 or not quantity_value.is_integer() or fee < 0:
        raise ValueError(f"Giao dịch {trade_id}: giá/khối lượng phải dương, khối lượng nguyên, phí không âm.")

    stop_raw = trade.get("stop_loss")
    stop_loss = None if stop_raw in (None, "") else _number(stop_raw, "stop_loss", trade_id)
    if stop_loss is not None and stop_loss <= 0:
        raise ValueError(f"Giao dịch {trade_id}: stop_loss phải lớn hơn 0 hoặc để trống.")

    return {
        **trade,
        "trade_id": trade_id,
        "ticker": ticker,
        "side": side,
        "price": price,
        "quantity": int(quantity_value),
        "fee": fee,
        "stop_loss": stop_loss,
        "strategy_tag": str(trade.get("strategy_tag") or "Chưa gắn nhãn").strip() or "Chưa gắn nhãn",
        "_sort": _trade_datetime(trade, index),
    }


def rows_to_trades(rows: list[list[Any]]) -> list[dict[str, Any]]:
    """Chuyển dữ liệu dạng hàng từ get_all_values thành danh sách giao dịch."""
    if not rows:
        return []
    headers = [str(cell).strip() for cell in rows[0]]
    output = []
    for row in rows[1:]:
        if not any(str(cell).strip() for cell in row):
            continue
        trade = {headers[col]: row[col] if col < len(row) else "" for col in range(len(headers))}
        for field in ("timestamp", "trade_date"):
            parsed = _parse_sheet_datetime(trade.get(field))
            if parsed is not None:
                trade[field] = parsed.isoformat(sep=" ", timespec="seconds") if field == "timestamp" else parsed.date().isoformat()
        output.append(trade)
    return output


def calculate_journal(trades: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Tính vị thế, lãi/lỗ đã thực hiện và thống kê từ danh sách lệnh.

    Giá vốn bình quân gồm phí BUY phân bổ vào giá vốn. Phí SELL được trừ khỏi
    lãi/lỗ thực hiện. Mỗi lần SELL là một sự kiện để tính win rate/expectancy;
    drawdown tính trên P&L cộng dồn từ 0, không phải NAV có tiền mặt và giá thị trường.
    """
    clean = [_clean_trade(trade, i) for i, trade in enumerate(trades)]
    clean.sort(key=lambda trade: trade["_sort"])

    positions: dict[str, dict[str, float | int]] = {}
    realized: list[dict[str, Any]] = []

    for trade in clean:
        ticker = trade["ticker"]
        position = positions.setdefault(ticker, {"quantity": 0, "cost_basis": 0.0})
        quantity = int(trade["quantity"])
        price = float(trade["price"])
        fee = float(trade["fee"])

        if trade["side"] == "BUY":
            position["quantity"] = int(position["quantity"]) + quantity
            position["cost_basis"] = float(position["cost_basis"]) + price * quantity + fee
            continue

        held = int(position["quantity"])
        if quantity > held:
            raise ValueError(
                f"Giao dịch {trade['trade_id']}: bán {quantity} cổ phiếu {ticker} "
                f"nhưng vị thế đang có {held}. Bán khống chưa được hỗ trợ."
            )

        average_cost = float(position["cost_basis"]) / held if held else 0.0
        allocated_cost = average_cost * quantity
        pnl = (price * quantity) - allocated_cost - fee
        r_multiple = None
        stop_loss = trade["stop_loss"]
        if stop_loss is not None:
            initial_risk = abs(average_cost - float(stop_loss)) * quantity
            if initial_risk > 0:
                r_multiple = pnl / initial_risk

        realized.append({
            "trade_id": trade["trade_id"],
            "trade_date": trade.get("trade_date", ""),
            "ticker": ticker,
            "quantity": quantity,
            "average_cost": average_cost,
            "sell_price": price,
            "fee": fee,
            "realized_pnl": pnl,
            "r_multiple": r_multiple,
            "strategy_tag": trade["strategy_tag"],
        })
        position["quantity"] = held - quantity
        position["cost_basis"] = max(0.0, float(position["cost_basis"]) - allocated_cost)

    positions_result = {
        ticker: {
            "quantity": int(position["quantity"]),
            "average_cost": (float(position["cost_basis"]) / int(position["quantity"]))
                if int(position["quantity"]) > 0 else None,
            "cost_basis": float(position["cost_basis"]),
        }
        for ticker, position in positions.items()
    }

    wins = [event["realized_pnl"] for event in realized if event["realized_pnl"] > 0]
    losses = [event["realized_pnl"] for event in realized if event["realized_pnl"] < 0]
    total_win = sum(wins)
    total_loss_abs = abs(sum(losses))
    event_count = len(realized)
    win_rate = len(wins) / event_count if event_count else 0.0
    loss_rate = len(losses) / event_count if event_count else 0.0
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = abs(sum(losses) / len(losses)) if losses else 0.0

    equity_curve: list[dict[str, Any]] = []
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    max_drawdown_pct: float | None = None
    for event in realized:
        cumulative += event["realized_pnl"]
        peak = max(peak, cumulative)
        drawdown = peak - cumulative
        max_drawdown = max(max_drawdown, drawdown)
        pct = drawdown / peak if peak > 0 else None
        if pct is not None and (max_drawdown_pct is None or pct > max_drawdown_pct):
            max_drawdown_pct = pct
        equity_curve.append({
            "trade_id": event["trade_id"],
            "ticker": event["ticker"],
            "cumulative_realized_pnl": cumulative,
            "drawdown": drawdown,
        })

    by_strategy: dict[str, dict[str, Any]] = defaultdict(lambda: {"events": 0, "wins": 0, "losses": 0, "realized_pnl": 0.0})
    for event in realized:
        summary = by_strategy[event["strategy_tag"]]
        summary["events"] += 1
        summary["realized_pnl"] += event["realized_pnl"]
        if event["realized_pnl"] > 0:
            summary["wins"] += 1
        elif event["realized_pnl"] < 0:
            summary["losses"] += 1
    for summary in by_strategy.values():
        summary["win_rate"] = summary["wins"] / summary["events"] if summary["events"] else 0.0

    r_values = [event["r_multiple"] for event in realized if event["r_multiple"] is not None]
    return {
        "positions": positions_result,
        "realized_events": realized,
        "summary": {
            "realized_pnl": sum(event["realized_pnl"] for event in realized),
            "closed_sell_events": event_count,
            "win_rate": win_rate,
            "average_win": average_win,
            "average_loss": average_loss,
            "profit_factor": total_win / total_loss_abs if total_loss_abs > 0 else (inf if total_win > 0 else None),
            "expectancy": win_rate * average_win - loss_rate * average_loss,
            "average_r_multiple": sum(r_values) / len(r_values) if r_values else None,
            "r_multiple_count": len(r_values),
            "max_drawdown_amount": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
        },
        "equity_curve": equity_curve,
        "by_strategy": dict(by_strategy),
    }


def read_and_calculate(sheet_rows: list[list[str]]) -> dict[str, Any]:
    """Chuyển hàng từ Google Sheets và tính bộ chỉ số nhật ký giao dịch."""
    return calculate_journal(rows_to_trades(sheet_rows))


if __name__ == "__main__":
    from src.sheets import read_trades

    result = read_and_calculate(read_trades())
    print(f"Tickers in journal: {len(result['positions'])}")
    print(f"Realized P&L: {result['summary']['realized_pnl']:,.0f} VND")
    print(f"Recorded sell events: {result['summary']['closed_sell_events']}")
