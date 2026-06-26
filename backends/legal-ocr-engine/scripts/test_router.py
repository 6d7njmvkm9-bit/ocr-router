#!/usr/bin/env python3
"""Routing tests: PaddleOCR first when supported."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from common import build_source_info
from router import choose_backend


class RouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.source_path = Path(self.tempdir.name) / "evidence.pdf"
        self.source_path.write_bytes(b"%PDF-test")
        self.source = build_source_info(str(self.source_path))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_direct_ocr_uses_paddle_then_mineru_for_local_pdf(self) -> None:
        with patch("router.resolve_mineru_token", return_value="mineru-token"):
            route = choose_backend(
                self.source,
                {
                    "PADDLE_OCR_API_ENDPOINT": "https://paddle.example/jobs",
                    "PADDLE_OCR_API_KEY": "paddle-token",
                },
                route_path="direct_ocr",
            )
        self.assertEqual(route.candidates, ["paddle", "mineru"])
        self.assertTrue(route.fallback_allowed)

    def test_complex_parse_uses_paddle_then_mineru_for_local_pdf(self) -> None:
        with patch("router.resolve_mineru_token", return_value="mineru-token"):
            route = choose_backend(
                self.source,
                {
                    "PADDLE_OCR_API_ENDPOINT": "https://paddle.example/jobs",
                    "PADDLE_OCR_API_KEY": "paddle-token",
                },
                route_path="complex_parse",
            )
        self.assertEqual(route.candidates, ["paddle", "mineru"])
        self.assertTrue(route.fallback_allowed)

    def test_auto_uses_paddle_for_local_pdf_when_both_are_configured(self) -> None:
        with patch("router.resolve_mineru_token", return_value="mineru-token"):
            route = choose_backend(
                self.source,
                {
                    "PADDLE_OCR_API_ENDPOINT": "https://paddle.example/jobs",
                    "PADDLE_OCR_API_KEY": "paddle-token",
                },
            )
        self.assertEqual(route.candidates, ["paddle", "mineru"])
        self.assertTrue(route.fallback_allowed)

    def test_office_file_uses_mineru_when_both_are_configured(self) -> None:
        source_path = Path(self.tempdir.name) / "evidence.docx"
        source_path.write_bytes(b"docx-test")
        source = build_source_info(str(source_path))
        with patch("router.resolve_mineru_token", return_value="mineru-token"):
            route = choose_backend(
                source,
                {
                    "PADDLE_OCR_API_ENDPOINT": "https://paddle.example/jobs",
                    "PADDLE_OCR_API_KEY": "paddle-token",
                },
            )
        self.assertEqual(route.candidates, ["mineru"])
        self.assertFalse(route.fallback_allowed)

    def test_explicit_backend_is_not_rewritten_by_route_path(self) -> None:
        with patch("router.resolve_mineru_token", return_value="mineru-token"):
            route = choose_backend(
                self.source,
                {
                    "PADDLE_OCR_API_ENDPOINT": "https://paddle.example/jobs",
                    "PADDLE_OCR_API_KEY": "paddle-token",
                },
                explicit_backend="mineru",
                route_path="direct_ocr",
            )
        self.assertEqual(route.candidates, ["mineru"])
        self.assertFalse(route.fallback_allowed)

    def test_paddle_only_when_mineru_token_is_missing(self) -> None:
        with patch("router.resolve_mineru_token", return_value=""):
            route = choose_backend(
                self.source,
                {
                    "PADDLE_OCR_API_ENDPOINT": "https://paddle.example/jobs",
                    "PADDLE_OCR_API_KEY": "paddle-token",
                },
            )
        self.assertEqual(route.candidates, ["paddle"])
        self.assertFalse(route.fallback_allowed)


if __name__ == "__main__":
    unittest.main()
