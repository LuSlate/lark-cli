# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
FIXTURE_PROVIDER = SCRIPT_DIR / "fixtures/svglide_artboard/followup_model_loop/fixture_model_provider.py"


def run_fixture(prompt: str, stage: str, tmpdir: Path) -> dict[str, object]:
    output = tmpdir / f"{stage}-{hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:8]}.json"
    completed = subprocess.run(
        [sys.executable, FIXTURE_PROVIDER.as_posix(), "--stage", stage, "--raw-output", output.as_posix()],
        cwd=REPO_ROOT,
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return json.loads(output.read_text(encoding="utf-8"))


class SVGlideFixtureModelProviderTest(unittest.TestCase):
    def test_fixture_provider_outputs_prompt_specific_plans(self) -> None:
        prompts = ["spacex IPO 分析", "冰岛火山研究", "新西兰风光"]
        expected_topics = ["spacex IPO 分析", "冰岛火山研究", "新西兰风光"]

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            deck_plans = [run_fixture(prompt, "deck-planner", tmpdir) for prompt in prompts]
            slide_plans = [run_fixture(prompt, "slide-planner", tmpdir) for prompt in prompts]
            canvas_plans = [run_fixture(prompt, "canvas-planner", tmpdir) for prompt in prompts]

        self.assertEqual(expected_topics, [plan["topic"] for plan in deck_plans])
        self.assertEqual(3, len({plan["slides"][0]["title"] for plan in deck_plans}))
        self.assertEqual(3, len({json.dumps(plan, ensure_ascii=False, sort_keys=True) for plan in slide_plans}))
        self.assertEqual(3, len({json.dumps(plan, ensure_ascii=False, sort_keys=True) for plan in canvas_plans}))
        self.assertTrue(all(plan["asset_contracts"] for plan in canvas_plans))
        self.assertEqual(
            ["SpaceX IPO 分析框架", "冰岛火山研究框架", "新西兰风光路线"],
            [plan["slides"][0]["title"] for plan in canvas_plans],
        )

    def test_fixture_provider_prefers_instruction_raw_prompt_over_generic_prompt_text(self) -> None:
        contaminated_prompt = (
            "For SpaceX IPO analysis, avoid claiming a confirmed IPO date.\n"
            "Instruction:\n"
            '{\n  "schema_version": "svglide-instruction/v1",\n  "raw_prompt": "新西兰风光",\n  "audience": "旅行内容策划读者"\n}'
        )

        with tempfile.TemporaryDirectory() as tmp:
            deck_plan = run_fixture(contaminated_prompt, "deck-planner", Path(tmp))

        self.assertEqual("新西兰风光", deck_plan["topic"])
        self.assertEqual("新西兰风光路线", deck_plan["slides"][0]["title"])


if __name__ == "__main__":
    unittest.main()
