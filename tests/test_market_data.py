"""Kiểm thử chuẩn hóa giá và tương thích lời gọi Vnstock v5/v6 bằng dữ liệu giả."""

import unittest

import pandas as pd

from src.market_data import _fetch_ohlcv, _normalize_history


class MarketDataTests(unittest.TestCase):
    def test_normalize_equity_prices_to_vnd(self):
        raw = pd.DataFrame({
            "time": ["2026-01-05"], "open": [10.0], "high": [11.0],
            "low": [9.0], "close": [10.5], "volume": [1000],
        })
        result = _normalize_history(raw, "FPT", price_scale=1000)
        self.assertEqual(result.iloc[0]["close"], 10500)
        self.assertEqual(result.iloc[0]["volume"], 1000)

    def test_v6_domain_call(self):
        calls = {}

        class Instrument:
            def ohlcv(self, **kwargs):
                calls.update(kwargs)
                return "index data"

        class Market:
            def index(self, symbol):
                calls["symbol"] = symbol
                return Instrument()

        result = _fetch_ohlcv(Market(), "index", "VNINDEX", "2026-01-01", "2026-01-31")
        self.assertEqual(result, "index data")
        self.assertEqual(calls["symbol"], "VNINDEX")
        self.assertEqual(calls["interval"], "1D")

    def test_v5_legacy_call(self):
        calls = {}

        class Equity:
            def ohlcv(self, **kwargs):
                calls.update(kwargs)
                return "equity data"

        class Market:
            equity = Equity()

        result = _fetch_ohlcv(Market(), "equity", "FPT", "2026-01-01", "2026-01-31")
        self.assertEqual(result, "equity data")
        self.assertEqual(calls["symbol"], "FPT")


if __name__ == "__main__":
    unittest.main()
