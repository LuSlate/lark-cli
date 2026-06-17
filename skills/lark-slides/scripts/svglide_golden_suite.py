#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import copy
import json
import sys
from typing import Any


MANIFEST_SCHEMA_VERSION = "svglide-golden-suite-manifest/v1"

_GOLDEN_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "ai-capital-editorial",
        "theme_domain": "ai_infrastructure_finance",
        "prompt_summary": "Editorial deck about capital flows, compute commitments, and investor risk signals in the AI infrastructure cycle.",
        "expected_archetypes": [
            "cover",
            "editor_note",
            "kpi_cards",
            "bar_chart",
            "donut_chart",
            "sankey_chart",
            "bubble_chart",
            "closing",
        ],
        "required_evidence": [
            "design_pattern_usage_receipt",
            "component_report_with_chart_archetypes",
            "svg_preflight_pass",
        ],
    },
    {
        "case_id": "aksu-oasis-planning",
        "theme_domain": "urban_oasis_residential_planning",
        "prompt_summary": "Planning deck for an Aksu oasis living district, using water, seasonal blocks, and local identity as the organizing system.",
        "expected_archetypes": [
            "cover",
            "agenda",
            "section",
            "kpi_cards",
            "sankey_chart",
            "hub_spoke",
            "comparison_table",
            "closing",
        ],
        "required_evidence": [
            "domain_copy_retained",
            "agenda_numbered_path",
            "section_signal",
            "non_ai_topic_parameterization",
            "svg_preflight_pass",
        ],
    },
    {
        "case_id": "runtime-smoke",
        "theme_domain": "svglide_runtime_health",
        "prompt_summary": "Small deterministic smoke case for validating runtime composition, manifest plumbing, and receipt emission before larger regressions.",
        "expected_archetypes": [
            "cover",
            "kpi_cards",
            "bar_chart",
            "closing",
        ],
        "required_evidence": [
            "runtime_cache_written",
            "component_report_written",
            "svg_preflight_pass",
        ],
    },
)


def list_cases() -> list[dict[str, Any]]:
    return copy.deepcopy(list(_GOLDEN_CASES))


def build_manifest() -> dict[str, Any]:
    cases = list_cases()
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "case_count": len(cases),
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emit the built-in SVGlide golden suite case manifest.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list", help="list built-in golden suite cases")
    list_parser.add_argument("--json", action="store_true", help="emit the case manifest as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list":
        if not args.json:
            parser.error("list currently supports only --json")
        print(json.dumps(build_manifest(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
