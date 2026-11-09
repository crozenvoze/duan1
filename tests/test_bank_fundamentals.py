"""Tests for append-only storage of manually reviewed bank ratios."""

import unittest
from unittest.mock import patch

from src.bank_fundamentals import BANK_FUNDAMENTALS_HEADERS, write_bank_fundamental


class BankFundamentalsTests(unittest.TestCase):
    def test_writer_creates_tab_schema_and_appends_a_version(self):
        class Worksheet:
            def __init__(self):
                self.values = []
                self.appended = []
                self.updated = []

            def get_all_values(self):
                return self.values

            def update(self, range_name, values):
                self.updated.append((range_name, values))
                self.values = values

            def append_rows(self, rows, value_input_option):
                self.appended.extend(rows)

        class Spreadsheet:
            def __init__(self):
                self.created = None
                self.worksheet_value = Worksheet()

            def worksheet(self, title):
                from gspread.exceptions import WorksheetNotFound
                raise WorksheetNotFound(title)

            def add_worksheet(self, **kwargs):
                self.created = kwargs
                return self.worksheet_value

        spreadsheet = Spreadsheet()
        record = {"ticker": "vcb", "period": "2025-Q4", "nim": 0.03, "casa": None}
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            write_bank_fundamental(record)

        self.assertEqual(spreadsheet.created["title"], "Bank_Fundamentals")
        self.assertEqual(spreadsheet.worksheet_value.updated[0][1][0], BANK_FUNDAMENTALS_HEADERS)
        saved = spreadsheet.worksheet_value.appended[0]
        self.assertEqual(len(saved), len(BANK_FUNDAMENTALS_HEADERS))
        self.assertEqual(saved[BANK_FUNDAMENTALS_HEADERS.index("ticker")], "VCB")
        self.assertEqual(saved[BANK_FUNDAMENTALS_HEADERS.index("period")], "2025-Q4")
        self.assertEqual(saved[BANK_FUNDAMENTALS_HEADERS.index("casa")], "")
        self.assertTrue(saved[BANK_FUNDAMENTALS_HEADERS.index("saved_at")])

    def test_writer_rejects_wrong_existing_headers_without_overwriting(self):
        class Worksheet:
            def __init__(self):
                self.values = [["ticker", "period", "other"]]

            def get_all_values(self):
                return self.values

        class Spreadsheet:
            def worksheet(self, title):
                return Worksheet()

        with patch("src.sheets.open_spreadsheet", return_value=Spreadsheet()):
            with self.assertRaisesRegex(RuntimeError, "header khác schema"):
                write_bank_fundamental({"ticker": "VCB", "period": "2025"})


if __name__ == "__main__":
    unittest.main()
