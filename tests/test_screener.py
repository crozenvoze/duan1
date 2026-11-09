"""Kiểm thử lọc và xếp hạng cổ phiếu bằng dữ liệu giả lập."""

import unittest
from unittest.mock import patch

from gspread.exceptions import WorksheetNotFound
import pandas as pd

from src.screener import filter_stocks, normalize_screener_data, rank_stocks, save_favorite_filter


class FakeWorksheet:
    def __init__(self, values=None):
        self.values = list(values or [])
        self.append_calls = []

    def get_all_values(self):
        return self.values

    def append_row(self, row, value_input_option=None):
        self.append_calls.append((row, value_input_option))
        self.values.append(row)


class FakeSpreadsheet:
    def __init__(self, worksheet=None):
        self.saved_filters = worksheet
        self.created = []

    def worksheet(self, title):
        if self.saved_filters is None:
            raise WorksheetNotFound(title)
        return self.saved_filters

    def add_worksheet(self, **kwargs):
        self.created.append(kwargs)
        self.saved_filters = FakeWorksheet()
        return self.saved_filters


class ScreenerTests(unittest.TestCase):
    def test_normalize_screener_data_converts_values_and_allows_optional_momentum(self):
        data = pd.DataFrame([{
            " Ticker ": "fpt", "PE": "12.5", "PB": "2.1", "ROE": "0.15",
            "Revenue_Growth": "0.10", "EPS_Growth": "0.08", "Debt_To_Equity": "0.3",
            "Avg_Value_Traded": "1000000000", "Market_Cap": "50000000000000",
            "Industry": " Công nghệ ", "source_note": "annual filing",
        }])

        result = normalize_screener_data(data)

        self.assertEqual(result.loc[0, "ticker"], "FPT")
        self.assertAlmostEqual(result.loc[0, "roe"], 0.15)
        self.assertEqual(result.loc[0, "industry"], "Công nghệ")
        self.assertTrue(pd.isna(result.loc[0, "momentum"]))
        self.assertEqual(result.loc[0, "source_note"], "annual filing")

    def test_normalize_screener_data_rejects_missing_columns(self):
        with self.assertRaisesRegex(ValueError, "Thiếu cột bắt buộc"):
            normalize_screener_data(pd.DataFrame([{"ticker": "FPT"}]))

    def test_normalize_screener_data_rejects_invalid_numeric_values(self):
        data = pd.DataFrame([{
            "ticker": "FPT", "pe": "twelve", "pb": 2, "roe": .15,
            "revenue_growth": .1, "eps_growth": .08, "debt_to_equity": .3,
            "avg_value_traded": 1e9, "market_cap": 5e13, "industry": "Tech",
        }])
        with self.assertRaisesRegex(ValueError, "Cột pe có giá trị không phải số hữu hạn"):
            normalize_screener_data(data)

    def test_normalize_screener_data_rejects_duplicate_tickers(self):
        data = pd.DataFrame([
            {"ticker": "FPT", "pe": 10, "pb": 1, "roe": .1, "revenue_growth": .1,
             "eps_growth": .1, "debt_to_equity": .2, "avg_value_traded": 1, "market_cap": 1, "industry": "Tech"},
            {"ticker": "fpt", "pe": 11, "pb": 1, "roe": .1, "revenue_growth": .1,
             "eps_growth": .1, "debt_to_equity": .2, "avg_value_traded": 1, "market_cap": 1, "industry": "Tech"},
        ])
        with self.assertRaisesRegex(ValueError, "mã trùng: FPT"):
            normalize_screener_data(data)

    def test_filter_and_rank(self):
        data = pd.DataFrame([
            {"ticker": "AAA", "pe": 8, "pb": 1, "roe": .2, "revenue_growth": .15, "eps_growth": .12,
             "debt_to_equity": .2, "avg_value_traded": 2e9, "market_cap": 10e12, "industry": "A", "momentum": .1},
            {"ticker": "BBB", "pe": 20, "pb": 3, "roe": .1, "revenue_growth": .05, "eps_growth": .03,
             "debt_to_equity": .8, "avg_value_traded": 1e9, "market_cap": 20e12, "industry": "B", "momentum": -.1},
        ])
        filtered = filter_stocks(data, {"pe_max": 10, "industries": ["A"]})
        self.assertEqual(filtered["ticker"].tolist(), ["AAA"])
        ranked = rank_stocks(data)
        self.assertEqual(ranked.iloc[0]["ticker"], "AAA")

    def test_save_favorite_filter_creates_tab_and_header_once(self):
        spreadsheet = FakeSpreadsheet()
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            save_favorite_filter("Value", {"pe_max": 12, "industries": ["Ngân hàng"]})

        self.assertEqual(spreadsheet.created, [{"title": "Saved_Filters", "rows": 500, "cols": 3}])
        self.assertEqual(spreadsheet.saved_filters.values[0], ["name", "criteria_json", "saved_at"])
        self.assertEqual(len(spreadsheet.saved_filters.values), 2)
        self.assertEqual(spreadsheet.saved_filters.append_calls[0][1], "RAW")
        self.assertEqual(spreadsheet.saved_filters.append_calls[1][1], "RAW")

    def test_save_favorite_filter_does_not_duplicate_existing_header(self):
        worksheet = FakeWorksheet([["name", "criteria_json", "saved_at"]])
        spreadsheet = FakeSpreadsheet(worksheet)
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            save_favorite_filter("Quality", {"roe_min": 0.15})

        self.assertEqual(len(worksheet.values), 2)
        self.assertEqual(worksheet.values[1][0], "Quality")

    def test_save_favorite_filter_rejects_blank_name(self):
        with self.assertRaisesRegex(ValueError, "không được để trống"):
            save_favorite_filter("   ", {})

    def test_save_favorite_filter_rejects_wrong_existing_header(self):
        worksheet = FakeWorksheet([["filter", "json", "date"]])
        spreadsheet = FakeSpreadsheet(worksheet)
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            with self.assertRaisesRegex(RuntimeError, "Header tab Saved_Filters"):
                save_favorite_filter("Quality", {})
        self.assertEqual(len(worksheet.values), 1)
        self.assertEqual(worksheet.append_calls, [])


if __name__ == "__main__":
    unittest.main()
