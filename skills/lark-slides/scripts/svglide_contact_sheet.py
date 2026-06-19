#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path


PREPARED_DIR = Path("04-svg/prepared")
OUTPUT_PATH = Path("05-preview/contact-sheet.html")
MANIFEST_PATH = Path("05-preview/contact-sheet.json")


def prepared_svgs(project: Path) -> list[Path]:
    root = project / PREPARED_DIR
    return sorted(root.glob("*.svg")) if root.exists() else []


def run_contact_sheet(project: Path) -> dict[str, object]:
    project = project.resolve()
    svgs = prepared_svgs(project)
    cards = []
    manifest_pages = []
    for index, svg in enumerate(svgs, 1):
        rel = svg.relative_to(project).as_posix()
        manifest_pages.append({"page": index, "svg": rel})
        cards.append(
            f'<section class="page"><div class="label">Page {index}</div>'
            f'<iframe src="../{html.escape(rel)}" title="Page {index}"></iframe></section>'
        )
    html_doc = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>SVGlide Contact Sheet</title>
  <style>
    body { margin: 24px; font-family: system-ui, sans-serif; background: #f7f7f5; color: #202124; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
    .page { border: 1px solid #d7d9dc; background: white; padding: 8px; }
    .label { font-size: 12px; margin-bottom: 6px; color: #5f6368; }
    iframe { width: 100%; aspect-ratio: 16 / 9; border: 0; background: white; }
  </style>
</head>
<body>
  <div class="grid">
    __SVGLIDE_CONTACT_SHEET_CARDS__
  </div>
</body>
</html>
""".replace("__SVGLIDE_CONTACT_SHEET_CARDS__", "\n".join(cards))
    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_doc, encoding="utf-8")
    result = {
        "schema_version": "svglide-contact-sheet/v1",
        "status": "passed" if svgs else "failed",
        "output": OUTPUT_PATH.as_posix(),
        "summary": {"page_count": len(svgs)},
        "pages": manifest_pages,
    }
    (project / MANIFEST_PATH).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a local SVGlide contact sheet HTML.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_contact_sheet(Path(args.project))
    except OSError as error:
        print(f"svglide_contact_sheet: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
