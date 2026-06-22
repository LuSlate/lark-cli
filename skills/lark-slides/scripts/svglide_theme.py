#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import beautiful_template_runtime


THEME_SPEC_VERSION = "svglide-theme/v1"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
GLOBAL_THEME_REGISTRY = beautiful_template_runtime.FAMILIES_PATH
PROJECT_THEME_REGISTRY = Path("02-plan/theme-registry.json")
PREPARED_SVG_DIR = Path("04-svg/prepared")
CORE_COLOR_ROLES = (
    "background",
    "surface",
    "text",
    "muted",
    "primary",
    "accent",
    "success",
    "warning",
    "danger",
)
CORE_TOKENS = tuple(f"color.{role}" for role in CORE_COLOR_ROLES)
DEFAULT_STATUS_COLORS = {
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}
HEX_COLOR_RE = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")
HEX_COLOR_SCAN_RE = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![0-9A-Fa-f])")
SVG_COLOR_ATTRS = {"fill", "stroke", "color"}


class ThemeError(ValueError):
    pass


def file_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json_sha256(payload: Any) -> str:
    data = json.dumps(_canonicalize(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def theme_sha256(theme: dict[str, Any]) -> str:
    return stable_json_sha256(theme)


def normalize_hex_color(value: str) -> str:
    if not isinstance(value, str):
        raise ThemeError(f"hex color must be a string, got {type(value).__name__}")
    raw = value.strip()
    if not HEX_COLOR_RE.fullmatch(raw):
        raise ThemeError(f"invalid hex color: {value!r}")
    digits = raw[1:]
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return f"#{digits.upper()}"


def relative_luminance(color: str) -> float:
    normalized = normalize_hex_color(color)
    channels = [int(normalized[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter = max(first, second)
    darker = min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def load_registry(root: Path | str | None = None) -> dict[str, Any]:
    path = theme_registry_path(root)
    payload = beautiful_template_runtime.theme_registry() if path == beautiful_template_runtime.FAMILIES_PATH else _read_json_object(path)
    if not isinstance(payload.get("themes"), list):
        raise ThemeError(f"theme registry must contain a themes array: {path}")
    return payload


def theme_registry_path(root: Path | str | None = None) -> Path:
    return _theme_registry_path(root)


def theme_file_path(theme_id: str, root: Path | str | None = None) -> Path | None:
    registry_path = theme_registry_path(root)
    registry = beautiful_template_runtime.theme_registry() if registry_path == beautiful_template_runtime.FAMILIES_PATH else _read_json_object(registry_path)
    record = _theme_record(registry, theme_id)
    if record is None:
        raise ThemeError(f"theme {theme_id!r} is not present in registry {registry_path}")
    raw_path = record.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    return _resolve_theme_file_path(registry_path, raw_path)


def load_theme(theme_id: str, root: Path | str | None = None) -> dict[str, Any]:
    if not isinstance(theme_id, str) or not theme_id:
        raise ThemeError("theme_id is required")
    registry_path = theme_registry_path(root)
    registry = beautiful_template_runtime.theme_registry() if registry_path == beautiful_template_runtime.FAMILIES_PATH else _read_json_object(registry_path)
    record = _theme_record(registry, theme_id)
    if record is None:
        raise ThemeError(f"theme {theme_id!r} is not present in registry {registry_path}")
    if record.get("status") not in (None, "active"):
        raise ThemeError(f"theme {theme_id!r} is not active")
    theme = _resolve_theme_payload(registry_path, record)
    adapted = _adapt_theme_spec(theme)
    issues = validate_theme_spec(adapted)
    if issues:
        details = "; ".join(f"{item['path']}: {item['message']}" for item in issues[:3])
        raise ThemeError(f"invalid theme {theme_id!r}: {details}")
    return adapted


def validate_theme_spec(theme: Any) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(theme, dict):
        return [_issue("theme_type_invalid", "$", "ThemeSpec must be an object")]

    required = ["schema_version", "theme_id", "mode", "colors", "semantic_colors", "tokens", "contrast", "allowed_color_roles"]
    for key in required:
        if key not in theme:
            issues.append(_issue("theme_required_missing", f"$.{key}", "required property is missing"))

    if theme.get("schema_version") != THEME_SPEC_VERSION:
        issues.append(_issue("theme_version_invalid", "$.schema_version", f"schema_version must be {THEME_SPEC_VERSION}"))
    if not isinstance(theme.get("theme_id"), str) or not theme.get("theme_id"):
        issues.append(_issue("theme_id_invalid", "$.theme_id", "theme_id must be a non-empty string"))
    if theme.get("mode") not in {"light", "dark"}:
        issues.append(_issue("theme_mode_invalid", "$.mode", "mode must be light or dark"))

    colors = theme.get("colors")
    if not isinstance(colors, dict):
        issues.append(_issue("theme_colors_invalid", "$.colors", "colors must be an object"))
    else:
        for role in CORE_COLOR_ROLES:
            if role not in colors:
                issues.append(_issue("theme_color_missing", f"$.colors.{role}", "core color is missing"))
                continue
            if _normalize_optional_color(colors.get(role)) is None:
                issues.append(_issue("theme_color_hex_invalid", f"$.colors.{role}", "core color must be #rgb or #rrggbb"))
        for role, value in colors.items():
            if not isinstance(role, str):
                issues.append(_issue("theme_color_role_invalid", "$.colors", "color role names must be strings"))
                continue
            if _normalize_optional_color(value) is None:
                issues.append(_issue("theme_color_hex_invalid", f"$.colors.{role}", "color value must be #rgb or #rrggbb"))

    tokens = theme.get("tokens")
    if not isinstance(tokens, dict):
        issues.append(_issue("theme_tokens_invalid", "$.tokens", "tokens must be an object"))
    else:
        for token in CORE_TOKENS:
            if token not in tokens:
                issues.append(_issue("theme_token_missing", f"$.tokens.{token}", "core color token is missing"))
                continue
            if _resolve_color_value(tokens.get(token), theme) is None:
                issues.append(_issue("theme_token_color_invalid", f"$.tokens.{token}", "token must resolve to #rgb or #rrggbb"))
        for token, value in tokens.items():
            if not isinstance(token, str) or not token:
                issues.append(_issue("theme_token_name_invalid", "$.tokens", "token names must be non-empty strings"))
                continue
            if _resolve_color_value(value, theme) is None:
                issues.append(_issue("theme_token_color_invalid", f"$.tokens.{token}", "token must resolve to #rgb or #rrggbb"))

    semantic_colors = theme.get("semantic_colors")
    if not isinstance(semantic_colors, dict) or not semantic_colors:
        issues.append(_issue("theme_semantic_colors_invalid", "$.semantic_colors", "semantic_colors must be a non-empty object"))
    else:
        for role, value in semantic_colors.items():
            if not isinstance(role, str) or not role:
                issues.append(_issue("theme_semantic_role_invalid", "$.semantic_colors", "semantic color roles must be non-empty strings"))
                continue
            if _resolve_color_value(value, theme) is None:
                issues.append(_issue("theme_semantic_color_invalid", f"$.semantic_colors.{role}", "semantic color must resolve to #rgb or #rrggbb"))

    contrast = theme.get("contrast")
    if not isinstance(contrast, dict):
        issues.append(_issue("theme_contrast_invalid", "$.contrast", "contrast must be an object"))
    else:
        min_text = contrast.get("min_text_contrast")
        if isinstance(min_text, bool) or not isinstance(min_text, (int, float)):
            issues.append(_issue("theme_contrast_min_text_invalid", "$.contrast.min_text_contrast", "min_text_contrast must be a number"))

    allowed = theme.get("allowed_color_roles")
    if not isinstance(allowed, list) or not allowed:
        issues.append(_issue("theme_allowed_roles_invalid", "$.allowed_color_roles", "allowed_color_roles must be a non-empty array"))
    else:
        for index, role in enumerate(allowed):
            if not isinstance(role, str) or not role:
                issues.append(_issue("theme_allowed_role_invalid", f"$.allowed_color_roles[{index}]", "allowed color roles must be non-empty strings"))
        missing_roles = [role for role in CORE_COLOR_ROLES if role not in allowed]
        for role in missing_roles:
            issues.append(_issue("theme_allowed_role_missing", f"$.allowed_color_roles.{role}", "core color role must be allowed"))

    data_series = theme.get("data_series")
    if data_series is not None:
        if not isinstance(data_series, list):
            issues.append(_issue("theme_data_series_invalid", "$.data_series", "data_series must be an array"))
        else:
            for index, value in enumerate(data_series):
                if _normalize_optional_color(value) is None:
                    issues.append(_issue("theme_data_series_color_invalid", f"$.data_series[{index}]", "data series color must be #rgb or #rrggbb"))

    return issues


def extract_svg_colors(svg_path: Path | str) -> list[str]:
    try:
        root = ElementTree.fromstring(Path(svg_path).read_text(encoding="utf-8"))
    except (OSError, ElementTree.ParseError) as err:
        raise ThemeError(f"unable to read SVG colors from {svg_path}: {err}") from err

    colors: list[str] = []
    seen: set[str] = set()

    def add_from_text(value: str) -> None:
        for match in HEX_COLOR_SCAN_RE.finditer(value):
            color = normalize_hex_color(match.group(0))
            if color not in seen:
                seen.add(color)
                colors.append(color)

    for element in root.iter():
        for raw_name, value in element.attrib.items():
            name = _local_name(raw_name).lower()
            if name in SVG_COLOR_ATTRS or name == "style":
                add_from_text(value)
    return colors


def classify_color(color: str, theme: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_hex_color(color)
    spec = _adapt_theme_spec(theme)

    token_matches = _matching_resolved_values(spec.get("tokens"), spec, normalized)
    if token_matches:
        return {"kind": "theme_token", "color": normalized, "role": token_matches[0], "matches": token_matches}

    semantic_matches = _matching_resolved_values(spec.get("semantic_colors"), spec, normalized)
    if semantic_matches:
        return {"kind": "semantic", "color": normalized, "role": semantic_matches[0], "matches": semantic_matches}

    data_series = spec.get("data_series")
    if isinstance(data_series, list):
        matches = [f"data_series[{index}]" for index, value in enumerate(data_series) if _normalize_optional_color(value) == normalized]
        if matches:
            return {"kind": "data_series", "color": normalized, "role": matches[0], "matches": matches}

    return {"kind": "unknown", "color": normalized, "role": None, "matches": []}


def prepared_svg_hashes(project_root: Path | str) -> list[dict[str, str]]:
    project = Path(project_root)
    svg_dir = project / PREPARED_SVG_DIR
    if not svg_dir.exists():
        return []
    return [
        {
            "path": path.relative_to(project).as_posix(),
            "sha256": file_sha256(path),
        }
        for path in sorted(svg_dir.glob("*.svg"))
        if path.is_file()
    ]


def _theme_registry_path(root: Path | str | None) -> Path:
    if root is None:
        return beautiful_template_runtime.FAMILIES_PATH
    base = Path(root)
    if base.is_file():
        return base
    candidates = [base / "registry.json", base / PROJECT_THEME_REGISTRY]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return beautiful_template_runtime.FAMILIES_PATH


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ThemeError(f"missing JSON file: {path}") from err
    except json.JSONDecodeError as err:
        raise ThemeError(f"invalid JSON in {path}: {err}") from err
    if not isinstance(payload, dict):
        raise ThemeError(f"expected JSON object: {path}")
    return payload


def _theme_record(registry: dict[str, Any], theme_id: str) -> dict[str, Any] | None:
    themes = registry.get("themes")
    if isinstance(themes, list):
        for item in themes:
            if isinstance(item, dict) and item.get("id") == theme_id:
                return item
    if isinstance(themes, dict):
        item = themes.get(theme_id)
        if isinstance(item, dict):
            return item
    return None


def _resolve_theme_payload(registry_path: Path, record: dict[str, Any]) -> dict[str, Any]:
    raw_path = record.get("path")
    if isinstance(raw_path, str) and raw_path:
        return _read_json_object(_resolve_theme_file_path(registry_path, raw_path))
    if isinstance(record.get("colors"), dict):
        theme_id = str(record.get("id") or record.get("theme_id") or "")
        if theme_id in beautiful_template_runtime.LEGACY_THEME_COLORS:
            return beautiful_template_runtime.theme_payload(theme_id)
        return record
    raise ThemeError(f"theme record {record.get('id')!r} has no theme payload")


def _resolve_theme_file_path(registry_path: Path, raw_path: str) -> Path:
    path_value = Path(raw_path)
    candidates = [path_value] if path_value.is_absolute() else [_registry_relative_base(registry_path) / path_value, registry_path.parent / path_value]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise ThemeError(f"theme file not found: {raw_path}")


def _registry_relative_base(registry_path: Path) -> Path:
    parts = registry_path.parts
    marker = ("skills", "lark-slides", "scripts", "artboard_renderer", "themes", "registry.json")
    for index in range(0, len(parts) - len(marker) + 1):
        if tuple(parts[index : index + len(marker)]) == marker:
            return Path(*parts[:index])
    if registry_path.parent.name == "02-plan":
        return registry_path.parent.parent
    return registry_path.parent


def _adapt_theme_spec(theme: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(theme, dict):
        raise ThemeError("theme must be an object")
    raw_colors = theme.get("colors") if isinstance(theme.get("colors"), dict) else {}
    colors = _normalized_colors(raw_colors)
    adapted: dict[str, Any] = dict(theme)
    adapted["schema_version"] = theme.get("schema_version") or THEME_SPEC_VERSION
    adapted["theme_id"] = theme.get("theme_id") or theme.get("id") or "theme"
    adapted["mode"] = theme.get("mode") if theme.get("mode") in {"light", "dark"} else _infer_mode(colors["background"])
    adapted["colors"] = colors
    if "semantic_colors" not in adapted or not isinstance(adapted.get("semantic_colors"), dict):
        adapted["semantic_colors"] = _default_semantic_colors(colors)
    if "tokens" not in adapted or not isinstance(adapted.get("tokens"), dict):
        adapted["tokens"] = _default_tokens(colors)
    else:
        tokens = dict(adapted["tokens"])
        for role in CORE_COLOR_ROLES:
            tokens.setdefault(f"color.{role}", colors[role])
        adapted["tokens"] = tokens
    if "contrast" not in adapted or not isinstance(adapted.get("contrast"), dict):
        adapted["contrast"] = {"min_text_contrast": 4.5}
    if "allowed_color_roles" not in adapted or not isinstance(adapted.get("allowed_color_roles"), list):
        adapted["allowed_color_roles"] = list(CORE_COLOR_ROLES)
    if "data_series" not in adapted:
        adapted["data_series"] = [colors["primary"], colors["accent"], colors["success"], colors["warning"], colors["danger"]]
    return _normalize_theme_colors(adapted)


def _normalized_colors(raw_colors: dict[str, Any]) -> dict[str, str]:
    colors: dict[str, str] = {}
    colors["background"] = normalize_hex_color(str(raw_colors.get("background") or "#0F172A"))
    surface = raw_colors.get("surface") or raw_colors.get("panel") or "#111827"
    colors["surface"] = normalize_hex_color(str(surface))
    colors["text"] = normalize_hex_color(str(raw_colors.get("text") or "#F8FAFC"))
    colors["muted"] = normalize_hex_color(str(raw_colors.get("muted") or "#CBD5E1"))
    colors["primary"] = normalize_hex_color(str(raw_colors.get("primary") or "#60A5FA"))
    colors["accent"] = normalize_hex_color(str(raw_colors.get("accent") or "#A78BFA"))
    for role, fallback in DEFAULT_STATUS_COLORS.items():
        colors[role] = normalize_hex_color(str(raw_colors.get(role) or fallback))
    for role, value in raw_colors.items():
        if isinstance(role, str) and role not in colors:
            colors[role] = normalize_hex_color(str(value))
    colors.setdefault("panel", colors["surface"])
    return colors


def _default_tokens(colors: dict[str, str]) -> dict[str, str]:
    return {f"color.{role}": colors[role] for role in CORE_COLOR_ROLES}


def _default_semantic_colors(colors: dict[str, str]) -> dict[str, str]:
    return {
        "canvas.background": colors["background"],
        "surface.default": colors["surface"],
        "text.default": colors["text"],
        "text.muted": colors["muted"],
        "brand.primary": colors["primary"],
        "brand.accent": colors["accent"],
        "status.success": colors["success"],
        "status.warning": colors["warning"],
        "status.danger": colors["danger"],
    }


def _infer_mode(background: str) -> str:
    return "dark" if relative_luminance(background) < 0.5 else "light"


def _normalize_theme_colors(theme: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(theme, ensure_ascii=False))
    colors = normalized.get("colors")
    if isinstance(colors, dict):
        normalized["colors"] = {role: normalize_hex_color(value) for role, value in colors.items()}
    for key in ("tokens", "semantic_colors"):
        values = normalized.get(key)
        if isinstance(values, dict):
            normalized[key] = {
                role: normalize_hex_color(value) if isinstance(value, str) and HEX_COLOR_RE.fullmatch(value.strip()) else value
                for role, value in values.items()
            }
    data_series = normalized.get("data_series")
    if isinstance(data_series, list):
        normalized["data_series"] = [normalize_hex_color(value) for value in data_series]
    return normalized


def _normalize_optional_color(value: Any) -> str | None:
    try:
        return normalize_hex_color(value)
    except ThemeError:
        return None


def _resolve_color_value(value: Any, theme: dict[str, Any], *, depth: int = 0) -> str | None:
    if depth > 4 or not isinstance(value, str):
        return None
    direct = _normalize_optional_color(value)
    if direct is not None:
        return direct
    colors = theme.get("colors") if isinstance(theme.get("colors"), dict) else {}
    tokens = theme.get("tokens") if isinstance(theme.get("tokens"), dict) else {}
    color_key = value.removeprefix("colors.") if value.startswith("colors.") else value
    if isinstance(colors, dict) and color_key in colors:
        return _normalize_optional_color(colors[color_key])
    token_key = value.removeprefix("tokens.") if value.startswith("tokens.") else value
    if isinstance(tokens, dict) and token_key in tokens:
        return _resolve_color_value(tokens[token_key], theme, depth=depth + 1)
    return None


def _matching_resolved_values(values: Any, theme: dict[str, Any], color: str) -> list[str]:
    if not isinstance(values, dict):
        return []
    matches: list[str] = []
    for role, value in values.items():
        if isinstance(role, str) and _resolve_color_value(value, theme) == color:
            matches.append(role)
    return matches


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonicalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    if isinstance(value, str):
        normalized = _normalize_optional_color(value)
        return normalized if normalized is not None else value
    return value


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1] if "}" in name else name


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}
