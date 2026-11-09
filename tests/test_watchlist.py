"""Kiểm thử biến động, so sánh thanh khoản và cảnh báo Watchlist."""

import unittest

from src.watchlist import price_change_from_sessions, threshold_alert, volume_vs_previous_sessions


class WatchlistTests(unittest.TestCase):
    def test_price_change_uses_previous_close_and_session_offsets(self):
        closes = [100, 110, 120, 125, 130, 140, 150]
        self.assertAlmostEqual(price_change_from_sessions(closes, 154, 1), 0.1)
        self.assertAlmostEqual(price_change_from_sessions(closes, 154, 5), 0.4)
        self.assertIsNone(price_change_from_sessions(closes, 154, 7))

    def test_latest_volume_compared_with_twenty_prior_sessions(self):
        latest, ratio = volume_vs_previous_sessions(list(range(1, 22)), sessions=20)
        self.assertEqual(latest, 21)
        self.assertAlmostEqual(ratio, 21 / 10.5)
        self.assertEqual(volume_vs_previous_sessions(list(range(1, 21))), (None, None))

    def test_price_alert_thresholds(self):
        self.assertEqual(threshold_alert(110, 110, 90), "Vượt ngưỡng trên")
        self.assertEqual(threshold_alert(90, 110, 90), "Chạm ngưỡng dưới")
        self.assertEqual(threshold_alert(100, 110, 90), "")


if __name__ == "__main__":
    unittest.main()
