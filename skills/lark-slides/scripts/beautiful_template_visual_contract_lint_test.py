#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import beautiful_template_visual_contract_lint as lint


SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def production_review_receipt_for_row(row: dict[str, object], *, status: str = "passed") -> dict[str, object]:
    evidence = {
        "renderer_module": row.get("renderer_module"),
        "golden_spec": row.get("golden_spec"),
        "fidelity_receipt": row.get("fidelity_receipt"),
        "page_family_smoke_deck": row.get("page_family_smoke_deck"),
        "page_family_smoke_receipt": row.get("page_family_smoke_receipt"),
        "visual_contract_path": row.get("visual_contract_path"),
    }
    golden_specs = row.get("page_variant_golden_specs")
    if isinstance(golden_specs, dict):
        evidence["page_variant_golden_specs"] = golden_specs
    input_hashes: dict[str, str] = {}
    for key, raw_path in evidence.items():
        if isinstance(raw_path, str) and raw_path:
            input_hashes[key] = file_sha256(lint.resolve_path(raw_path))
        elif isinstance(raw_path, dict):
            for variant_id, variant_path in raw_path.items():
                input_hashes[f"{key}.{variant_id}"] = file_sha256(lint.resolve_path(variant_path))
    return {
        "version": "svglide-beautiful-production-review/v1",
        "family_id": row.get("family_id"),
        "runtime_template_id": row.get("runtime_template_id"),
        "status": status,
        "review_type": "production_promotion",
        "review_decision": {
            "allow_production": status == "passed",
            "allow_default_selectable": status == "passed",
        },
        "required_evidence": evidence,
        "input_hashes": input_hashes,
        "scope": "production review receipt fixture for lint tests",
        "claim_boundary": "human/production review evidence only; does not replace fidelity or page-family smoke",
    }


def minimal_page_family_contract() -> dict[str, object]:
    return {
        "family_id": "blue-professional",
        "runtime_template_id": "executive-dashboard",
        "page_family": {
            "source_slide_count": 1,
            "core_page_roles": ["cover"],
            "production_minimum_roles": ["cover"],
        },
        "page_variants": {
            "cover": {
                "source_class": "layout-cover",
                "source_slide_index": 1,
                "page_role": "cover",
                "required_slots": ["title"],
                "source_refs": [
                    {
                        "path": "beautiful-html-templates/templates/blue-professional/template.html",
                        "selector_or_token": ".layout-cover",
                        "raw_value": "class=\"slide layout-cover active\"",
                    }
                ],
                "extraction_confidence": "css_extracted_from_template_html",
            }
        },
    }


