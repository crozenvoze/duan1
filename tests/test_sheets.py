import unittest
from unittest.mock import patch

import gspread

from src.sheets import upsert_prices_cache


class FakeWorksheet:
    def __init__(self, values=None):
        self.values = values or []
        self.updates = []
        self.appended = []

    def get_all_values(self):
        return self.values

    def update(self, range_name, values):
        self.updates.append((range_name, values))

    def batch_update(self, data, value_input_option):
        self.updates.extend(data)

    def append_rows(self, rows, value_input_option):
        self.appended.extend(rows)


class FakeSpreadsheet:
    def __init__(self, worksheet=None):
        self.sheet = worksheet
        self.created = None

    def worksheet(self, title):
        if self.sheet is None:
            raise gspread.exceptions.WorksheetNotFound(title)
        return self.sheet

    def add_worksheet(self, title, rows, cols):
        self.sheet = FakeWorksheet()
        self.created = (title, rows, cols)
        return self.sheet


class PriceCacheTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "ticker": "FPT",
            "date": "2026-11-09",
            "open": 100000.0,
            "high": 101000.0,
            "low": 99000.0,
            "close": 100500.0,
            "volume": 123456.0,
        }

    def test_creates_cache_tab_and_appends_new_row(self):
        spreadsheet = FakeSpreadsheet()
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            added, updated = upsert_prices_cache([self.record])

        self.assertEqual(spreadsheet.created, ("Prices_Cache", 1000, 7))
        self.assertEqual((added, updated), (1, 0))
        self.assertEqual(spreadsheet.sheet.updates[0][0], "A1:G1")
        self.assertEqual(spreadsheet.sheet.appended[0][:2], ["FPT", "2026-11-09"])

    def test_updates_existing_ticker_date_without_adding_duplicate(self):
        values = [
            ["ticker", "date", "open", "high", "low", "close", "volume"],
            ["FPT", "2026-11-09", "100000.0", "101000.0", "99000.0", "100000.0", "123456.0"],
        ]
        spreadsheet = FakeSpreadsheet(FakeWorksheet(values))
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            added, updated = upsert_prices_cache([self.record])

        self.assertEqual((added, updated), (0, 1))
        self.assertEqual(spreadsheet.sheet.appended, [])
        self.assertEqual(spreadsheet.sheet.updates[0]["range"], "A2:G2")

    def test_empty_update_does_not_open_sheet(self):
        with patch("src.sheets.open_spreadsheet") as open_sheet:
            self.assertEqual(upsert_prices_cache([]), (0, 0))
        open_sheet.assert_not_called()


if __name__ == "__main__":
    unittest.main()
