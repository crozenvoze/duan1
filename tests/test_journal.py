"""Kiểm thử giá vốn bình quân và chỉ số journal bằng 10 lệnh giả lập."""

import unittest

from datetime import datetime

from src.journal import calculate_journal, rows_to_trades
from src.sample_data import SAMPLE_TRADES


class JournalTests(unittest.TestCase):
    """So sánh các kết quả của journal với đáp án tính tay trong spec."""

    def test_ten_sample_trades(self):
        result = calculate_journal(SAMPLE_TRADES)
        summary = result["summary"]

        self.assertEqual(len(SAMPLE_TRADES), 10)
        self.assertAlmostEqual(result["realized_events"][0]["average_cost"], 105)
        self.assertAlmostEqual(result["realized_events"][1]["average_cost"], 97.5)
        self.assertAlmostEqual(result["realized_events"][2]["average_cost"], 98.75)
        self.assertAlmostEqual(summary["realized_pnl"], 1500)
        self.assertEqual(summary["closed_sell_events"], 4)
        self.assertAlmostEqual(summary["win_rate"], 0.5)
        self.assertAlmostEqual(summary["average_win"], 1312.5)
        self.assertAlmostEqual(summary["average_loss"], 562.5)
        self.assertAlmostEqual(summary["profit_factor"], 2625 / 1125)
        self.assertAlmostEqual(summary["expectancy"], 375)
        self.assertAlmostEqual(summary["max_drawdown_amount"], 750)
        self.assertAlmostEqual(summary["max_drawdown_pct"], 0.5)
        self.assertEqual(result["positions"]["FPT"]["quantity"], 0)
        self.assertEqual(result["positions"]["MWG"]["quantity"], 200)
        self.assertAlmostEqual(result["positions"]["MWG"]["average_cost"], 55)
        self.assertEqual(summary["r_multiple_count"], 4)

    def test_rejects_oversell(self):
        trades = [
            {"ticker": "FPT", "side": "SELL", "price": 100, "quantity": 100, "fee": 0}
        ]
        with self.assertRaisesRegex(ValueError, "Bán khống chưa được hỗ trợ"):
            calculate_journal(trades)

    def test_backfilled_trades_sort_by_execution_date_not_entry_timestamp(self):
        trades = [
            {"trade_id": "SELL", "timestamp": "2026-01-06 10:00:00", "trade_date": "2026-01-02", "ticker": "FPT", "side": "SELL", "price": 110, "quantity": 100, "fee": 0},
            {"trade_id": "BUY", "timestamp": "2026-01-07 10:00:00", "trade_date": "2026-01-01", "ticker": "FPT", "side": "BUY", "price": 100, "quantity": 100, "fee": 0},
        ]
        result = calculate_journal(trades)
        self.assertEqual(result["realized_events"][0]["trade_id"], "SELL")
        self.assertEqual(result["realized_events"][0]["realized_pnl"], 1000)

    def test_rows_to_trades_normalizes_google_sheet_serial_dates(self):
        sheet_epoch = datetime(1899, 12, 30)
        trade_date_serial = (datetime(2026, 1, 5) - sheet_epoch).days
        timestamp_serial = (datetime(2026, 1, 5, 9, 30) - sheet_epoch).total_seconds() / 86400
        rows = [
            ["trade_id", "timestamp", "trade_date", "ticker"],
            ["T1", timestamp_serial, trade_date_serial, "FPT"],
        ]
        result = rows_to_trades(rows)[0]
        self.assertEqual(result["timestamp"], "2026-01-05 09:30:00")
        self.assertEqual(result["trade_date"], "2026-01-05")


if __name__ == "__main__":
    unittest.main()
