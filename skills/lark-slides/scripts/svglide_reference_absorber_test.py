# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_reference_absorber


def write_text(path: Path, text: str = "fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, object]) -> None:
    write_text(path, json.dumps(payload))


def build_beautiful_fixture(root: Path) -> None:
    write_json(
        root / "index.json",
        {
            "schema_version": 1,
            "template_count": 1,
            "templates": [
                {
                    "slug": "blue-professional",
                    "name": "Blue Professional",
                    "mood": ["professional"],
                    "scheme": "light",
                    "slide_count": 1,
                }
            ],
        },
    )
    write_text(root / "AGENTS.md", "Use slug for template folders.")
    write_text(root / "README.md", "Template library.")
    write_text(root / "LICENSE", "MIT")
    write_json(root / "templates/blue-professional/template.json", {"slug": "blue-professional"})
    write_text(root / "templates/blue-professional/template.html", "<html></html>")
    write_text(root / "templates/blue-professional/design.md", "colors: blue")
    write_text(root / "screenshots/blue-professional-1.png", "not really a png")


def good_abstraction_record(item_id: str) -> dict[str, object]:
    return {
        "source_item_id": item_id,
        "absorbed_as": ["template_candidate"],
        "svglide_asset_ids": ["template.blue_professional_fixture"],
        "non_copying_transform": "Reuse the layout intent as an SVGlide-owned template; do not copy source HTML/CSS.",
        "forbidden_usage": ["do_not_embed_reference_html_or_css"],
        "canvas_spec_fixtures": ["skills/lark-slides/scripts/fixtures/svglide_artboard/p0a-cover/02-plan/slide_plan.json"],
    }


def attach_abstraction_record(payload: dict[str, object], root: Path, record: dict[str, object]) -> dict[str, object]:
    items = payload["items"]
    assert isinstance(items, list)
    item = items[0]
    assert isinstance(item, dict)
    item_id = item["id"]
    assert isinstance(item_id, str)
    record_path = root / "absorptions" / f"{item_id}.json"
    write_json(record_path, record)
    item["disposition"] = "absorbed"
    item["absorption_record"] = str(record_path)
    return item


class SVGlideReferenceAbsorberTest(unittest.TestCase):
    def test_beautiful_census_uses_slug_paths_and_records_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})

            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)

            paths = {item["source_path"] for item in payload["items"]}
            self.assertIn(str((source / "templates/blue-professional/template.json").resolve()), paths)
            self.assertFalse(any("Blue Professional" in path for path in paths))
            beautiful_meta = payload["repos"][0]
            drift_codes = {item["code"] for item in beautiful_meta["drift"]}
            self.assertIn("beautiful_templates_len_drift", drift_codes)
            self.assertIn("beautiful_screenshots_count_drift", drift_codes)

            result = svglide_reference_absorber.validate_inventory_payload(payload, specs)
            self.assertEqual(result["status"], "passed")

    def test_check_inventory_detects_required_field_path_hash_and_family_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})
            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)
            bad_payload = copy.deepcopy(payload)
            bad_payload["items"][0].pop("priority")
            bad_payload["items"][1]["source_hash"] = "sha256:stale"
            bad_payload["items"][2]["source_path"] = "relative/path"
            bad_payload["items"][3].pop("disposition")
            bad_payload["coverage"] = [
                item for item in bad_payload["coverage"] if item["source_family"] != "screenshot"
            ]

            result = svglide_reference_absorber.validate_inventory_payload(bad_payload, specs)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("missing_priority", codes)
            self.assertIn("source_hash_stale", codes)
            self.assertIn("source_path_not_absolute", codes)
            self.assertIn("missing_disposition", codes)
            self.assertIn("source_family_coverage_missing", codes)

    def test_check_absorption_requires_record_fixture_and_duplicate_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})
            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)
            payload["items"][0]["disposition"] = "absorbed"
            payload["items"][1]["disposition"] = "duplicate_of"

            result = svglide_reference_absorber.validate_absorption_payload(payload, specs)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("absorbed_missing_abstraction_record", codes)
            self.assertIn("duplicate_missing_canonical", codes)

    def test_check_absorption_accepts_good_abstraction_record_with_fixture_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})
            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)
            item = payload["items"][0]
            attach_abstraction_record(payload, tmp, good_abstraction_record(item["id"]))

            result = svglide_reference_absorber.validate_absorption_payload(payload, specs)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["absorbed_count"], 1)

    def test_check_absorption_rejects_abstraction_source_item_id_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})
            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)
            item = payload["items"][0]
            record = good_abstraction_record(item["id"])
            record["source_item_id"] = "beautiful-html-templates.template.wrong"
            attach_abstraction_record(payload, tmp, record)

            result = svglide_reference_absorber.validate_absorption_payload(payload, specs)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("abstraction_source_item_id_mismatch", codes)

    def test_check_absorption_rejects_missing_required_semantic_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})
            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)
            item = payload["items"][0]
            attach_abstraction_record(
                payload,
                tmp,
                {
                    "source_item_id": item["id"],
                    "canvas_spec_fixtures": [
                        "skills/lark-slides/scripts/fixtures/svglide_artboard/p0a-cover/02-plan/slide_plan.json"
                    ],
                },
            )

            result = svglide_reference_absorber.validate_absorption_payload(payload, specs)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("abstraction_required_field_missing", codes)

    def test_check_absorption_rejects_invalid_required_list_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})
            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)
            item = payload["items"][0]
            record = good_abstraction_record(item["id"])
            record["absorbed_as"] = ["template_candidate", ""]
            record["svglide_asset_ids"] = ["template.blue_professional_fixture", 42]
            record["forbidden_usage"] = ["do_not_embed_reference_html_or_css", None]
            attach_abstraction_record(payload, tmp, record)

            result = svglide_reference_absorber.validate_absorption_payload(payload, specs)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("abstraction_required_list_item_invalid", codes)

    def test_check_absorption_final_disposition_mode_rejects_pending_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})
            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)

            result = svglide_reference_absorber.validate_absorption_payload(
                payload,
                specs,
                require_final_disposition=True,
            )

            self.assertEqual(result["status"], "failed")
            self.assertGreater(result["summary"]["pending_count"], 0)
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("pending_disposition", codes)

    def test_check_absorption_cli_require_final_disposition_flag_rejects_pending_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})
            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)
            inventory_path = tmp / "inventory.json"
            write_json(inventory_path, payload)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = svglide_reference_absorber.main(
                    ["check-absorption", str(inventory_path), "--require-final-disposition"]
                )

            self.assertEqual(exit_code, 1)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["status"], "failed")
            self.assertGreater(result["summary"]["pending_count"], 0)

    def test_preview_disposition_suggests_safe_final_groups_without_editing_inventory(self) -> None:
        payload = {
            "items": [
                {
                    "id": "beautiful-html-templates.template.blue-professional.template.html",
                    "source_repo": "beautiful-html-templates",
                    "source_family": "template_html",
                    "disposition": "pending",
                    "runtime_policy": "forbidden_external_runtime_dependency",
                    "owner_target": "layout_planner",
                    "source_repo_relative_path": "templates/blue-professional/template.html",
                },
                {
                    "id": "beautiful-html-templates.screenshot.blue-professional-1",
                    "source_repo": "beautiful-html-templates",
                    "source_family": "screenshot",
                    "disposition": "pending",
                    "runtime_policy": "reference_only_no_runtime_dependency",
                    "owner_target": "visual_acceptance",
                    "source_repo_relative_path": "screenshots/blue-professional-1.png",
                },
                {
                    "id": "PosterGen.data_samples.data.demo.paper.pdf",
                    "source_repo": "PosterGen",
                    "source_family": "data_samples",
                    "disposition": "pending",
                    "runtime_policy": "reference_only_no_runtime_dependency",
                    "owner_target": "vf5_benchmark",
                    "source_repo_relative_path": "data/demo/paper.pdf",
                },
            ]
        }
        original_dispositions = [item["disposition"] for item in payload["items"]]
        result = svglide_reference_absorber.preview_disposition_payload(payload)

        self.assertEqual(["pending", "pending", "pending"], original_dispositions)
        self.assertEqual([item["disposition"] for item in payload["items"]], original_dispositions)
        suggestions = {item["id"]: item for item in result["suggestions"]}
        self.assertEqual(
            "forbidden_runtime_dependency",
            suggestions["beautiful-html-templates.template.blue-professional.template.html"]["suggested_disposition"],
        )
        self.assertEqual(
            "duplicate_of",
            suggestions["beautiful-html-templates.screenshot.blue-professional-1"]["suggested_disposition"],
        )
        self.assertEqual(
            "beautiful-html-templates.template.blue-professional.design.md",
            suggestions["beautiful-html-templates.screenshot.blue-professional-1"]["canonical_item_id"],
        )
        self.assertIn("absorption_record", suggestions["beautiful-html-templates.screenshot.blue-professional-1"])
        self.assertEqual(
            "not_applicable_to_svglide",
            suggestions["PosterGen.data_samples.data.demo.paper.pdf"]["suggested_disposition"],
        )

    def test_apply_disposition_payload_writes_safe_final_fields_without_mutating_input(self) -> None:
        payload = {
            "summary": {"by_disposition": {"absorbed": 1, "pending": 4}},
            "items": [
                {
                    "id": "beautiful-html-templates.template.blue-professional.design.md",
                    "source_repo": "beautiful-html-templates",
                    "source_family": "design_doc",
                    "source_type": "template",
                    "disposition": "absorbed",
                    "absorption_record": "skills/lark-slides/references/absorptions/beautiful-html-templates/blue-professional.executive-dashboard.json",
                },
                {
                    "id": "beautiful-html-templates.screenshot.blue-professional-1",
                    "source_repo": "beautiful-html-templates",
                    "source_family": "screenshot",
                    "source_type": "quality_rule",
                    "disposition": "pending",
                    "runtime_policy": "reference_only_no_runtime_dependency",
                    "owner_target": "visual_acceptance",
                },
                {
                    "id": "beautiful-html-templates.template.blue-professional.template.html",
                    "source_repo": "beautiful-html-templates",
                    "source_family": "template_html",
                    "source_type": "layout",
                    "disposition": "pending",
                    "runtime_policy": "forbidden_external_runtime_dependency",
                    "owner_target": "layout_planner",
                },
                {
                    "id": "PosterGen.data_samples.data.demo.paper.pdf",
                    "source_repo": "PosterGen",
                    "source_family": "data_samples",
                    "source_type": "benchmark_route",
                    "disposition": "pending",
                    "runtime_policy": "reference_only_no_runtime_dependency",
                    "owner_target": "vf5_benchmark",
                },
                {
                    "id": "open-design.design-template-guidance.cards.md",
                    "source_repo": "open-design",
                    "source_family": "design_template_guidance",
                    "source_type": "component",
                    "disposition": "pending",
                    "runtime_policy": "reference_only_no_runtime_dependency",
                    "owner_target": "component",
                },
            ],
        }

        updated, result = svglide_reference_absorber.apply_disposition_payload(payload)

        self.assertEqual("pending", payload["items"][1]["disposition"])
        self.assertEqual(4, result["summary"]["applied_count"])
        self.assertEqual(0, result["summary"]["remaining_pending_count"])
        updated_by_id = {item["id"]: item for item in updated["items"]}
        screenshot = updated_by_id["beautiful-html-templates.screenshot.blue-professional-1"]
        self.assertEqual("duplicate_of", screenshot["disposition"])
        self.assertEqual(
            "beautiful-html-templates.template.blue-professional.design.md",
            screenshot["canonical_item_id"],
        )
        self.assertEqual("pass", screenshot["review_status"])
        html = updated_by_id["beautiful-html-templates.template.blue-professional.template.html"]
        self.assertEqual("forbidden_runtime_dependency", html["disposition"])
        blocked = updated_by_id["open-design.design-template-guidance.cards.md"]
        self.assertEqual("blocked_with_reason", blocked["disposition"])
        self.assertEqual("blocked", blocked["review_status"])

    def test_apply_disposition_cli_dry_run_requires_final_disposition_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source_files = {
                "canonical.md": "colors: blue",
                "shot.png": "not really a png",
                "template.html": "<html></html>",
                "paper.pdf": "%PDF placeholder",
                "cards.md": "component cards",
            }
            for relative_path, text in source_files.items():
                write_text(tmp / relative_path, text)
            record_path = tmp / "blue-professional.executive-dashboard.json"
            write_json(
                record_path,
                good_abstraction_record("beautiful-html-templates.template.blue-professional.design.md"),
            )

            def item(item_id: str, relative_path: str, **fields: object) -> dict[str, object]:
                path = tmp / relative_path
                return {
                    "id": item_id,
                    "source_repo": fields.pop("source_repo"),
                    "source_family": fields.pop("source_family"),
                    "source_path": str(path.resolve()),
                    "source_hash": svglide_reference_absorber.source_hash(path),
                    "priority": fields.pop("priority", "P0"),
                    "source_type": fields.pop("source_type"),
                    "disposition": fields.pop("disposition", "pending"),
                    **fields,
                }

            payload = {
                "expected_repos": [],
                "repos": [
                    {
                        "source_repo": "beautiful-html-templates",
                        "drift": [
                            {"code": "beautiful_template_folders_count_drift"},
                            {"code": "beautiful_template_json_count_drift"},
                            {"code": "beautiful_template_html_count_drift"},
                            {"code": "beautiful_design_md_count_drift"},
                            {"code": "beautiful_screenshots_count_drift"},
                        ],
                    }
                ],
                "coverage": [],
                "summary": {},
                "items": [
                    item(
                        "beautiful-html-templates.template.blue-professional.design.md",
                        "canonical.md",
                        source_repo="test-reference",
                        source_family="design_doc",
                        source_type="template",
                        disposition="absorbed",
                        absorption_record=str(record_path),
                    ),
                    item(
                        "beautiful-html-templates.screenshot.blue-professional-1",
                        "shot.png",
                        source_repo="test-reference",
                        source_family="screenshot",
                        source_type="quality_rule",
                        runtime_policy="reference_only_no_runtime_dependency",
                        owner_target="visual_acceptance",
                    ),
                    item(
                        "beautiful-html-templates.template.blue-professional.template.html",
                        "template.html",
                        source_repo="test-reference",
                        source_family="template_html",
                        source_type="layout",
                        runtime_policy="forbidden_external_runtime_dependency",
                        owner_target="layout_planner",
                    ),
                    item(
                        "PosterGen.data_samples.data.demo.paper.pdf",
                        "paper.pdf",
                        source_repo="PosterGen",
                        source_family="data_samples",
                        source_type="benchmark_route",
                        runtime_policy="reference_only_no_runtime_dependency",
                        owner_target="vf5_benchmark",
                    ),
                    item(
                        "open-design.design-template-guidance.cards.md",
                        "cards.md",
                        source_repo="open-design",
                        source_family="design_template_guidance",
                        source_type="component",
                        runtime_policy="reference_only_no_runtime_dependency",
                        owner_target="component",
                    ),
                ],
            }
            inventory_path = tmp / "inventory.json"
            write_json(inventory_path, payload)
            original_context_map = svglide_reference_absorber.absorption_context_record_map
            svglide_reference_absorber.absorption_context_record_map = lambda records_root=None: {
                "beautiful-html-templates.screenshot.blue-professional-1": {
                    "absorption_record": str(record_path),
                    "canonical_item_id": "beautiful-html-templates.template.blue-professional.design.md",
                    "relation": "context_ref",
                }
            }
            try:
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    exit_code = svglide_reference_absorber.main(
                        ["apply-disposition", str(inventory_path), "--dry-run", "--pretty"]
                    )
            finally:
                svglide_reference_absorber.absorption_context_record_map = original_context_map

            self.assertEqual(exit_code, 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual("passed", result["status"])
            self.assertEqual(4, result["summary"]["applied_count"])
            self.assertEqual(0, result["final_check"]["pending_count"])
            persisted = json.loads(inventory_path.read_text(encoding="utf-8"))
            self.assertEqual("pending", persisted["items"][1]["disposition"])

    def test_report_records_phase_zero_baseline_and_inventory_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "beautiful-html-templates"
            build_beautiful_fixture(source)
            specs = svglide_reference_absorber.build_repo_specs({"beautiful-html-templates": source})
            payload = svglide_reference_absorber.census_repos("beautiful-html-templates", specs)

            report = svglide_reference_absorber.build_report(
                payload,
                svglide_reference_absorber.validate_inventory_payload(payload, specs),
                svglide_reference_absorber.validate_absorption_payload(payload, specs),
            )

            self.assertIn("Coordinator Baseline", report)
            self.assertIn("551f333563f5a26ec9568ad8090a0f14a1a419c7", report)
            self.assertIn("Current Dirty File Attribution", report)
            self.assertIn("Repo Provenance", report)
            self.assertIn("license_file", report)
            self.assertIn("slug", report)
            self.assertIn("no asset implementation", report)
            self.assertIn("does not mean absorption is complete", report)
            self.assertIn("real_benchmark=true", report)
            self.assertIn("trusted_provider_evidence", report)
            self.assertIn("forbidden runtime dependency disposition items", report)
            self.assertIn("forbidden runtime boundary items checked by `check-absorption`", report)

    def test_status_path_preserves_leading_space_status_lines(self) -> None:
        self.assertEqual(
            "skills/lark-slides/SKILL.md",
            svglide_reference_absorber.status_path(" M skills/lark-slides/SKILL.md"),
        )
        self.assertEqual(
            "skills/lark-slides/references/svglide-reference-source-inventory.json",
            svglide_reference_absorber.status_path("?? skills/lark-slides/references/svglide-reference-source-inventory.json"),
        )

    def test_runtime_traceability_accepts_all_runtime_asset_areas(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            old_root = svglide_reference_absorber.REPO_ROOT
            svglide_reference_absorber.REPO_ROOT = root
            try:
                record_path = "skills/lark-slides/references/absorptions/svglide-baseline/all.json"
                write_json(
                    root / record_path,
                    {
                        "source_item_id": "svglide-baseline.all",
                        "absorbed_as": ["owned_baseline_runtime_asset"],
                        "svglide_asset_ids": [
                            "template.cover",
                            "component.Title",
                            "layout.hero-cover",
                            "theme.dark",
                            "image_strategy.figure",
                            "chart_strategy.bars",
                        ],
                        "non_copying_transform": "Owned baseline assets keep local SVGlide abstractions.",
                        "forbidden_usage": ["do_not_import_external_runtime"],
                        "canvas_spec_fixtures": ["skills/lark-slides/scripts/fixtures/svglide_artboard/golden/cover.canvas-spec.json"],
                    },
                )
                write_json(root / "skills/lark-slides/scripts/fixtures/svglide_artboard/golden/cover.canvas-spec.json", {"ok": True})
                trace = ["svglide-baseline.all"]
                write_json(
                    root / "skills/lark-slides/references/svglide-template-registry.json",
                    {"templates": [{"id": "cover", "status": "active", "source_trace": trace, "abstraction_record": record_path}]},
                )
                write_json(
                    root / "skills/lark-slides/references/svglide-component-registry.json",
                    {"components": [{"id": "Title", "status": "active", "source_trace": trace, "abstraction_record": record_path}]},
                )
                write_json(
                    root / "skills/lark-slides/references/svglide-layout-archetypes.json",
                    {"archetypes": [{"id": "hero-cover", "status": "active", "source_trace": trace, "abstraction_record": record_path}]},
                )
                theme_file = "skills/lark-slides/scripts/artboard_renderer/themes/dark.json"
                write_json(
                    root / "skills/lark-slides/scripts/artboard_renderer/themes/registry.json",
                    {"themes": [{"id": "dark", "status": "active", "path": theme_file, "source_trace": trace, "abstraction_record": record_path}]},
                )
                write_json(
                    root / theme_file,
                    {"theme_id": "dark", "source_trace": trace, "abstraction_record": record_path},
                )
                write_json(
                    root / "skills/lark-slides/references/svglide-image-strategies.json",
                    {"strategies": [{"id": "figure", "status": "active", "source_trace": trace, "abstraction_record": record_path}]},
                )
                write_json(
                    root / "skills/lark-slides/references/svglide-chart-strategies.json",
                    {"strategies": [{"id": "bars", "status": "active", "source_trace": trace, "abstraction_record": record_path}]},
                )

                result = svglide_reference_absorber.validate_runtime_traceability()

                self.assertEqual("passed", result["status"])
                self.assertEqual(6, result["summary"]["active_runtime_asset_count"])
                self.assertEqual(6, result["summary"]["traced_runtime_asset_count"])
            finally:
                svglide_reference_absorber.REPO_ROOT = old_root

    def test_runtime_traceability_requires_asset_id_in_abstraction_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            old_root = svglide_reference_absorber.REPO_ROOT
            svglide_reference_absorber.REPO_ROOT = root
            try:
                record_path = "skills/lark-slides/references/absorptions/svglide-baseline/templates.json"
                write_json(
                    root / record_path,
                    {
                        "source_item_id": "svglide-baseline.templates",
                        "absorbed_as": ["owned_baseline_runtime_asset"],
                        "svglide_asset_ids": ["template.other"],
                        "non_copying_transform": "Owned baseline assets keep local SVGlide abstractions.",
                        "forbidden_usage": ["do_not_import_external_runtime"],
                        "template_guardrail_records": ["skills/lark-slides/references/svglide-template-registry.json"],
                    },
                )
                write_json(
                    root / "skills/lark-slides/references/svglide-template-registry.json",
                    {
                        "templates": [
                            {
                                "id": "cover",
                                "status": "active",
                                "source_trace": ["svglide-baseline.templates"],
                                "abstraction_record": record_path,
                            }
                        ]
                    },
                )
                for rel, key in [
                    ("skills/lark-slides/references/svglide-component-registry.json", "components"),
                    ("skills/lark-slides/references/svglide-layout-archetypes.json", "archetypes"),
                    ("skills/lark-slides/scripts/artboard_renderer/themes/registry.json", "themes"),
                    ("skills/lark-slides/references/svglide-image-strategies.json", "strategies"),
                    ("skills/lark-slides/references/svglide-chart-strategies.json", "strategies"),
                ]:
                    write_json(root / rel, {key: []})

                result = svglide_reference_absorber.validate_runtime_traceability()

                self.assertEqual("failed", result["status"])
                self.assertEqual("runtime_trace_asset_not_in_record", result["issues"][0]["code"])
            finally:
                svglide_reference_absorber.REPO_ROOT = old_root


if __name__ == "__main__":
    unittest.main()
