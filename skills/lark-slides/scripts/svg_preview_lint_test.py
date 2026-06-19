# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svg_preview_lint


class SvgPreviewLintTest(unittest.TestCase):
    def test_reports_safe_area_debug_rect(self) -> None:
        html = """
        <html><body>
          <svg width="960" height="540" viewBox="0 0 960 540">
            <rect width="960" height="540" fill="#F5F1EE"/>
            <rect x="48" y="40" width="864" height="460" fill="none" stroke="#0E5A3C" stroke-opacity="0.12"/>
          </svg>
        </body></html>
        """
        result = svg_preview_lint.lint_text(html, "preview.html")
        codes = [issue["code"] for issue in result["page_issues"]]
        self.assertIn("preview_safe_area_debug_rect_visible", codes)
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["action"], "repair_and_rerun")

    def test_ignores_hidden_debug_guide(self) -> None:
        html = """
        <svg width="960" height="540" viewBox="0 0 960 540">
          <rect id="safe-area-guide" x="48" y="40" width="864" height="460" fill="none" stroke="#0E5A3C" style="display:none"/>
        </svg>
        """
        result = svg_preview_lint.lint_text(html, "preview.html")
        codes = [issue["code"] for issue in result["page_issues"]]
        self.assertNotIn("preview_debug_guide_visible", codes)
        self.assertNotIn("preview_safe_area_debug_rect_visible", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_reports_tight_chinese_text_and_big_number_boxes(self) -> None:
        html = """
        <svg width="960" height="540" viewBox="0 0 960 540">
          <foreignObject x="102" y="358" width="110" height="46">
            <div xmlns="http://www.w3.org/1999/xhtml" class="t body-strong center">锁定重点客户清单</div>
          </foreignObject>
          <foreignObject x="654" y="194" width="90" height="40">
            <div xmlns="http://www.w3.org/1999/xhtml" class="t metric-light">+100</div>
          </foreignObject>
        </svg>
        """
        result = svg_preview_lint.lint_text(html, "preview.html")
        codes = [issue["code"] for issue in result["page_issues"]]
        self.assertIn("preview_text_overflow_risk", codes)
        self.assertIn("preview_big_number_box_tight", codes)
        self.assertGreaterEqual(result["summary"]["error_count"], 2)

    def test_reports_substantial_text_box_overlap_as_error(self) -> None:
        html = """
        <svg width="960" height="540" viewBox="0 0 960 540">
          <foreignObject x="100" y="100" width="220" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:16px;line-height:1.3;">第一段文本</div>
          </foreignObject>
          <foreignObject x="120" y="110" width="220" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:16px;line-height:1.3;">第二段文本</div>
          </foreignObject>
        </svg>
        """
        result = svg_preview_lint.lint_text(html, "preview.html")
        codes = [issue["code"] for issue in result["page_issues"]]
        self.assertIn("preview_text_box_overlap", codes)
        self.assertGreaterEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["action"], "repair_and_rerun")

    def test_reports_no_svg_pages(self) -> None:
        result = svg_preview_lint.lint_text("<html><body>No slides</body></html>", "preview.html")
        codes = [issue["code"] for issue in result["page_issues"]]
        self.assertIn("preview_no_svg_pages", codes)
        self.assertEqual(result["action"], "repair_and_rerun")

    def test_accepts_roomy_text_boxes(self) -> None:
        html = """
        <svg width="960" height="540" viewBox="0 0 960 540">
          <foreignObject x="80" y="80" width="360" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;line-height:1.35;">年度目标拆解清晰</div>
          </foreignObject>
        </svg>
        """
        result = svg_preview_lint.lint_text(html, "preview.html")
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["action"], "create_live")


if __name__ == "__main__":
    unittest.main()
