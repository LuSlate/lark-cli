#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Mapping
from html import escape
from typing import Any


SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"
SLIDE_NS = "https://slides.bytedance.com/ns"
CONTRACT_VERSION = "svglide-authoring-contract/v1"


def xml_escape(value: object) -> str:
    return escape(str(value), quote=True)


def svg_attrs(attrs: Mapping[str, object | None]) -> str:
    return " ".join(f'{key}="{xml_escape(value)}"' for key, value in attrs.items() if value is not None)


def _with_extra(base: dict[str, str], extra: Mapping[str, Any] | None = None) -> dict[str, str]:
    if extra:
        for key, value in extra.items():
            if value is not None:
                base[str(key)] = str(value)
    return base


def svg_root_attrs(extra: Mapping[str, Any] | None = None) -> dict[str, str]:
    return _with_extra(
        {
            "xmlns": SVG_NS,
            "xmlns:slide": SLIDE_NS,
            "slide:role": "slide",
            "slide:contract-version": CONTRACT_VERSION,
        },
        extra,
    )


def shape_attrs(extra: Mapping[str, Any] | None = None) -> dict[str, str]:
    return _with_extra({"slide:role": "shape"}, extra)


def image_attrs(extra: Mapping[str, Any] | None = None) -> dict[str, str]:
    return _with_extra({"slide:role": "image"}, extra)


def text_shape_attrs(extra: Mapping[str, Any] | None = None) -> dict[str, str]:
    return _with_extra({"slide:role": "shape", "slide:shape-type": "text"}, extra)


def chart_marker_attrs(chart_ref: str, extra: Mapping[str, Any] | None = None) -> dict[str, str]:
    return _with_extra({"slide:role": "chart", "slide:chart-ref": chart_ref}, extra)
