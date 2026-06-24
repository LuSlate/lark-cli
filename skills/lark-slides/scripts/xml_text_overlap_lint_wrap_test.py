# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import unittest

import xml_text_overlap_lint


def make_slide(shapes: str) -> str:
    return f"""
    <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
      <slide xmlns="http://www.larkoffice.com/sml/2.0">
        <data>{shapes}</data>
      </slide>
    </presentation>
    """


def text_shape(
    lines: list[str],
    *,
    text_type: str = "body",
    align: str = "left",
    x: int = 120,
    y: int = 120,
    width: int = 360,
    height: int = 120,
    font_size: int = 28,
) -> str:
    paragraphs = "".join(f"<p>{line}</p>" for line in lines)
    return f"""
    <shape type="text" topLeftX="{x}" topLeftY="{y}" width="{width}" height="{height}">
      <content textType="{text_type}" textAlign="{align}" fontSize="{font_size}">
        {paragraphs}
      </content>
    </shape>
    """


class XmlTextOverlapWrapLintTest(unittest.TestCase):
    def lint_one(self, shape_xml: str) -> dict:
        result = xml_text_overlap_lint.lint_xml(make_slide(shape_xml))
        self.assertEqual(result["summary"]["error_count"], 0)
        return result

    def issue_codes(self, result: dict) -> list[str]:
        return [
            issue["code"]
            for slide in result["slides"]
            for issue in slide["issues"]
        ]

    def assertWarnsCode(self, shape_xml: str, code: str) -> None:
        result = self.lint_one(shape_xml)
        self.assertIn(code, self.issue_codes(result))
        self.assertGreaterEqual(result["summary"]["warning_count"], 1)

    def assertDoesNotWarnCode(self, shape_xml: str, code: str) -> None:
        result = self.lint_one(shape_xml)
        self.assertNotIn(code, self.issue_codes(result))

    def test_wrap_lint_detects_orphan_line(self) -> None:
        cases = [
            ["把排版看成一套可维护的规则", "系统"],
            ["为什么大多数企业知识库最终都会", "失效"],
            ["让内容生产流程持续保持稳定的", "质量"],
            ["复杂协作权限需要清晰可读的继承", "边界"],
            ["自动化检查应该优先发现低级排版", "问题"],
        ]
        for lines in cases:
            with self.subTest(lines=lines):
                self.assertWarnsCode(text_shape(lines, width=520), "text_orphan_line")

    def test_wrap_lint_allows_orphan_line_controls(self) -> None:
        cases = [
            ["把排版看成", "一套可维护的规则系统"],
            ["为什么大多数企业知识库", "最终都会失效"],
            ["复杂协作权限需要", "清晰可读的继承边界"],
            ["自动化检查应该", "优先发现低级排版问题"],
            ["标题换行质量", "直接影响读者理解效率"],
        ]
        for lines in cases:
            with self.subTest(lines=lines):
                self.assertDoesNotWarnCode(text_shape(lines, width=520), "text_orphan_line")

    def test_wrap_lint_allows_multiline_body_with_short_final_line(self) -> None:
        shape_xml = text_shape(
            ["按行业、阶段、投资年份分层；剔除信息不可得或标签不完整样本。"],
            align="left",
            width=146,
            height=42,
            font_size=10,
        )
        self.assertDoesNotWarnCode(shape_xml, "text_orphan_line")

    def test_wrap_lint_detects_unnecessary_wrap_in_title_like_text(self) -> None:
        cases = [
            ["减少手工", "格式"],
            ["内容", "生产"],
            ["智能", "生成"],
            ["质量", "检查"],
            ["边界", "规则"],
        ]
        for lines in cases:
            with self.subTest(lines=lines):
                self.assertWarnsCode(text_shape(lines, text_type="headline", width=420), "text_unnecessary_wrap")

    def test_wrap_lint_allows_unnecessary_wrap_controls(self) -> None:
        cases = [
            ["减少手工格式"],
            ["内容生产"],
            ["智能生成"],
            ["质量检查"],
            ["边界规则"],
        ]
        for lines in cases:
            with self.subTest(lines=lines):
                self.assertDoesNotWarnCode(text_shape(lines, text_type="headline", width=420), "text_unnecessary_wrap")

    def test_wrap_lint_detects_short_display_text_that_will_auto_wrap(self) -> None:
        cases = [
            "模型、平台、数据、研究",
            "产业协同能力研究",
            "接口边界安全研究",
            "投后监测策略研究",
            "评分稳定性复盘研究",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertWarnsCode(
                    text_shape([text], width=190, height=26, font_size=26),
                    "text_unnecessary_wrap",
                )

    def test_wrap_lint_allows_body_text_that_will_auto_wrap(self) -> None:
        shape_xml = text_shape(
            ["按行业、阶段、投资年份分层；剔除信息不可得或标签不完整样本。"],
            width=146,
            height=42,
            font_size=10,
        )
        self.assertDoesNotWarnCode(shape_xml, "text_unnecessary_wrap")

    def test_wrap_lint_detects_center_wrapped_text(self) -> None:
        cases = [
            ["下一代智能", "办公系统"],
            ["企业知识库", "治理方案"],
            ["自动化排版", "质量基线"],
            ["协作权限", "继承模型"],
            ["内容生产", "智能流程"],
        ]
        for lines in cases:
            with self.subTest(lines=lines):
                self.assertWarnsCode(text_shape(lines, align="center", y=150), "text_center_wrapped")

    def test_wrap_lint_detects_center_text_that_will_auto_wrap(self) -> None:
        shape_xml = text_shape(
            ["平台价值：让数据、模型和流程在同一界面被调用、解释和追踪。"],
            align="center",
            width=248,
            height=12,
            font_size=10,
        )
        self.assertWarnsCode(shape_xml, "text_center_wrapped")

    def test_wrap_lint_allows_center_wrapped_controls(self) -> None:
        cases = [
            text_shape(["下一代智能办公系统"], align="center"),
            text_shape(["企业知识库治理方案"], align="center"),
            text_shape(["自动化排版质量基线"], align="left"),
            text_shape(["封面主标题", "副标题"], text_type="title", align="center", y=210),
            text_shape(["金句内容", "保持居中"], text_type="quote", align="center"),
            text_shape(["企业筛选 / 排序 / 尽调建议"], align="center", width=132, height=20, font_size=10),
            text_shape(["经营异动 / 风险预警 / 里程碑"], align="center", width=136, height=12, font_size=10),
            text_shape(
                ["建议采用 Top-N 命中率、风险预警召回率和评分稳定性三类指标，不只看单一准确率。"],
                align="left",
                width=146,
                height=42,
                font_size=10,
            ),
        ]
        for shape_xml in cases:
            with self.subTest(shape=shape_xml):
                self.assertDoesNotWarnCode(shape_xml, "text_center_wrapped")

    def test_wrap_lint_detects_text_box_too_short(self) -> None:
        cases = [
            "REST API / 批量文件 / 定时同步",
            "鉴权、审计、脱敏与最小权限",
            "优先适配现有系统，减少重复建设",
            "服务化部署、权限隔离、日志留痕",
            "试运行三个月，终验后三年维保",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertWarnsCode(
                    text_shape([text], width=280, height=2, font_size=18),
                    "text_box_too_short",
                )

    def test_wrap_lint_allows_text_box_with_sufficient_height(self) -> None:
        cases = [
            "REST API / 批量文件 / 定时同步",
            "鉴权、审计、脱敏与最小权限",
            "优先适配现有系统，减少重复建设",
            "11",
            "KR1",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertDoesNotWarnCode(
                    text_shape([text], width=450, height=48, font_size=18),
                    "text_box_too_short",
                )

    def test_wrap_lint_keeps_bbox_overlap_detection(self) -> None:
        result = xml_text_overlap_lint.lint_xml(
            make_slide(
                text_shape(["Title"], text_type="title", x=80, y=80, width=300, height=60)
                + text_shape(["Body"], text_type="body", x=80, y=80, width=300, height=80)
            )
        )
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertIn("bbox_overlap", self.issue_codes(result))


if __name__ == "__main__":
    unittest.main()
