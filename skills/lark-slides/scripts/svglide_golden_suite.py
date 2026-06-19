#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import svglide_chart_verify
import svglide_runtime_review
import svglide_semantic_advisory
import svglide_semantic_review
import svglide_source
import svglide_strategy_review


CASE_TYPES = ["data_news", "real_estate_planning", "data_dense_report"]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_svg(path: Path, texts: list[str], *, chart: bool = False) -> None:
    body = []
    if chart:
        body.append('<rect x="80" y="200" width="120" height="180" fill="#3366cc" />')
        body.append('<rect x="240" y="150" width="120" height="230" fill="#66aa99" />')
    for index, text in enumerate(texts):
        body.append(f'<text x="80" y="{80 + index * 34}">{text}</text>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540">{"".join(body)}</svg>', encoding="utf-8")


def evidence_items(case_type: str) -> list[dict[str, str]]:
    topics = {
        "data_news": "市场结构变化",
        "real_estate_planning": "片区空间规划",
        "data_dense_report": "经营指标复盘",
        "negative_english": "薄弱英文样例",
    }
    topic = topics[case_type]
    return [
        {"id": "item-001", "text": f"{topic}的第一条证据覆盖背景、时间、对象和关键变化，文本长度足以支撑图表页和内容页判断。"},
        {"id": "item-002", "text": f"{topic}的第二条证据覆盖对比样本、业务含义和主要风险，避免页面只剩口号或装饰性图表。"},
        {"id": "item-003", "text": f"{topic}的第三条证据覆盖后续动作、约束条件和可验证指标，能够支撑结尾页的行动建议。"},
    ]


def positive_plan(case_type: str) -> dict[str, Any]:
    labels = {
        "data_news": ("数据新闻", "市场变化"),
        "real_estate_planning": ("空间规划", "片区更新"),
        "data_dense_report": ("经营报告", "指标复盘"),
    }
    title_prefix, section = labels[case_type]
    return {
        "route": "svglide-svg",
        "language": "zh-CN",
        "audience": "业务决策团队",
        "deck_structure": ["cover", "content", "content", "closing"],
        "style_preset": "safe-native-v1",
        "slides": [
            {
                "page": 1,
                "page_type": "cover",
                "section": "开场",
                "role": "thesis",
                "title": f"{title_prefix}洞察简报",
                "key_message": f"{section}需要从结构证据进入判断",
                "body_points": ["明确本次判断对象", "锁定后续验证口径"],
                "renderer_id": "cover",
                "layout_family": "cover",
                "visual_recipe": "hero_typography",
                "source_refs": ["source:item-001"],
            },
            {
                "page": 2,
                "page_type": "content",
                "section": section,
                "role": "evidence",
                "title": f"{section}的第一组证据",
                "key_message": "核心变化已经具备连续验证信号",
                "body_points": ["证据一显示结构变化正在形成", "证据二说明变化不是单点扰动", "证据三给出后续观测口径"],
                "source_refs": ["source:item-001", "source:item-002"],
                "renderer_id": "chart",
                "layout_family": "chart",
                "visual_recipe": "micro_chart",
                "chart_contract": {"verify": "required", "data": [12, 18, 25], "labels": ["一", "二", "三"]},
            },
            {
                "page": 3,
                "page_type": "content",
                "section": section,
                "role": "implication",
                "title": f"{section}的业务含义",
                "key_message": "行动排序应围绕高确定性证据展开",
                "body_points": ["优先处理确定性最高的场景", "保留对不确定变量的监控", "把复盘口径前置到执行计划"],
                "source_refs": ["source:item-002", "source:item-003"],
                "renderer_id": "timeline",
                "layout_family": "timeline",
                "visual_recipe": "path_flow",
            },
            {
                "page": 4,
                "page_type": "closing",
                "section": "结论",
                "role": "takeaway",
                "title": f"{title_prefix}后续动作",
                "key_message": "下一步应把证据链转成可复跑行动",
                "body_points": ["保留当前证据链", "补齐缺口数据", "按周复盘关键变化"],
                "source_refs": ["source:item-003"],
                "renderer_id": "closing",
                "layout_family": "closing",
                "visual_recipe": "closing_cta",
            },
        ],
    }


