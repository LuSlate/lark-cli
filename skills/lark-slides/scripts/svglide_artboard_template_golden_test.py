from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_artboard_renderer as artboard
import beautiful_template_runtime


REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"
MATRIX_PATH = REFERENCES_DIR / "beautiful-template-executable-matrix.json"

P1_TEMPLATE_IDS = [
    "intelligence-brief",
    "executive-dashboard",
    "trend-grid-report",
    "product-ribbon",
    "brutalist-matrix",
    "architectural-spec",
    "annotated-field-board",
    "serif-stat-editorial",
    "ledger-briefing",
    "poster-stat-punch",
]

DEDICATED_SAMPLE_TEMPLATE_IDS = [
    "executive-dashboard",
    "intelligence-brief",
    "poster-stat-punch",
    "coral-magazine-feature",
    "soft-editorial-feature",
    "tritone-editorial-spread",
    "pixel-orbit-console",
    "biennale-programme-poster",
    "block-frame-grid",
    "editorial-quote-chart",
    "architectural-spec",
    "printed-program",
    "ledger-briefing",
    "capsule-card-system",
    "creative-mode-grid",
    "daisy-workshop-playbook",
    "emerald-editorial-cover",
    "trend-grid-report",
    "product-ribbon",
    "brutalist-matrix",
    "type-mass-poster",
    "serif-stat-editorial",
    "grove-organic-brief",
    "mat-midcentury-board",
    "dense-panel-grid",
    "people-platform-manifesto",
    "annotated-field-board",
    "pink-nocturne-feature",
    "playful-indie-launch",
    "retro-ui-dashboard",
    "retro-zine-spread",
    "sticky-workshop-board",
    "stencil-field-manual",
    "vellum-scholar-brief",
]

