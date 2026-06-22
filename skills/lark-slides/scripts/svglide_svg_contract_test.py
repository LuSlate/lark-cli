# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_svg_contract as contract


class SVGlideSvgContractTest(unittest.TestCase):
    def test_root_attrs_include_slide_namespace_role_and_contract_version(self) -> None:
        attrs = contract.svg_root_attrs({"width": 960, "height": 540})

        self.assertEqual(attrs["xmlns:slide"], contract.SLIDE_NS)
        self.assertEqual(attrs["slide:role"], "slide")
        self.assertEqual(attrs["slide:contract-version"], contract.CONTRACT_VERSION)
        self.assertEqual(attrs["width"], "960")
        self.assertEqual(attrs["height"], "540")

    def test_shape_attrs_only_emit_shape_role(self) -> None:
        self.assertEqual(contract.shape_attrs(), {"slide:role": "shape"})

    def test_image_attrs_only_emit_image_role(self) -> None:
        self.assertEqual(contract.image_attrs(), {"slide:role": "image"})

    def test_text_shape_attrs_emit_shape_role_and_text_shape_type(self) -> None:
        self.assertEqual(contract.text_shape_attrs(), {"slide:role": "shape", "slide:shape-type": "text"})

    def test_chart_marker_attrs_emit_chart_role_and_ref(self) -> None:
        self.assertEqual(contract.chart_marker_attrs("chart-1"), {"slide:role": "chart", "slide:chart-ref": "chart-1"})

    def test_svg_attrs_escapes_values_and_keeps_stable_order(self) -> None:
        attrs = contract.svg_attrs({"id": 'a"b', "data-label": "A&B<C", "skip": None})

        self.assertEqual(attrs, 'id="a&quot;b" data-label="A&amp;B&lt;C"')

    def test_no_helper_emits_protocol_outside_compile_boundary_by_default(self) -> None:
        # This helper centralizes protocol attributes but has no side effects and no runner-stage coupling.
        self.assertFalse(hasattr(contract, "inject_into_svg"))
        self.assertFalse(hasattr(contract, "prepare_project"))


if __name__ == "__main__":
    unittest.main()
