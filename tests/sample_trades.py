"""Bộ 10 giao dịch giả lập dùng để đối chiếu tay và kiểm thử journal."""

SAMPLE_TRADES = [
    {"trade_id": "S01", "trade_date": "2026-01-05", "ticker": "FPT", "side": "BUY", "price": 100, "quantity": 100, "fee": 0, "strategy_tag": "swing"},
    {"trade_id": "S02", "trade_date": "2026-01-05", "ticker": "FPT", "side": "BUY", "price": 110, "quantity": 100, "fee": 0, "strategy_tag": "swing"},
    {"trade_id": "S03", "trade_date": "2026-01-06", "ticker": "FPT", "side": "SELL", "price": 120, "quantity": 100, "fee": 0, "stop_loss": 95, "strategy_tag": "swing"},
    {"trade_id": "S04", "trade_date": "2026-01-07", "ticker": "FPT", "side": "BUY", "price": 90, "quantity": 100, "fee": 0, "strategy_tag": "swing"},
    {"trade_id": "S05", "trade_date": "2026-01-08", "ticker": "FPT", "side": "SELL", "price": 90, "quantity": 100, "fee": 0, "stop_loss": 105, "strategy_tag": "swing"},
    {"trade_id": "S06", "trade_date": "2026-01-09", "ticker": "FPT", "side": "BUY", "price": 100, "quantity": 100, "fee": 0, "strategy_tag": "swing"},
    {"trade_id": "S07", "trade_date": "2026-01-12", "ticker": "FPT", "side": "SELL", "price": 110, "quantity": 100, "fee": 0, "stop_loss": 90, "strategy_tag": "swing"},
    {"trade_id": "S08", "trade_date": "2026-01-13", "ticker": "FPT", "side": "SELL", "price": 95, "quantity": 100, "fee": 0, "stop_loss": 90, "strategy_tag": "swing"},
    {"trade_id": "S09", "trade_date": "2026-01-14", "ticker": "MWG", "side": "BUY", "price": 50, "quantity": 100, "fee": 0, "strategy_tag": "value"},
    {"trade_id": "S10", "trade_date": "2026-01-15", "ticker": "MWG", "side": "BUY", "price": 60, "quantity": 100, "fee": 0, "strategy_tag": "value"},
]