BEAUTIFUL_DEDICATED_SAMPLE_CONTRACTS = {
    "executive-dashboard": {
        "module": "executive-dashboard.mjs",
        "source_family": "blue-professional",
        "reference_screenshot": "blue-professional-1.png",
    },
    "intelligence-brief": {
        "module": "intelligence-brief.mjs",
        "source_family": "signal",
        "reference_screenshot": "signal-1.png",
    },
    "poster-stat-punch": {
        "module": "poster-stat-punch.mjs",
        "source_family": "bold-poster",
        "reference_screenshot": "bold-poster-1.png",
    },
    "coral-magazine-feature": {
        "module": "coral-magazine-feature.mjs",
        "source_family": "coral",
        "reference_screenshot": "coral-1.png",
    },
    "soft-editorial-feature": {
        "module": "soft-editorial-feature.mjs",
        "source_family": "soft-editorial",
        "reference_screenshot": "soft-editorial-4.png",
    },
    "tritone-editorial-spread": {
        "module": "tritone-editorial-spread.mjs",
        "source_family": "editorial-tri-tone",
        "reference_screenshot": "editorial-tri-tone-1.png",
    },
    "pixel-orbit-console": {
        "module": "pixel-orbit-console.mjs",
        "source_family": "8-bit-orbit",
        "reference_screenshot": "8-bit-orbit-1.png",
    },
    "biennale-programme-poster": {
        "module": "biennale-programme-poster.mjs",
        "source_family": "biennale-yellow",
        "reference_screenshot": "biennale-yellow-1.png",
    },
    "block-frame-grid": {
        "module": "block-frame-grid.mjs",
        "source_family": "block-frame",
        "reference_screenshot": "block-frame-1.png",
    },
    "editorial-quote-chart": {
        "module": "broadside-editorial-quote.mjs",
        "source_family": "broadside",
        "reference_screenshot": "broadside-1.png",
    },
    "architectural-spec": {
        "module": "cartesian-architectural-spec.mjs",
        "source_family": "cartesian",
        "reference_screenshot": "cartesian-1.png",
    },
    "printed-program": {
        "module": "long-table-printed-program.mjs",
        "source_family": "long-table",
        "reference_screenshot": "long-table-1.png",
    },
    "ledger-briefing": {
        "module": "monochrome-ledger-briefing.mjs",
        "source_family": "monochrome",
        "reference_screenshot": "monochrome-1.png",
    },
    "capsule-card-system": {
        "module": "capsule-card-system.mjs",
        "source_family": "capsule",
        "reference_screenshot": "capsule-1.png",
    },
    "creative-mode-grid": {
        "module": "creative-mode-grid.mjs",
        "source_family": "creative-mode",
        "reference_screenshot": "creative-mode-1.png",
    },
    "daisy-workshop-playbook": {
        "module": "daisy-workshop-playbook.mjs",
        "source_family": "daisy-days",
        "reference_screenshot": "daisy-days-1.png",
    },
    "emerald-editorial-cover": {
        "module": "emerald-editorial-cover.mjs",
        "source_family": "emerald-editorial",
        "reference_screenshot": "emerald-editorial-1.png",
    },
    "trend-grid-report": {
        "module": "trend-grid-report.mjs",
        "source_family": "cobalt-grid",
        "reference_screenshot": "cobalt-grid-1.png",
    },
    "product-ribbon": {
        "module": "product-ribbon.mjs",
        "source_family": "sakura-chroma",
        "reference_screenshot": "sakura-chroma-1.png",
    },
    "brutalist-matrix": {
        "module": "brutalist-matrix.mjs",
        "source_family": "raw-grid",
        "reference_screenshot": "raw-grid-1.png",
    },
    "type-mass-poster": {
        "module": "type-mass-poster.mjs",
        "source_family": "studio",
        "reference_screenshot": "studio-1.png",
    },
    "serif-stat-editorial": {
        "module": "serif-stat-editorial.mjs",
        "source_family": "editorial-forest",
        "reference_screenshot": "editorial-forest-1.png",
    },
    "grove-organic-brief": {
        "module": "grove-organic-brief.mjs",
        "source_family": "grove",
        "reference_screenshot": "grove-1.png",
    },
    "mat-midcentury-board": {
        "module": "mat-midcentury-board.mjs",
        "source_family": "mat",
        "reference_screenshot": "mat-1.png",
    },
    "dense-panel-grid": {
        "module": "dense-panel-grid.mjs",
        "source_family": "neo-grid-bold",
        "reference_screenshot": "neo-grid-bold-1.png",
    },
    "people-platform-manifesto": {
        "module": "people-platform-manifesto.mjs",
        "source_family": "peoples-platform",
        "reference_screenshot": "peoples-platform-1.png",
    },
    "annotated-field-board": {
        "module": "annotated-field-board.mjs",
        "source_family": "pin-and-paper",
        "reference_screenshot": "pin-and-paper-1.png",
    },
    "pink-nocturne-feature": {
        "module": "pink-nocturne-feature.mjs",
        "source_family": "pink-script",
        "reference_screenshot": "pink-script-1.png",
    },
    "playful-indie-launch": {
        "module": "playful-indie-launch.mjs",
        "source_family": "playful",
        "reference_screenshot": "playful-1.png",
    },
    "retro-ui-dashboard": {
        "module": "retro-ui-dashboard.mjs",
        "source_family": "retro-windows",
        "reference_screenshot": "retro-windows-1.png",
    },
    "retro-zine-spread": {
        "module": "retro-zine-spread.mjs",
        "source_family": "retro-zine",
        "reference_screenshot": "retro-zine-1.png",
    },
    "sticky-workshop-board": {
        "module": "sticky-workshop-board.mjs",
        "source_family": "scatterbrain",
        "reference_screenshot": "scatterbrain-1.png",
    },
    "stencil-field-manual": {
        "module": "stencil-field-manual.mjs",
        "source_family": "stencil-tablet",
        "reference_screenshot": "stencil-tablet-1.png",
    },
    "vellum-scholar-brief": {
        "module": "vellum-scholar-brief.mjs",
        "source_family": "vellum",
        "reference_screenshot": "vellum-1.png",
    },
}

LAYOUT_FAMILIES = [
    "briefing",
    "dashboard",
    "timeline",
    "product",
    "matrix",
    "architecture",
    "annotation",
    "editorial",
    "ledger",
    "closing",
]

BLUE_PROFESSIONAL_PAGE_VARIANTS = [
    "cover",
    "agenda",
    "metrics",
    "dashboard",
    "split",
    "bars",
    "quote",
    "timeline",
    "detail",
    "closing",
]

