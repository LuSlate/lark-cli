#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


TEXT_RE = re.compile(r"\s+")


def json_sha256(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def normalize_text(value: str) -> str:
    return TEXT_RE.sub(" ", value).strip()


def normalized_match(value: str) -> str:
    return "".join(normalize_text(value).split()).lower()


def _attr(element: ET.Element, name: str) -> str | None:
    value = element.get(name)
    if value is not None:
        return value
    for key, item in element.attrib.items():
        if key.rsplit("}", 1)[-1] == name:
            return item
    return None


def extract_visible_semantic_nodes(svg_path: Path) -> list[dict[str, str | None]]:
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    nodes: list[dict[str, str | None]] = []
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        if local_name not in {"text", "foreignObject"}:
            continue
        text = normalize_text("".join(element.itertext()))
        if not text:
            continue
        nodes.append(
            {
                "element_id": _attr(element, "data-node-id"),
                "source_ref": _attr(element, "data-source-ref"),
                "text": text,
            }
        )
    return nodes


def validate_semantic_map_against_svg(semantic_map: dict[str, Any], svg_path: Path) -> list[dict[str, str]]:
    visible_nodes = extract_visible_semantic_nodes(svg_path)
    visible_by_id = {
        str(node["element_id"]): node
        for node in visible_nodes
        if isinstance(node.get("element_id"), str) and str(node.get("element_id"))
    }
    issues: list[dict[str, str]] = []
    elements = semantic_map.get("elements") if isinstance(semantic_map.get("elements"), list) else []
    for element in elements:
        if not isinstance(element, dict) or element.get("kind") != "text":
            continue
        element_id = element.get("element_id")
        expected_text = element.get("text")
        if not isinstance(element_id, str) or not element_id:
            continue
        if not isinstance(expected_text, str) or not normalize_text(expected_text):
            continue
        observed = visible_by_id.get(element_id)
        if observed is None:
            issues.append({"code": "semantic_map_visible_text_missing", "message": f"visible SVG text is missing semantic element {element_id}"})
            continue
        if normalized_match(str(observed.get("text") or "")) != normalized_match(expected_text):
            issues.append({"code": "semantic_map_visible_text_mismatch", "message": f"visible SVG text does not match semantic map element {element_id}"})
        expected_ref = element.get("source_ref")
        if isinstance(expected_ref, str) and expected_ref:
            actual_ref = observed.get("source_ref")
            if actual_ref != expected_ref:
                issues.append({"code": "semantic_map_source_ref_mismatch", "message": f"visible SVG source_ref does not match semantic map element {element_id}"})
    return issues
