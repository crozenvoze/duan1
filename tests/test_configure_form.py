"""Tests for safely generating the ignored local web-form configuration."""

import unittest

from src.configure_form import render_form_config


class FormConfigTests(unittest.TestCase):
    def test_renders_valid_url_and_escapes_values_as_javascript_strings(self):
        config = render_form_config(
            "https://script.google.com/macros/s/test-deployment/exec",
            'a"b\\c' + "x" * 32,
        )
        self.assertIn('"https://script.google.com/macros/s/test-deployment/exec"', config)
        self.assertIn(r'"a\"b\\c', config)
        self.assertTrue(config.startswith("window.APP_CONFIG = {"))

    def test_rejects_non_exec_url_and_short_token(self):
        with self.assertRaisesRegex(ValueError, "kết thúc bằng /exec"):
            render_form_config("https://example.com/not-app", "x" * 40)
        with self.assertRaisesRegex(ValueError, "ít nhất 32 ký tự"):
            render_form_config(
                "https://script.google.com/macros/s/test-deployment/exec",
                "short",
            )


if __name__ == "__main__":
    unittest.main()