class BeautifulTemplateVisualContractLintTest(unittest.TestCase):
    def test_real_matrix_covers_34_families_with_source_paths_and_contracts(self) -> None:
        issues = lint.validate_candidate_matrix()

        self.assertEqual([], issues)

    def test_real_matrix_strict_page_family_contracts_and_production_smoke_boundaries(self) -> None:
        issues = lint.validate_candidate_matrix(page_family_mode="strict")

        self.assertEqual([], issues)

    def test_lint_rejects_candidate_missing_source_evidence(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        family = matrix["candidates"][0]["family_id"]
        matrix["candidates"][0].pop("source_template_html", None)
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("candidate_required_field_missing", family, "source_template_html"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_rejects_contract_missing_required_sections(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        family = matrix["candidates"][0]["family_id"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            contract_path = tmp_path / "bad-contract.json"
            write_json(
                contract_path,
                {
                    "family_id": family,
                    "runtime_template_id": matrix["candidates"][0].get("runtime_template_id"),
                    "source": {key: matrix["candidates"][0].get(key) for key in sorted(lint.REQUIRED_SOURCE_FIELDS)},
                    "layout": {"summary": "present"},
                },
            )
            matrix["candidates"][0]["visual_contract_path"] = contract_path.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("contract_required_section_missing", family, "typography"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_page_family_contract_lint_rejects_missing_page_family(self) -> None:
        contract = minimal_page_family_contract()
        contract.pop("page_family")

        issues = lint.validate_page_family_contract(contract, family_id="blue-professional")

        self.assertIn(
            ("contract_page_family_missing", "blue-professional", "page_family"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_page_family_contract_lint_rejects_missing_page_variants(self) -> None:
        contract = minimal_page_family_contract()
        contract.pop("page_variants")

        issues = lint.validate_page_family_contract(contract, family_id="blue-professional")

        self.assertIn(
            ("contract_page_variants_missing", "blue-professional", "page_variants"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_page_family_contract_lint_rejects_variant_without_source_refs_or_confidence(self) -> None:
        contract = minimal_page_family_contract()
        variant = contract["page_variants"]["cover"]  # type: ignore[index]
        variant.pop("source_refs")  # type: ignore[attr-defined]
        variant.pop("extraction_confidence")  # type: ignore[attr-defined]

        issues = lint.validate_page_family_contract(contract, family_id="blue-professional")

        issue_set = {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues}
        self.assertIn(("page_variant_required_field_missing", "blue-professional", "page_variants.cover.source_refs"), issue_set)
        self.assertIn(("page_variant_required_field_missing", "blue-professional", "page_variants.cover.extraction_confidence"), issue_set)

    def test_page_family_contract_lint_accepts_blue_professional_10_variant_fixture(self) -> None:
        report_path = REFERENCES_DIR / "visual-contracts/beautiful/_fixtures/blue-professional-page-family.fixture.json"
        contract = json.loads(report_path.read_text(encoding="utf-8"))

        issues = lint.validate_page_family_contract(contract, family_id="blue-professional")

        self.assertEqual([], issues)
        self.assertEqual(10, len(contract["page_variants"]))

    def test_strict_page_family_matrix_lint_blocks_production_without_smoke_or_migration_block(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] == "production")
        row.pop("page_family_smoke_receipt", None)
        row.pop("page_family_promotion_gate", None)
        row.pop("migration_block", None)
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path, page_family_mode="strict")

        self.assertIn(
            ("production_page_family_smoke_missing", row["family_id"], "page_family_smoke_receipt"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_strict_page_family_matrix_lint_blocks_gate_without_golden_specs_or_smoke_deck(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] == "production")
        row.pop("page_variant_golden_specs", None)
        row.pop("page_family_smoke_deck", None)
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path, page_family_mode="strict")

        issue_set = {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues}
        self.assertIn(("page_family_gate_passed_without_smoke_deck", row["family_id"], "page_family_smoke_deck"), issue_set)
        self.assertIn(("page_family_gate_passed_without_golden_specs", row["family_id"], "page_variant_golden_specs"), issue_set)

    def test_strict_page_family_matrix_lint_blocks_smoke_receipt_without_input_hashes(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] == "production")
        receipt = json.loads(lint.resolve_path(row["page_family_smoke_receipt"]).read_text(encoding="utf-8"))
        receipt["input_hashes"] = {}
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            receipt_path = tmp_path / "smoke.json"
            write_json(receipt_path, receipt)
            row["page_family_smoke_receipt"] = receipt_path.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path, page_family_mode="strict")

        self.assertIn(
            ("page_family_smoke_receipt_input_hashes_missing", row["family_id"], "page_family_smoke_receipt.input_hashes"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_strict_page_family_matrix_lint_blocks_smoke_receipt_missing_implemented_variant(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] == "production")
        receipt = json.loads(lint.resolve_path(row["page_family_smoke_receipt"]).read_text(encoding="utf-8"))
        receipt["pages"] = [
            page for page in receipt["pages"] if page.get("page_variant_id") != "bars"
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            receipt_path = tmp_path / "smoke.json"
            write_json(receipt_path, receipt)
            row["page_family_smoke_receipt"] = receipt_path.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path, page_family_mode="strict")

        self.assertIn(
            ("page_family_smoke_receipt_missing_implemented_variant", row["family_id"], "page_family_smoke_receipt.pages.bars"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_rejects_candidate_missing_font_typography_text_style_strategy(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        family = matrix["candidates"][0]["family_id"]
        for key in ("font_strategy", "typography_strategy", "text_style_strategy"):
            matrix["candidates"][0].pop(key, None)
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        issue_set = {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues}
        self.assertIn(("candidate_required_field_missing", family, "font_strategy"), issue_set)
        self.assertIn(("strategy_required_section_missing", family, "font_strategy"), issue_set)
        self.assertIn(("strategy_required_section_missing", family, "typography_strategy"), issue_set)
        self.assertIn(("strategy_required_section_missing", family, "text_style_strategy"), issue_set)

    def test_lint_rejects_missing_typography_contract_fields(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = matrix["candidates"][0]
        family = row["family_id"]
        for key in ("word_spacing", "paragraph_spacing", "wrapping_policy", "text_direction", "writing_mode"):
            row["typography_strategy"].pop(key, None)
        contract_path = lint.resolve_path(row["visual_contract_path"])
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["typography_strategy"] = row["typography_strategy"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_contract = tmp_path / "contract.json"
            write_json(local_contract, contract)
            row["visual_contract_path"] = local_contract.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        issue_set = {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues}
        self.assertIn(("strategy_required_field_missing", family, "typography_strategy.word_spacing"), issue_set)
        self.assertIn(("strategy_required_field_missing", family, "typography_strategy.wrapping_policy"), issue_set)
        self.assertIn(("strategy_required_field_missing", family, "typography_strategy.writing_mode"), issue_set)

    def test_lint_rejects_missing_text_style_decoration_contract_fields(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = matrix["candidates"][0]
        family = row["family_id"]
        row["text_style_strategy"].pop("line_through", None)
        row["text_style_strategy"].pop("text_decoration_policy", None)
        contract_path = lint.resolve_path(row["visual_contract_path"])
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["text_style_strategy"] = row["text_style_strategy"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_contract = tmp_path / "contract.json"
            write_json(local_contract, contract)
            row["visual_contract_path"] = local_contract.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        issue_set = {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues}
        self.assertIn(("strategy_required_field_missing", family, "text_style_strategy.line_through"), issue_set)
        self.assertIn(("strategy_required_field_missing", family, "text_style_strategy.text_decoration_policy.underline.style"), issue_set)
        self.assertIn(("text_decoration_policy_field_missing", family, "text_style_strategy.text_decoration_policy.line_through.thickness"), issue_set)

    def test_lint_rejects_extracted_field_without_source_refs(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = matrix["candidates"][0]
        family = row["family_id"]
        row["typography_strategy"]["extraction_confidence"] = {
            field: "absent_use_default" for field in lint.STRATEGY_EVIDENCE_FIELDS["typography_strategy"]
        }
        row["typography_strategy"]["extraction_confidence"]["font_size_scale"] = "css_extracted_from_template_html"
        row["typography_strategy"]["source_refs"] = {}
        contract_path = lint.resolve_path(row["visual_contract_path"])
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["typography_strategy"] = row["typography_strategy"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_contract = tmp_path / "contract.json"
            write_json(local_contract, contract)
            row["visual_contract_path"] = local_contract.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("strategy_source_refs_missing", family, "typography_strategy.source_refs.font_size_scale"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_rejects_invalid_extraction_confidence(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = matrix["candidates"][0]
        family = row["family_id"]
        row["font_strategy"]["extraction_confidence"] = {
            field: "absent_use_default" for field in lint.STRATEGY_EVIDENCE_FIELDS["font_strategy"]
        }
        row["font_strategy"]["extraction_confidence"].pop("source_fonts")
        contract_path = lint.resolve_path(row["visual_contract_path"])
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["font_strategy"] = row["font_strategy"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_contract = tmp_path / "contract.json"
            write_json(local_contract, contract)
            row["visual_contract_path"] = local_contract.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("strategy_extraction_confidence_invalid", family, "font_strategy.extraction_confidence.source_fonts"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_rejects_role_mapping_font_outside_allowlist_without_receipt_marker(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = matrix["candidates"][0]
        family = row["family_id"]
        row["font_strategy"]["role_mapping"]["display"] = {
            "source_font": "Some Remote Font",
            "slide_font": "Some Remote Font",
        }
        contract_path = lint.resolve_path(row["visual_contract_path"])
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["font_strategy"] = row["font_strategy"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_contract = tmp_path / "contract.json"
            write_json(local_contract, contract)
            row["visual_contract_path"] = local_contract.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("font_strategy_role_font_not_allowed", family, "font_strategy.role_mapping.display"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_rejects_all_families_sharing_one_font_and_typography_strategy(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        first_font_strategy = matrix["candidates"][0]["font_strategy"]
        first_typography_strategy = matrix["candidates"][0]["typography_strategy"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for row in matrix["candidates"]:
                row["font_strategy"] = first_font_strategy
                row["typography_strategy"] = first_typography_strategy
                contract_path = lint.resolve_path(row["visual_contract_path"])
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                contract["font_strategy"] = first_font_strategy
                contract["typography_strategy"] = first_typography_strategy
                local_contract = tmp_path / f"{row['family_id']}.json"
                write_json(local_contract, contract)
                row["visual_contract_path"] = local_contract.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        issue_codes = {item.get("code") for item in issues}
        self.assertIn("font_strategy_all_families_identical", issue_codes)
        self.assertIn("typography_strategy_all_families_identical", issue_codes)

    def test_lint_rejects_non_production_actual_evidence_path_that_does_not_exist(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] != "production")
        row["renderer_module"] = "skills/lark-slides/scripts/artboard_renderer/templates/beautiful/not-real.mjs"
        row["planned_renderer_module"] = "skills/lark-slides/scripts/artboard_renderer/templates/beautiful/not-real.mjs"
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("candidate_actual_evidence_missing_file", row["family_id"], "renderer_module"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_rejects_unfinished_renderer_with_actual_golden_or_receipt_fields(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] != "production")
        row["renderer_module"] = ""
        row["renderer_id"] = "artboard_satori.not-finished"
        row["golden_spec"] = "skills/lark-slides/scripts/fixtures/svglide_artboard/golden/not-finished.canvas-spec.json"
        row["fidelity_receipt"] = "skills/lark-slides/references/receipts/template-fidelity/not-finished.json"
        row["fidelity_gate"] = {"status": "passed"}
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        issue_set = {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues}
        self.assertIn(("candidate_unfinished_actual_evidence_present", row["family_id"], "renderer_id"), issue_set)
        self.assertIn(("candidate_unfinished_actual_evidence_present", row["family_id"], "golden_spec"), issue_set)
        self.assertIn(("candidate_unfinished_actual_evidence_present", row["family_id"], "fidelity_receipt"), issue_set)
        self.assertIn(("candidate_unfinished_fidelity_status_invalid", row["family_id"], "fidelity_gate.status"), issue_set)

    def test_lint_blocks_production_without_real_renderer_and_receipt(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["family_id"] != "blue-professional")
        row["promotion_status"] = "production"
        row["default_selectable"] = True
        row["renderer_module"] = "skills/lark-slides/scripts/artboard_renderer/templates/beautiful/missing.mjs"
        row["golden_spec"] = "skills/lark-slides/scripts/fixtures/svglide_artboard/golden/missing.canvas-spec.json"
        row["fidelity_receipt"] = "skills/lark-slides/references/receipts/template-fidelity/missing.json"
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("candidate_production_evidence_missing_file", row["family_id"], "renderer_module"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_blocks_production_receipt_without_role_consumption(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] == "production")
        family = row["family_id"]
        receipt = json.loads(lint.resolve_path(row["fidelity_receipt"]).read_text(encoding="utf-8"))
        receipt.pop("role_consumption", None)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            receipt_path = tmp_path / "receipt.json"
            write_json(receipt_path, receipt)
            row["fidelity_receipt"] = receipt_path.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("candidate_production_fidelity_role_consumption_missing", family, "fidelity_receipt.role_consumption"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_blocks_default_selectable_without_production_review_receipt(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] == "production")
        row.pop("production_review_receipt", None)
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("candidate_production_review_receipt_missing", row["family_id"], "production_review_receipt"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_blocks_default_selectable_with_failed_production_review_receipt(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] == "production")
        receipt = production_review_receipt_for_row(row, status="failed")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            receipt_path = tmp_path / "production-review.json"
            write_json(receipt_path, receipt)
            row["production_review_receipt"] = receipt_path.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("candidate_production_review_receipt_not_passed", row["family_id"], "production_review_receipt.status"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_blocks_default_selectable_with_stale_production_review_receipt(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] == "production")
        receipt = production_review_receipt_for_row(row)
        receipt["input_hashes"]["renderer_module"] = "stale"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            receipt_path = tmp_path / "production-review.json"
            write_json(receipt_path, receipt)
            row["production_review_receipt"] = receipt_path.as_posix()
            matrix_path = tmp_path / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertIn(
            ("candidate_production_review_receipt_stale", row["family_id"], "production_review_receipt.input_hashes.renderer_module"),
            {(item.get("code"), item.get("family_id"), item.get("path")) for item in issues},
        )

    def test_lint_does_not_require_production_review_receipt_for_needs_review_family(self) -> None:
        matrix = json.loads((REFERENCES_DIR / "beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        row = next(item for item in matrix["candidates"] if item["promotion_status"] == "needs_review")
        row.pop("production_review_receipt", None)
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            write_json(matrix_path, matrix)

            issues = lint.validate_candidate_matrix(matrix_path=matrix_path)

        self.assertNotIn(
            row["family_id"],
            {
                item.get("family_id")
                for item in issues
                if str(item.get("code") or "").startswith("candidate_production_review")
            },
        )


if __name__ == "__main__":
    unittest.main()
