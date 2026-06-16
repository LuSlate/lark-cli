# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import svglide_asset_selector as selector


def resource(
    resource_id: str,
    *,
    kind: str = "chart_template",
    tags: list[str] | None = None,
    summary: str = "business strategy roadmap dashboard chart",
    activation_status: str = "active",
    license_status: str = "clear",
    protocol_compatibility: str = "svglide_compatible",
    normalized_fixture: str = "fixtures/demo.svg",
) -> dict:
    return {
        "id": resource_id,
        "source_path": f"ppt-master/{resource_id}.svg",
        "kind": kind,
        "summary": summary,
        "selection_tags": tags or ["business", "strategy", "roadmap", "chart"],
        "activation_status": activation_status,
        "license_status": license_status,
        "protocol_compatibility": protocol_compatibility,
        "copy_policy": "derive_contract_only",
        "normalized_primitives": ["slide_role_shape"],
        "normalized_fixture": normalized_fixture,
    }


def asset_map(resources: list[dict]) -> dict:
    return {
        "schema_version": "svglide-ppt-master-asset-map/v1",
        "summary": {"digests": {"all_source_files": "fixture"}},
        "resources": resources,
    }


class SVGlideAssetSelectorTest(unittest.TestCase):
    def test_reference_only_is_excluded_from_production(self) -> None:
        data = asset_map(
            [
                resource(
                    "chart.reference_only",
                    activation_status="active",
                    license_status="reference_only",
                    tags=["business", "strategy"],
                ),
                resource("chart.ready", activation_status="validated", license_status="clear", tags=["business", "strategy"]),
            ]
        )

        selected = selector.select_assets(data, brief="business strategy", lane="production")

        self.assertEqual([asset["id"] for asset in selected["selected_assets"]], ["chart.ready"])
        self.assertIn("license_not_production_ready", {asset["reason"] for asset in selected["excluded_assets"]})

    def test_rejected_assets_are_never_selected(self) -> None:
        data = asset_map(
            [
                resource("chart.rejected", activation_status="rejected", tags=["roadmap"]),
                resource("chart.ready", activation_status="validated", license_status="clear", tags=["roadmap"]),
            ]
        )

        selected = selector.select_assets(data, brief="roadmap", lane="authoring")

        self.assertEqual([asset["id"] for asset in selected["selected_assets"]], ["chart.ready"])
        self.assertIn("rejected_asset", {asset["reason"] for asset in selected["excluded_assets"]})

    def test_raw_unnormalized_assets_are_excluded_from_production(self) -> None:
        data = asset_map(
            [
                resource(
                    "chart.raw",
                    activation_status="active",
                    license_status="clear",
                    protocol_compatibility="needs_normalization",
                    normalized_fixture="",
                    tags=["dashboard"],
                ),
                resource("chart.ready", activation_status="active", license_status="clear", tags=["dashboard"]),
            ]
        )

        selected = selector.select_assets(data, brief="dashboard", lane="golden")

        self.assertEqual([asset["id"] for asset in selected["selected_assets"]], ["chart.ready"])
        self.assertIn("raw_asset_needs_normalization", {asset["reason"] for asset in selected["excluded_assets"]})

    def test_candidate_assets_are_allowed_only_outside_strict_lanes(self) -> None:
        data = asset_map([resource("chart.candidate", activation_status="candidate", license_status="reference_only", tags=["research"])])

        authoring = selector.select_assets(data, brief="research", lane="authoring")
        production = selector.select_assets(data, brief="research", lane="production")

        self.assertEqual([asset["id"] for asset in authoring["selected_assets"]], ["chart.candidate"])
        self.assertEqual(production["selected_assets"], [])
        self.assertIn("activation_status_not_production_ready", {asset["reason"] for asset in production["excluded_assets"]})

    def test_prompt_budget_caps_per_kind_and_total_context(self) -> None:
        resources = [
            resource(f"chart.{index}", tags=["business", "chart"], activation_status="validated", license_status="clear")
            for index in range(10)
        ]
        resources.extend(
            resource(
                f"layout.{index}",
                kind="layout_template",
                tags=["business", "layout"],
                activation_status="validated",
                license_status="clear",
            )
            for index in range(5)
        )
        data = asset_map(resources)

        selected = selector.select_assets(
            data,
            brief="business chart layout",
            lane="production",
            budget={"chart": 2, "layout": 2},
            max_total_assets=3,
        )

        self.assertLessEqual(selected["prompt_budget"]["total_selected"], 3)
        self.assertLessEqual(selected["prompt_budget"]["selected_per_kind"]["chart"], 2)
        self.assertLessEqual(selected["prompt_budget"]["selected_per_kind"]["layout"], 2)
        self.assertLess(selected["prompt_budget"]["estimated_prompt_tokens"], 500)
        self.assertNotIn("resources", selected)

    def test_brief_changes_selection_digest(self) -> None:
        data = asset_map(
            [
                resource(
                    "chart.roadmap",
                    tags=["roadmap"],
                    summary="roadmap milestones timeline",
                    activation_status="validated",
                    license_status="clear",
                ),
                resource(
                    "chart.market",
                    tags=["market"],
                    summary="market sizing and growth",
                    activation_status="validated",
                    license_status="clear",
                ),
            ]
        )

        roadmap = selector.select_assets(data, brief="roadmap", lane="production")
        market = selector.select_assets(data, brief="market", lane="production")

        self.assertNotEqual(roadmap["request_digest"], market["request_digest"])
        self.assertNotEqual(roadmap["selection_digest"], market["selection_digest"])
        self.assertEqual([asset["id"] for asset in roadmap["selected_assets"]], ["chart.roadmap"])
        self.assertEqual([asset["id"] for asset in market["selected_assets"]], ["chart.market"])


if __name__ == "__main__":
    unittest.main()
