#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_prepare


SVG_NS = "http://www.w3.org/2000/svg"
SLIDE_NS = "https://slides.bytedance.com/ns"
TEXT_STYLE_MANIFEST_ID = "svglide-text-style-manifest"
TEXT_STYLE_MANIFEST_VERSION = "svglide-satori-text-style/v1"

SOURCE_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:slide="https://slides.bytedance.com/ns"
     slide:role="slide"
     slide:contract-version="svglide-authoring-contract/v1"
     width="960" height="540" viewBox="0 0 960 540">
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
  <text slide:role="text" x="72" y="120" font-family="Source Sans Pro" font-size="48" font-weight="800" letter-spacing="-0.2" fill="#111827">ALPHA METRIC</text>
  <text slide:role="text" x="72" y="190" font-family="Inter" font-size="22" font-weight="500" letter-spacing="0.1" fill="#374151">Prepared SVG must carry parser metadata.</text>
</svg>
"""


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slide_plan() -> dict[str, object]:
    return {
        "generation_mode": "artboard_satori",
        "slides": [
            {
                "page": 1,
                "title": "Text style manifest",
                "canvas_spec": {
                    "version": "svglide-canvas-spec/v1",
                    "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
                    "template_id": "executive-dashboard",
                    "theme_id": "blue-professional",
                    "theme": {
                        "colors": {
                            "background": "#f8fafc",
                            "panel": "#ffffff",
                            "primary": "#2563eb",
                            "accent": "#0f766e",
                            "text": "#111827",
                            "muted": "#374151",
                        },
                        "typography": {
                            "font_roles": {
                                "display": "Source Sans Pro",
                                "body": "Inter",
                                "label": "Inter",
                                "metric": "IBM Plex Mono",
                            },
                            "role_tokens": {
                                "display": {
                                    "font_size": 48,
                                    "font_weight": 800,
                                    "line_height": 1.08,
                                    "letter_spacing": -0.2,
                                    "text_transform": "uppercase",
                                },
                                "body": {
                                    "font_size": 22,
                                    "font_weight": 500,
                                    "line_height": 1.35,
                                    "letter_spacing": 0.1,
                                },
                            },
                            "text_style_roles": {
                                "display": {
                                    "color": "#111827",
                                    "decoration": {
                                        "line": "underline",
                                        "style": "solid",
                                        "color": "currentColor",
                                        "thickness": "1px",
                                    },
                                },
                                "body": {
                                    "color": "#374151",
                                    "decoration": {
                                        "line": "none",
                                        "style": "solid",
                                        "color": "currentColor",
                                        "thickness": "1px",
                                    },
                                },
                            },
                        },
                    },
                    "content": {
                        "title": "ALPHA METRIC",
                        "subtitle": "Prepared SVG must carry parser metadata.",
                    },
                },
            }
        ],
    }


class SVGlideSatoriTextStyleManifestTest(unittest.TestCase):
    def write_artboard_generator_receipt(self, project: Path) -> None:
        write_json(
            project / "receipts" / "generate_svg.json",
            {
                "stage": "generate_svg",
                "status": "passed",
                "generation_mode": "artboard_satori",
                "generated_files": [{"path": "04-svg/page-001.svg", "sha256": svglide_prepare.file_sha256(project / "04-svg" / "page-001.svg")}],
            },
        )

    def write_contract_manifest(self, project: Path) -> None:
        output = project / "04-svg" / "page-001.svg"
        digest = svglide_prepare.file_sha256(output)
        report = {
            "version": "svglide-contract-compile/v1",
            "status": "passed",
            "source": "04-artboard/raw/page-001.visual.svg",
            "semantic_map": "04-artboard/raw/page-001.semantic-map.json",
            "output": "04-svg/page-001.svg",
            "output_sha256": digest,
            "summary": {"degraded_elements": 0, "rasterized_regions": 0, "dropped_decorations": 0},
        }
        manifest = {
            "version": "svglide-contract-compile-manifest/v1",
            "stage": "contract_compile",
            "status": "passed",
            "pages": [
                {
                    "page": 1,
                    "source": "04-artboard/raw/page-001.visual.svg",
                    "semantic_map": "04-artboard/raw/page-001.semantic-map.json",
                    "output": "04-svg/page-001.svg",
                    "output_sha256": digest,
                    "report": "04-svg/contract/page-001.report.json",
                    "status": "passed",
                }
            ],
            "summary": {"pages": 1, "blocking_issues": 0, "degraded_elements": 0, "rasterized_regions": 0, "dropped_decorations": 0},
        }
        write_json(project / "04-svg" / "contract" / "page-001.report.json", report)
        write_json(project / "04-svg" / "contract" / "manifest.json", manifest)

    def prepare_fixture_project(self, tmpdir: str) -> tuple[Path, dict[str, object]]:
        project = Path(tmpdir) / ".lark-slides" / "plan" / "text-style-manifest"
        (project / "03-assets").mkdir(parents=True, exist_ok=True)
        (project / "04-svg").mkdir(parents=True, exist_ok=True)
        write_json(project / "02-plan" / "slide_plan.json", slide_plan())
        (project / "04-svg" / "page-001.svg").write_text(SOURCE_SVG, encoding="utf-8")
        self.write_artboard_generator_receipt(project)
        self.write_contract_manifest(project)
        receipt = svglide_prepare.prepare_project(project)
        return project, receipt

    def manifest_metadata(self, root: ElementTree.Element) -> ElementTree.Element | None:
        for element in root.iter(f"{{{SVG_NS}}}metadata"):
            if element.attrib.get("id") == TEXT_STYLE_MANIFEST_ID:
                return element
        return None

    def managed_text_nodes(self, root: ElementTree.Element) -> list[ElementTree.Element]:
        return [element for element in root.iter(f"{{{SVG_NS}}}text") if element.attrib.get(f"{{{SLIDE_NS}}}role") == "text"]

    def test_prepare_injects_text_style_manifest_into_prepared_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project, _receipt = self.prepare_fixture_project(tmpdir)

            prepared = project / "04-svg" / "prepared" / "page-001.svg"
            root = ElementTree.fromstring(prepared.read_text(encoding="utf-8"))
            metadata = self.manifest_metadata(root)

            self.assertIsNotNone(metadata, "prepared SVG must include <metadata id=\"svglide-text-style-manifest\">")
            manifest = json.loads(metadata.text or "{}") if metadata is not None else {}
            self.assertEqual(manifest.get("version"), TEXT_STYLE_MANIFEST_VERSION)
            self.assertEqual(manifest.get("source"), "cli-artboard-satori")
            items = manifest.get("items")
            self.assertIsInstance(items, dict)

            text_nodes = self.managed_text_nodes(root)
            self.assertGreaterEqual(len(text_nodes), 2)
            self.assertEqual(len(items), len(text_nodes))
            required_item_fields = {
                "role",
                "font_family",
                "font_size",
                "font_weight",
                "line_height",
                "letter_spacing",
                "text_transform",
                "color",
                "decoration",
                "source_contract",
                "loss_notes",
            }
            for text_node in text_nodes:
                text_style_id = text_node.attrib.get("data-svglide-text-style-id")
                self.assertTrue(text_style_id, "managed text nodes must be bound to a manifest item")
                item = items.get(text_style_id) if isinstance(items, dict) else None
                self.assertIsInstance(item, dict)
                self.assertTrue(required_item_fields.issubset(item))

    def test_prepare_receipt_records_text_style_manifest_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _project, receipt = self.prepare_fixture_project(tmpdir)

            self.assertIn("text_style_manifest_count", receipt)
            self.assertIn("text_style_manifest_bound_count", receipt)
            self.assertIn("text_style_manifest_loss_count", receipt)
            self.assertGreaterEqual(receipt["text_style_manifest_count"], 2)
            self.assertEqual(receipt["text_style_manifest_bound_count"], receipt["text_style_manifest_count"])
            self.assertEqual(receipt["text_style_manifest_loss_count"], 0)


if __name__ == "__main__":
    unittest.main()