REQUIRED_TYPOGRAPHY_ROLES = {"display", "body", "label", "metric"}
REQUIRED_ROLE_TOKEN_FIELDS = {"font_weight", "line_height", "letter_spacing", "text_transform"}
REQUIRED_TEXT_STYLE_ROLE_FIELDS = {"bold", "italic", "underline", "line_through", "emphasis", "text_decoration_policy"}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_legacy_fixture_registries(project: Path) -> None:
    write_json(project / "02-plan/theme-registry.json", beautiful_template_runtime.theme_registry(include_legacy=True))
    write_json(project / "02-plan/template-registry.json", beautiful_template_runtime.template_registry(include_legacy=True))


def assert_receipt_consumes_font_and_typography_roles(test_case: unittest.TestCase, receipt: dict[str, object]) -> None:
    font_roles = receipt.get("font_roles")
    test_case.assertIsInstance(font_roles, dict)
    test_case.assertTrue(REQUIRED_TYPOGRAPHY_ROLES.issubset(set(font_roles or {})))
    for role in REQUIRED_TYPOGRAPHY_ROLES:
        resolved = (font_roles or {}).get(role)
        test_case.assertIsInstance(resolved, dict)
        test_case.assertTrue(resolved.get("family"))
        test_case.assertTrue(resolved.get("source"))

    typography_roles = receipt.get("typography_roles")
    test_case.assertIsInstance(typography_roles, dict)
    test_case.assertTrue(REQUIRED_TYPOGRAPHY_ROLES.issubset(set(typography_roles or {})))
    for role in REQUIRED_TYPOGRAPHY_ROLES:
        token = (typography_roles or {}).get(role)
        test_case.assertIsInstance(token, dict)
        test_case.assertTrue(REQUIRED_ROLE_TOKEN_FIELDS.issubset(set(token or {})))
    text_style_roles = receipt.get("text_style_roles")
    test_case.assertIsInstance(text_style_roles, dict)
    test_case.assertTrue(REQUIRED_TEXT_STYLE_ROLE_FIELDS.issubset(set(text_style_roles or {})))
    test_case.assertTrue(receipt.get("typography_strategy_source"))


def load_candidate_matrix() -> list[dict[str, object]]:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    return [row for row in matrix.get("candidates", []) if isinstance(row, dict)]


