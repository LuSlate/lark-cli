#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_artboard_final_acceptance as final_acceptance


class ArtboardFinalAcceptanceTest(unittest.TestCase):
    def test_extract_gate_statuses(self) -> None:
        text = """
| Gate | Status | Owner | Reviewer verdict | Evidence |
|---:|---|---|---|---|
| 0 Baseline | DONE | executor | PASS | ok |
| 11 Packaging | DONE | executor | PASS | ok |
| 12a Instruction adherence | DONE | executor | PASS | ok |
| 12 Final | TODO | executor | PENDING | |
"""
        statuses = final_acceptance.extract_gate_statuses(text)
        self.assertEqual(statuses["0"]["status"], "DONE")
        self.assertEqual(statuses["11"]["reviewer_verdict"], "PASS")
        self.assertEqual(statuses["12a"]["reviewer_verdict"], "PASS")
        self.assertEqual(statuses["12"]["status"], "TODO")

    def test_extract_gate_statuses_rejects_missing_pass_in_validator_shape(self) -> None:
        text = """
| 0 Baseline | DONE | executor | PASS | ok |
| 1 Contract | IN_REVIEW | executor | PENDING | waiting |
"""
        statuses = final_acceptance.extract_gate_statuses(text)
        self.assertEqual(statuses["1"]["status"], "IN_REVIEW")
        self.assertNotEqual(statuses["1"]["reviewer_verdict"], "PASS")

    def test_gate12a_is_required_for_final_acceptance(self) -> None:
        text = "\n".join(
            f"| {gate} Gate | DONE | executor | PASS | ok |"
            for gate in range(0, 12)
        )
        statuses = final_acceptance.extract_gate_statuses(text)
        missing = []
        for gate in [*(str(value) for value in range(0, 12)), "12a"]:
            status = statuses.get(gate)
            if status is None or status.get("status") != "DONE" or status.get("reviewer_verdict") != "PASS":
                missing.append(gate)
        self.assertEqual(missing, ["12a"])


if __name__ == "__main__":
    unittest.main()
