#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCE_DIR = SCRIPT_DIR.parent / "references"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_path(name: str) -> Path:
    return REFERENCE_DIR / name


def validate_json_schema(payload: Any, schema: dict[str, Any], *, path: str = "$") -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(payload, expected_type):
        issues.append(
            {
                "code": "schema_type_mismatch",
                "path": path,
                "message": f"expected {expected_type}, got {_json_type(payload)}",
            }
        )
        return issues

    if "const" in schema and payload != schema["const"]:
        issues.append({"code": "schema_const_mismatch", "path": path, "message": f"expected constant {schema['const']!r}"})
    if "enum" in schema and payload not in schema["enum"]:
        issues.append({"code": "schema_enum_mismatch", "path": path, "message": f"value {payload!r} is not allowed"})
    any_of = schema.get("anyOf")
    if isinstance(any_of, list) and any_of:
        if not any(isinstance(option, dict) and not validate_json_schema(payload, option, path=path) for option in any_of):
            issues.append({"code": "schema_any_of_mismatch", "path": path, "message": "value does not match any allowed schema"})

    if isinstance(payload, dict):
        for required in schema.get("required", []):
            if required not in payload:
                issues.append({"code": "schema_required_missing", "path": f"{path}.{required}", "message": "required property is missing"})
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for key, value in payload.items():
                child_schema = properties.get(key)
                if isinstance(child_schema, dict):
                    issues.extend(validate_json_schema(value, child_schema, path=f"{path}.{key}"))
        additional = schema.get("additionalProperties", True)
        if additional is False and isinstance(properties, dict):
            for key in payload:
                if key not in properties:
                    issues.append({"code": "schema_additional_property", "path": f"{path}.{key}", "message": "additional property is not allowed"})

    if isinstance(payload, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(payload) < min_items:
            issues.append({"code": "schema_min_items", "path": path, "message": f"expected at least {min_items} items"})
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(payload) > max_items:
            issues.append({"code": "schema_max_items", "path": path, "message": f"expected at most {max_items} items"})
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(payload):
                issues.extend(validate_json_schema(item, item_schema, path=f"{path}[{index}]"))

    if isinstance(payload, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(payload) < min_length:
            issues.append({"code": "schema_min_length", "path": path, "message": f"expected at least {min_length} characters"})
    if isinstance(payload, (int, float)) and not isinstance(payload, bool):
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)) and payload < minimum:
            issues.append({"code": "schema_minimum", "path": path, "message": f"expected value >= {minimum}"})

    return issues


def _matches_type(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_matches_type(value, item) for item in expected)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _json_type(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if value is None:
        return "null"
    return type(value).__name__