class ArtboardTemplateGoldenTest(unittest.TestCase):
    def test_beautiful_renderer_contract_uses_closed_loop_sample_not_generic_fallback(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        renderer_dir = scripts_dir / "artboard_renderer"
        p0_source = (renderer_dir / "templates/p0-templates.mjs").read_text(encoding="utf-8")
        index_source = (renderer_dir / "templates/beautiful/index.mjs").read_text(encoding="utf-8")
        self.assertNotIn("return beautifulTemplate(spec, BEAUTIFUL_TEMPLATE_CONFIGS[spec.template_id])", p0_source)
        self.assertTrue((renderer_dir / "templates/beautiful/index.mjs").exists())
        for sample_template_id, contract in BEAUTIFUL_DEDICATED_SAMPLE_CONTRACTS.items():
            self.assertNotIn(f"'{sample_template_id}':", p0_source)
            module_path = renderer_dir / f"templates/beautiful/{contract['module']}"
            self.assertTrue(module_path.exists())
            module_source = module_path.read_text(encoding="utf-8")
            self.assertNotIn("beautifulTemplate(", module_source)
            self.assertIn("templateId", module_source)
            self.assertIn(f"source_family: '{contract['source_family']}'", module_source)
            self.assertIn(contract["reference_screenshot"], module_source)
            self.assertIn(contract["module"], index_source)
            for role in ["display", "body", "label", "metric"]:
                self.assertIn(f"fontRole('{role}'", module_source)
        evaluation_stub = renderer_dir / "templates/beautiful/evaluation-stub.mjs"
        self.assertTrue(evaluation_stub.exists())

    def test_font_role_helper_consumes_typography_strategy_tokens(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        typography_source = (scripts_dir / "artboard_renderer/components/typography.mjs").read_text(encoding="utf-8")

        for source_token, satori_style in [
            ("font_weight", "fontWeight"),
            ("line_height", "lineHeight"),
            ("letter_spacing", "letterSpacing"),
            ("text_transform", "textTransform"),
            ("text_decoration_policy", "textDecorationLine"),
            ("underline", "textDecorationStyle"),
            ("line_through", "textDecorationThickness"),
        ]:
            self.assertIn(source_token, typography_source)
            self.assertIn(satori_style, typography_source)
        self.assertIn("tokenStyle(role, spec)", typography_source)
        self.assertIn("textDecorationStyle(spec, decorationRequestFromFallback(fallback))", typography_source)
        self.assertIn("typographyRolesFromTheme", typography_source)

    def test_existing_dedicated_golden_specs_match_matrix_typography_strategy(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        renderer_rows = [row for row in load_candidate_matrix() if row.get("renderer_module")]
        self.assertGreaterEqual(len(renderer_rows), len(DEDICATED_SAMPLE_TEMPLATE_IDS))

        for row in renderer_rows:
            with self.subTest(family_id=row.get("family_id"), template_id=row.get("runtime_template_id")):
                spec_path = repo_root / str(row["golden_spec"])
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
                typography = spec.get("theme", {}).get("typography", {})
                font_roles = typography.get("font_roles")
                role_tokens = typography.get("role_tokens")
                text_style_roles = typography.get("text_style_roles")
                self.assertIsInstance(font_roles, dict)
                self.assertIsInstance(role_tokens, dict)
                self.assertIsInstance(text_style_roles, dict)
                self.assertTrue(REQUIRED_TYPOGRAPHY_ROLES.issubset(set(font_roles or {})))
                self.assertTrue(REQUIRED_TYPOGRAPHY_ROLES.issubset(set(role_tokens or {})))
                self.assertTrue(REQUIRED_TEXT_STYLE_ROLE_FIELDS.issubset(set(text_style_roles or {})))
                self.assertEqual(typography.get("strategy_source"), row.get("visual_contract_path"))

                font_strategy = row.get("font_strategy", {})
                for role in REQUIRED_TYPOGRAPHY_ROLES:
                    expected_alias = font_strategy.get("role_mapping", {}).get(role, {}).get("runtime_alias")
                    self.assertEqual(font_roles.get(role), expected_alias)

                expected_tokens = row.get("typography_strategy", {}).get("role_mapping")
                self.assertEqual(role_tokens, expected_tokens)

    def test_p1_templates_render_without_baseline_or_debug_artifacts(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        golden_dir = scripts_dir / "fixtures/svglide_artboard/golden"
        slides = []
        for page, template_id in enumerate(P1_TEMPLATE_IDS, start=1):
            spec = json.loads((golden_dir / f"{template_id}.canvas-spec.json").read_text(encoding="utf-8"))
            self.assertEqual(spec["template_id"], template_id)
            self.assertNotIn(spec.get("theme_id"), {"baseline", "safe-native-v1", "default"})
            page_type = "closing" if page == len(P1_TEMPLATE_IDS) else ("cover" if page == 1 else "content")
            slides.append(
                {
                    "page": page,
                    "title": spec["content"]["title"],
                    "page_type": page_type,
                    "renderer_id": f"artboard_satori.{template_id}",
                    "layout_family": LAYOUT_FAMILIES[page - 1],
                    "visual_recipe": "closing summary" if page_type == "closing" else f"{LAYOUT_FAMILIES[page - 1]} canvas",
                    "content_density_contract": "dashboard >= 4 metrics" if page == 2 else "matrix >= 6 cells",
                    "canvas_spec": spec,
                }
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_legacy_fixture_registries(project)
            write_json(project / "02-plan/slide_plan.json", {"generation_mode": "artboard_satori", "slides": slides})
            result = artboard.render_project(project)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(len(result["artboard_receipts"]), len(P1_TEMPLATE_IDS))
            preview_parts = ["<html><body>"]
            for page in range(1, len(P1_TEMPLATE_IDS) + 1):
                raw = project / f"04-svg/artboard/raw/page-{page:03d}.satori.svg"
                prepared = project / f"04-svg/page-{page:03d}.svg"
                receipt_path = project / f"04-svg/artboard/page-{page:03d}.receipt.json"
                self.assertTrue(raw.exists())
                self.assertTrue(prepared.exists())
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                self.assertEqual(receipt["compiler_input"], f"04-svg/artboard/raw/page-{page:03d}.satori.svg")
                assert_receipt_consumes_font_and_typography_roles(self, receipt)
                text = raw.read_text(encoding="utf-8") + prepared.read_text(encoding="utf-8")
                lowered = text.lower()
                self.assertNotIn("baseline", lowered)
                self.assertNotIn("debug guide", lowered)
                self.assertNotIn("reference line", lowered)
                self.assertNotIn("stroke-dasharray=\"2 2\"", lowered)
                self.assertNotIn("opacity=\"0.12\" data-debug", lowered)
                preview_parts.append(prepared.read_text(encoding="utf-8"))
            preview_parts.append("</body></html>")
            preview = project / "05-preview/preview.html"
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview.write_text("\n".join(preview_parts), encoding="utf-8")
            preflight_command = [
                sys.executable,
                (scripts_dir / "svg_preflight.py").as_posix(),
                "--plan",
                (project / "02-plan/slide_plan.json").as_posix(),
            ]
            for page in range(1, len(P1_TEMPLATE_IDS) + 1):
                preflight_command.extend(["--input", (project / f"04-svg/page-{page:03d}.svg").as_posix()])
            preflight = subprocess.run(preflight_command, check=False, capture_output=True, text=True)
            self.assertEqual(preflight.returncode, 0, preflight.stdout + preflight.stderr)
            preview_lint = subprocess.run(
                [sys.executable, (scripts_dir / "svg_preview_lint.py").as_posix(), preview.as_posix(), "--pretty"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(preview_lint.returncode, 0, preview_lint.stdout + preview_lint.stderr)

    def test_dedicated_sample_template_renders_without_baseline_or_debug_artifacts(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        golden_dir = scripts_dir / "fixtures/svglide_artboard/golden"
        slides = []
        for page, template_id in enumerate(DEDICATED_SAMPLE_TEMPLATE_IDS, start=1):
            spec = json.loads((golden_dir / f"{template_id}.canvas-spec.json").read_text(encoding="utf-8"))
            self.assertEqual(spec["template_id"], template_id)
            self.assertNotIn(spec.get("theme_id"), {"baseline", "safe-native-v1", "default"})
            page_type = "summary" if page == len(DEDICATED_SAMPLE_TEMPLATE_IDS) else ("cover" if page == 1 else "content")
            slides.append(
                {
                    "page": page,
                    "title": spec["content"]["title"],
                    "page_type": page_type,
                    "renderer_id": f"artboard_satori.{template_id}",
                    "layout_family": template_id.replace("-", "_"),
                    "visual_recipe": f"{template_id} family-owned canvas",
                    "content_density_contract": "family template golden fixture",
                    "canvas_spec": spec,
                }
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_legacy_fixture_registries(project)
            write_json(project / "02-plan/slide_plan.json", {"generation_mode": "artboard_satori", "slides": slides})
            result = artboard.render_project(project)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(len(result["artboard_receipts"]), len(DEDICATED_SAMPLE_TEMPLATE_IDS))
            preview_parts = ["<html><body>"]
            for page in range(1, len(DEDICATED_SAMPLE_TEMPLATE_IDS) + 1):
                raw = project / f"04-svg/artboard/raw/page-{page:03d}.satori.svg"
                prepared = project / f"04-svg/page-{page:03d}.svg"
                receipt_path = project / f"04-svg/artboard/page-{page:03d}.receipt.json"
                self.assertTrue(raw.exists())
                self.assertTrue(prepared.exists())
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                self.assertEqual(receipt["compiler_input"], f"04-svg/artboard/raw/page-{page:03d}.satori.svg")
                assert_receipt_consumes_font_and_typography_roles(self, receipt)
                text = raw.read_text(encoding="utf-8") + prepared.read_text(encoding="utf-8")
                lowered = text.lower()
                self.assertNotIn("baseline", lowered)
                self.assertNotIn("debug guide", lowered)
                self.assertNotIn("reference line", lowered)
                self.assertNotIn("stroke-dasharray=\"2 2\"", lowered)
                self.assertNotIn("opacity=\"0.12\" data-debug", lowered)
                preview_parts.append(prepared.read_text(encoding="utf-8"))
            preview_parts.append("</body></html>")
            preview = project / "05-preview/preview.html"
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview.write_text("\n".join(preview_parts), encoding="utf-8")
            preflight_command = [
                sys.executable,
                (scripts_dir / "svg_preflight.py").as_posix(),
                "--plan",
                (project / "02-plan/slide_plan.json").as_posix(),
            ]
            for page in range(1, len(DEDICATED_SAMPLE_TEMPLATE_IDS) + 1):
                preflight_command.extend(["--input", (project / f"04-svg/page-{page:03d}.svg").as_posix()])
            preflight = subprocess.run(preflight_command, check=False, capture_output=True, text=True)
            self.assertEqual(preflight.returncode, 0, preflight.stdout + preflight.stderr)
            preview_lint = subprocess.run(
                [sys.executable, (scripts_dir / "svg_preview_lint.py").as_posix(), preview.as_posix(), "--pretty"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(preview_lint.returncode, 0, preview_lint.stdout + preview_lint.stderr)

    def test_blue_professional_page_family_variants_render_and_record_variant_metadata(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        golden_dir = scripts_dir / "fixtures/svglide_artboard/golden"
        slides = []
        for page, variant_id in enumerate(BLUE_PROFESSIONAL_PAGE_VARIANTS, start=1):
            spec_path = golden_dir / f"blue-professional.{variant_id}.canvas-spec.json"
            self.assertTrue(spec_path.exists(), f"missing page-family fixture: {spec_path}")
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            self.assertEqual(spec["template_id"], "executive-dashboard")
            self.assertEqual(spec["family_id"], "blue-professional")
            self.assertEqual(spec["page_variant_id"], variant_id)
            self.assertTrue(spec.get("page_role"))
            slides.append(
                {
                    "page": page,
                    "title": spec["content"]["title"],
                    "page_type": spec["page_role"],
                    "renderer_id": "artboard_satori.executive-dashboard",
                    "layout_family": "executive_dashboard",
                    "visual_recipe": f"blue-professional {variant_id} canvas",
                    "content_density_contract": "page-family variant fixture",
                    "canvas_spec": spec,
                }
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_legacy_fixture_registries(project)
            write_json(project / "02-plan/slide_plan.json", {"generation_mode": "artboard_satori", "slides": slides})
            result = artboard.render_project(project)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(len(result["artboard_receipts"]), len(BLUE_PROFESSIONAL_PAGE_VARIANTS))
            layout_signatures = set()
            for page, variant_id in enumerate(BLUE_PROFESSIONAL_PAGE_VARIANTS, start=1):
                receipt = json.loads((project / f"04-svg/artboard/page-{page:03d}.receipt.json").read_text(encoding="utf-8"))
                metadata = json.loads((project / receipt["render_metadata"]).read_text(encoding="utf-8"))
                self.assertEqual(receipt["template_id"], "executive-dashboard")
                self.assertEqual(receipt["family_id"], "blue-professional")
                self.assertEqual(receipt["page_role"], slides[page - 1]["page_type"])
                self.assertEqual(receipt["page_variant_id"], variant_id)
                self.assertEqual(metadata["family_id"], "blue-professional")
                self.assertEqual(metadata["page_role"], slides[page - 1]["page_type"])
                self.assertEqual(metadata["page_variant_id"], variant_id)
                assert_receipt_consumes_font_and_typography_roles(self, receipt)
                layout_map = json.loads((project / receipt["node_layout_map"]).read_text(encoding="utf-8"))
                boxes = [
                    (
                        node.get("kind"),
                        node.get("x"),
                        node.get("y"),
                        node.get("width"),
                        node.get("height"),
                    )
                    for node in layout_map.get("nodes", [])
                    if isinstance(node, dict)
                ]
                layout_signatures.add(json.dumps(boxes[:8], sort_keys=True))
            self.assertGreaterEqual(len(layout_signatures), 6)


if __name__ == "__main__":
    unittest.main()
