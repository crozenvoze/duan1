"""Kiểm thử chuẩn hóa giá và tương thích lời gọi Vnstock v5/v6 bằng dữ liệu giả."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from datetime import date

import pandas as pd

from src.market_data import _fetch_ohlcv, _normalize_history, fetch_history, get_current_price


class MarketDataTests(unittest.TestCase):
    def test_current_price_v5_quote_is_already_in_vnd(self):
        class Instrument:
            def quote(self):
                return pd.DataFrame({"close_price": [12345.0]})

        class Market:
            def equity(self, symbol):
                self.symbol = symbol
                return Instrument()

        market = Market()
        with patch("src.market_data._market_client", return_value=market):
            result = get_current_price("fpt")

        self.assertEqual(market.symbol, "FPT")
        self.assertEqual(result, {"ticker": "FPT", "price": 12345.0, "source": "quote"})

    def test_current_price_v6_quote_scales_thousand_vnd_to_vnd(self):
        class Instrument:
            def quote(self):
                return pd.DataFrame({"close": [12.345]})

        class Market:
            def equity(self, symbol):
                return Instrument()

        with patch("src.market_data._market_client", return_value=Market()):
            result = get_current_price("FPT")

        self.assertEqual(result, {"ticker": "FPT", "price": 12345.0, "source": "quote"})

    def test_current_price_falls_back_to_latest_history_when_quote_fails(self):
        class Instrument:
            def quote(self):
                raise RuntimeError("quote unavailable")

        class Market:
            def equity(self, symbol):
                return Instrument()

        history = pd.DataFrame({
            "date": [pd.Timestamp("2026-01-06")],
            "close": [12345.0],
        })
        with patch("src.market_data._market_client", return_value=Market()), patch(
            "src.market_data.vietnam_today", return_value=date(2026, 1, 6)
        ) as today, patch("src.market_data.fetch_history", return_value=history) as fetch:
            result = get_current_price("FPT")

        today.assert_called_once_with()
        fetch.assert_called_once_with("FPT", "2025-12-27", "2026-01-06")
        self.assertEqual(result["ticker"], "FPT")
        self.assertEqual(result["price"], 12345.0)
        self.assertEqual(result["source"], "historical_close")

    def test_normalize_equity_prices_to_vnd(self):
        raw = pd.DataFrame({
            "time": ["2026-01-05"], "open": [10.0], "high": [11.0],
            "low": [9.0], "close": [10.5], "volume": [1000],
        })
        result = _normalize_history(raw, "FPT", price_scale=1000)
        self.assertEqual(result.iloc[0]["close"], 10500)
        self.assertEqual(result.iloc[0]["volume"], 1000)

    def test_normalize_vietnam_timezone_candles_to_local_session_dates(self):
        raw = pd.DataFrame({
            "time": pd.to_datetime(["2026-01-05T07:00:00+07:00"]),
            "open": [10.0], "high": [11.0], "low": [9.0],
            "close": [10.5], "volume": [1000],
        })
        result = _normalize_history(raw, "FPT", price_scale=1000)

        self.assertEqual(result.iloc[0]["date"], pd.Timestamp("2026-01-05"))

    def test_fetch_history_includes_end_date_from_timezone_aware_source(self):
        candles = pd.DataFrame({
            "time": pd.to_datetime([
                "2026-01-05T07:00:00+07:00",
                "2026-01-06T07:00:00+07:00",
            ]),
            "open": [10.0, 11.0], "high": [10.0, 11.0],
            "low": [10.0, 11.0], "close": [10.0, 11.0], "volume": [100, 200],
        })

        class Instrument:
            def ohlcv(self, **kwargs):
                return candles

        class Market:
            def equity(self, symbol):
                return Instrument()

        with TemporaryDirectory() as cache_directory:
            with patch("src.market_data.CACHE_DIR", Path(cache_directory)), patch(
                "src.market_data._market_client", return_value=Market()
            ):
                result = fetch_history(
                    "FPT", "2026-01-05", "2026-01-06", force_refresh=True
                )

        self.assertEqual(result["date"].dt.strftime("%Y-%m-%d").tolist(), [
            "2026-01-05", "2026-01-06"
        ])

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
