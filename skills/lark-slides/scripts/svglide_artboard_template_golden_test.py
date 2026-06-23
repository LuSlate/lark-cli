from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_artboard_renderer as artboard


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

PROMOTED_TEMPLATE_IDS = [
    "pixel-orbit-console",
    "biennale-programme-poster",
    "block-frame-grid",
    "capsule-card-system",
    "coral-magazine-feature",
    "creative-mode-grid",
    "daisy-workshop-playbook",
    "tritone-editorial-spread",
    "emerald-editorial-cover",
    "grove-organic-brief",
    "mat-midcentury-board",
    "people-platform-manifesto",
    "pink-nocturne-feature",
    "playful-indie-launch",
    "retro-zine-spread",
    "sticky-workshop-board",
    "soft-editorial-feature",
    "stencil-field-manual",
    "vellum-scholar-brief",
]

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


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class ArtboardTemplateGoldenTest(unittest.TestCase):
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

    def test_promoted_beautiful_templates_render_without_baseline_or_debug_artifacts(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        golden_dir = scripts_dir / "fixtures/svglide_artboard/golden"
        slides = []
        for page, template_id in enumerate(PROMOTED_TEMPLATE_IDS, start=1):
            spec = json.loads((golden_dir / f"{template_id}.canvas-spec.json").read_text(encoding="utf-8"))
            self.assertEqual(spec["template_id"], template_id)
            self.assertNotIn(spec.get("theme_id"), {"baseline", "safe-native-v1", "default"})
            page_type = "summary" if page == len(PROMOTED_TEMPLATE_IDS) else ("cover" if page == 1 else "content")
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
            write_json(project / "02-plan/slide_plan.json", {"generation_mode": "artboard_satori", "slides": slides})
            result = artboard.render_project(project)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(len(result["artboard_receipts"]), len(PROMOTED_TEMPLATE_IDS))
            preview_parts = ["<html><body>"]
            for page in range(1, len(PROMOTED_TEMPLATE_IDS) + 1):
                raw = project / f"04-svg/artboard/raw/page-{page:03d}.satori.svg"
                prepared = project / f"04-svg/page-{page:03d}.svg"
                receipt_path = project / f"04-svg/artboard/page-{page:03d}.receipt.json"
                self.assertTrue(raw.exists())
                self.assertTrue(prepared.exists())
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                self.assertEqual(receipt["compiler_input"], f"04-svg/artboard/raw/page-{page:03d}.satori.svg")
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
            for page in range(1, len(PROMOTED_TEMPLATE_IDS) + 1):
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


if __name__ == "__main__":
    unittest.main()