def negative_plan() -> dict[str, Any]:
    return {
        "route": "svglide-svg",
        "language": "en-US",
        "audience": "",
        "deck_structure": ["content"],
        "slides": [
            {
                "page": 1,
                "title": "English Thin Chart",
                "key_message": "Thin",
                "body_points": ["Fast", "Cheap"],
                "renderer_id": "unknown",
                "layout_family": "chart",
                "visual_recipe": "unknown",
                "chart_contract": {"verify": "required"},
            }
        ],
    }


def build_project(root: Path, case_type: str, *, negative: bool = False) -> Path:
    project = root / case_type
    plan = negative_plan() if negative else positive_plan(case_type)
    write_json(project / "02-plan/slide_plan.json", plan)
    write_json(project / "source/evidence.json", {"schema_version": "svglide-evidence/v1", "source_status": "ready", "items": evidence_items(case_type)})
    slides = plan["slides"]
    for index, slide in enumerate(slides, 1):
        texts = [value for value in [slide.get("title"), slide.get("key_message"), *slide.get("body_points", [])] if isinstance(value, str)]
        write_svg(project / f"04-svg/prepared/page-{index:03d}.svg", texts, chart=bool(slide.get("chart_contract")))
    return project


def run_case(project: Path, *, expected_status: str, expected_codes: set[str] | None = None) -> dict[str, Any]:
    checks = [
        ("source", svglide_source.run_source),
        ("strategy_review", svglide_strategy_review.run_strategy_review),
        ("chart_verify", svglide_chart_verify.run_chart_verify),
        ("semantic_review", svglide_semantic_review.run_semantic_review),
        ("runtime_review", svglide_runtime_review.run_runtime_review),
        ("semantic_advisory", svglide_semantic_advisory.run_advisory),
    ]
    results: dict[str, Any] = {}
    issue_codes: set[str] = set()
    warning_count = 0
    for name, fn in checks:
        result = fn(project)
        results[name] = {"status": result.get("status"), "summary": result.get("summary", {})}
        for item in result.get("issues", []) if isinstance(result.get("issues"), list) else []:
            if isinstance(item, dict) and isinstance(item.get("code"), str):
                issue_codes.add(item["code"])
        summary = result.get("summary")
        if name == "semantic_advisory" and isinstance(summary, dict) and isinstance(summary.get("warning_count"), int):
            warning_count += summary["warning_count"]
    actual_status = "passed" if all(item["status"] == "passed" for item in results.values()) else "failed"
    expected_codes = expected_codes or set()
    missing_expected_codes = sorted(expected_codes - issue_codes)
    status = "passed" if actual_status == expected_status and not missing_expected_codes and (expected_status == "failed" or warning_count == 0) else "failed"
    return {
        "status": status,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "warning_count": warning_count,
        "issue_codes": sorted(issue_codes),
        "missing_expected_codes": missing_expected_codes,
        "checks": results,
    }


def run_suite(output_dir: Path | None = None) -> dict[str, Any]:
    temp_dir = Path(tempfile.mkdtemp(prefix="svglide-golden-"))
    try:
        cases = []
        for case_type in CASE_TYPES:
            project = build_project(temp_dir, case_type)
            cases.append({"name": case_type, **run_case(project, expected_status="passed")})
        negative_project = build_project(temp_dir, "negative_english", negative=True)
        cases.append(
            {
                "name": "negative_english",
                **run_case(
                    negative_project,
                    expected_status="failed",
                    expected_codes={"language_not_zh_cn", "audience_missing", "renderer_unknown", "chart_contract_data_missing"},
                ),
            }
        )
        failed = [case for case in cases if case["status"] != "passed"]
        result = {
            "schema_version": "svglide-golden-suite/v1",
            "status": "failed" if failed else "passed",
            "summary": {
                "case_count": len(cases),
                "failed_case_count": len(failed),
                "positive_case_count": len(CASE_TYPES),
                "warning_budget": 0,
            },
            "cases": cases,
        }
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            write_json(output_dir / "golden-suite.json", result)
        return result
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local SVGlide golden suite profile.")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_suite(args.output_dir)
    except Exception as error:
        print(f"svglide_golden_suite: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
