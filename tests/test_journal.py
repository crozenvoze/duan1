"""Kiểm thử giá vốn bình quân và chỉ số journal bằng 10 lệnh giả lập."""

import unittest

from src.journal import calculate_journal
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


if __name__ == "__main__":
    unittest.main()
