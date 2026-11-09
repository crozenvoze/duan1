import unittest

from src.update_data import watchlist_tickers


class WatchlistTickerTests(unittest.TestCase):
    def test_returns_unique_uppercase_valid_tickers(self):
        rows = [
            ["ticker", "alert_above", "alert_below", "note"],
            ["fpt", "", "", ""],
            ["FPT", "", "", "duplicate"],
            ["VNM", "", "", ""],
            ["bad1", "", "", "invalid"],
            ["", "", "", "blank"],
        ]
        self.assertEqual(watchlist_tickers(rows), ["FPT", "VNM"])

    def test_missing_ticker_column_is_clear_error(self):
        with self.assertRaisesRegex(RuntimeError, "thiếu cột ticker"):
            watchlist_tickers([["symbol", "note"], ["FPT", "x"]])

    def test_empty_sheet_returns_no_tickers(self):
        self.assertEqual(watchlist_tickers([]), [])


if __name__ == "__main__":
    unittest.main()
