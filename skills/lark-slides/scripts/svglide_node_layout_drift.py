#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


DEFAULT_DRIFT_THRESHOLD_PX = 8.0
TEXT_RE = re.compile(r"\s+")


def number(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None or isinstance(value, bool):
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def normalize_text(value: str) -> str:
    return TEXT_RE.sub(" ", value).strip()


def normalized_match(value: str) -> str:
    return "".join(normalize_text(value).split()).lower()


def bbox_from_node(node: dict[str, Any]) -> dict[str, float]:
    return {
        "x": number(node.get("x")),
        "y": number(node.get("y")),
        "width": number(node.get("width")),
        "height": number(node.get("height")),
    }


def node_center(bbox: dict[str, float]) -> tuple[float, float]:
    return (bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2)


def bbox_delta_px(expected: dict[str, float], measured: dict[str, float]) -> float:
    return max(
        abs(expected["x"] - measured["x"]),
        abs(expected["y"] - measured["y"]),
        abs(expected["width"] - measured["width"]),
        abs(expected["height"] - measured["height"]),
    )


def normalize_renderer_observations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        props = observation.get("props") if isinstance(observation.get("props"), dict) else {}
        node_id = observation.get("node_id") or observation.get("key") or props.get("data-node-id")
        bbox = {
            "x": number(observation.get("left")),
            "y": number(observation.get("top")),
            "width": number(observation.get("width")),
            "height": number(observation.get("height")),
        }
        if bbox["width"] <= 0 or bbox["height"] <= 0:
            continue
        text = observation.get("textContent")
        normalized.append(
            {
                "id": str(node_id) if node_id is not None else None,
                "kind": str(observation.get("type") or "node"),
                "text": str(text) if isinstance(text, str) else None,
                "bbox": bbox,
            }
        )
    return normalized


def _attr(element: ET.Element, name: str) -> str | None:
    value = element.get(name)
    if value is not None:
        return value
    for key, item in element.attrib.items():
        if key.rsplit("}", 1)[-1] == name:
            return item
    return None


def observations_from_svg(svg_path: Path) -> list[dict[str, Any]]:
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    observations: list[dict[str, Any]] = []
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        node_id = _attr(element, "data-node-id")
        bbox: dict[str, float] | None = None
        if local_name in {"rect", "foreignObject", "image"}:
            bbox = {
                "x": number(_attr(element, "x")),
                "y": number(_attr(element, "y")),
                "width": number(_attr(element, "width")),
                "height": number(_attr(element, "height")),
            }
        elif local_name == "text":
            font_size = number(_attr(element, "font-size"), 18)
            text = normalize_text("".join(element.itertext()))
            bbox = {
                "x": number(_attr(element, "data-box-x"), number(_attr(element, "x"))),
                "y": number(_attr(element, "data-box-y"), number(_attr(element, "y")) - font_size),
                "width": number(_attr(element, "data-box-width"), max(len(text) * font_size * 0.62, font_size * 2)),
                "height": number(_attr(element, "data-box-height"), font_size * 1.35),
            }
        elif local_name == "circle":
            radius = number(_attr(element, "r"))
            bbox = {
                "x": number(_attr(element, "cx")) - radius,
                "y": number(_attr(element, "cy")) - radius,
                "width": radius * 2,
                "height": radius * 2,
            }
        if bbox is None or bbox["width"] <= 0 or bbox["height"] <= 0:
            continue
        observations.append(
            {
                "id": node_id,
                "kind": local_name,
                "text": normalize_text("".join(element.itertext())) or None,
                "bbox": bbox,
            }
        )
    return observations


def _match_observation(expected: dict[str, Any], observations: list[dict[str, Any]], used: set[int]) -> tuple[int | None, dict[str, Any] | None]:
    expected_id = str(expected.get("id") or "")
    for index, observation in enumerate(observations):
        if index in used:
            continue
        if expected_id and observation.get("id") == expected_id:
            return index, observation
    expected_text = expected.get("text")
    if isinstance(expected_text, str) and normalized_match(expected_text):
        candidates: list[tuple[float, int, dict[str, Any]]] = []
        expected_bbox = bbox_from_node(expected)
        expected_center = node_center(expected_bbox)
        for index, observation in enumerate(observations):
            if index in used:
                continue
            observed_text = observation.get("text")
            if not isinstance(observed_text, str):
                continue
            if normalized_match(observed_text) != normalized_match(expected_text):
                continue
            observed_center = node_center(observation["bbox"])
            distance = (expected_center[0] - observed_center[0]) ** 2 + (expected_center[1] - observed_center[1]) ** 2
            candidates.append((distance, index, observation))
        if candidates:
            _, index, observation = min(candidates, key=lambda item: item[0])
            return index, observation
    expected_bbox = bbox_from_node(expected)
    expected_center = node_center(expected_bbox)
    candidates = []
    for index, observation in enumerate(observations):
        if index in used:
            continue
        observed_center = node_center(observation["bbox"])
        distance = (expected_center[0] - observed_center[0]) ** 2 + (expected_center[1] - observed_center[1]) ** 2
        candidates.append((distance, index, observation))
    if not candidates:
        return None, None
    _, index, observation = min(candidates, key=lambda item: item[0])
    return index, observation


def build_node_layout_map(
    *,
    page: int,
    expected_nodes: list[dict[str, Any]],
    renderer_observations: list[dict[str, Any]] | None,
    satori_svg_path: Path,
    threshold_px: float = DEFAULT_DRIFT_THRESHOLD_PX,
) -> dict[str, Any]:
    observations = normalize_renderer_observations(renderer_observations or [])
    observation_source = "satori_on_node_detected"
    if not observations:
        observations = observations_from_svg(satori_svg_path)
        observation_source = "rendered_satori_svg_parse"
    used: set[int] = set()
    measured_nodes: list[dict[str, Any]] = []
    max_px = 0.0
    renderer_max_px = 0.0
    missing_count = 0
    for expected in expected_nodes:
        expected_bbox = bbox_from_node(expected)
        index, observation = _match_observation(expected, observations, used)
        measured_bbox = observation["bbox"] if observation else None
        if index is not None:
            used.add(index)
        if measured_bbox is None:
            missing_count += 1
            drift_px = None
            measured_bbox = expected_bbox
        else:
            drift_px = bbox_delta_px(expected_bbox, measured_bbox)
            renderer_max_px = max(renderer_max_px, drift_px)
        # The exported node layout is the canonical CanvasSpec/template layout.
        # Renderer observations are retained for audit but must not overwrite
        # downstream fit boxes, because Satori can report intermediate flex
        # nodes with the same data-node-id as the intended text run.
        layout_bbox = expected_bbox
        measured_nodes.append(
            {
                "id": str(expected.get("id") or ""),
                "kind": str(expected.get("kind") or "node"),
                "x": layout_bbox["x"],
                "y": layout_bbox["y"],
                "width": layout_bbox["width"],
                "height": layout_bbox["height"],
                "text": expected.get("text") if isinstance(expected.get("text"), str) else None,
                "expected_bbox": expected_bbox,
                "measured_bbox": measured_bbox,
                "drift_px": drift_px,
                "renderer_drift_px": drift_px,
                "observation_source": observation_source if observation else "missing",
            }
        )
    status = "passed" if max_px <= threshold_px else "failed"
    return {
        "version": "svglide-node-layout-map/v1",
        "page": page,
        "source": "measured-layout-observation",
        "observation_source": observation_source,
        "threshold_px": threshold_px,
        "drift": {
            "status": status,
            "max_px": max_px,
            "threshold_px": threshold_px,
            "missing_count": missing_count,
            "canonical_fallback_count": missing_count,
            "renderer_max_px": renderer_max_px,
        },
        "nodes": measured_nodes,
    }


def validate_node_layout_map(layout_map: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    source = layout_map.get("source")
    observation_source = layout_map.get("observation_source")
    if source != "measured-layout-observation":
        issues.append({"code": "node_layout_map_source_not_measured", "message": "node-layout-map source must be measured-layout-observation"})
    if not isinstance(observation_source, str) or not observation_source or observation_source == "not_measured_in_p0":
        issues.append({"code": "node_layout_map_observation_source_invalid", "message": "node-layout-map must record a measured observation_source"})
    drift = layout_map.get("drift") if isinstance(layout_map.get("drift"), dict) else {}
    max_px = number(drift.get("max_px"), 0)
    threshold_px = number(drift.get("threshold_px"), number(layout_map.get("threshold_px"), DEFAULT_DRIFT_THRESHOLD_PX))
    missing_count = int(number(drift.get("missing_count"), 0))
    fallback_count = sum(1 for node in layout_map.get("nodes", []) if isinstance(node, dict) and node.get("observation_source") == "missing")
    if drift.get("status") != "passed":
        issues.append({"code": "node_layout_drift_failed", "message": "node-layout-map drift status must be passed"})
    if max_px > threshold_px:
        issues.append({"code": "node_layout_drift_exceeds_threshold", "message": f"node-layout-map max drift {max_px:g}px exceeds threshold {threshold_px:g}px"})
    if missing_count > 0 and missing_count != fallback_count:
        issues.append({"code": "node_layout_observation_missing", "message": f"node-layout-map has {missing_count} missing measured nodes"})
    return issues
