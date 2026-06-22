# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REFERENCES = ROOT / "skills" / "lark-slides" / "references"


REQUIRED_CONTRACT_FILES = {
    "skills/lark-slides/references/svglide-contract-compile-report.schema.json",
    "skills/lark-slides/references/svglide-contract-compile-manifest.schema.json",
    "skills/lark-slides/scripts/svglide_svg_contract.py",
    "skills/lark-slides/scripts/svglide_contract_compile.py",
}


class SVGlideDocsContractCompileTest(unittest.TestCase):
    def read_reference_json(self, name: str) -> dict[str, object]:
        return json.loads((REFERENCES / name).read_text(encoding="utf-8"))

    def test_contract_compile_files_are_registered_in_private_manifest(self) -> None:
        manifest = self.read_reference_json("svg-private-manifest.json")
        private_files = set(manifest.get("private_strategy_files", []))

        self.assertTrue(REQUIRED_CONTRACT_FILES.issubset(private_files))
        self.assertIn("skills/lark-slides/scripts/svglide_contract_compile.py", set(manifest.get("allowed_route_entrypoints", [])))

    def test_contract_compile_files_are_registered_in_private_rules(self) -> None:
        rules = self.read_reference_json("svglide-svg-private.rules.json")
        private_files = set(rules.get("private_strategy_files", []))
        write_scope = set(rules.get("write_scope", []))

        self.assertTrue(REQUIRED_CONTRACT_FILES.issubset(private_files))
        self.assertTrue(REQUIRED_CONTRACT_FILES.issubset(write_scope))
        self.assertIn("skills/lark-slides/scripts/svglide_contract_compile.py", set(rules.get("allowed_route_entrypoints", [])))
        self.assertIn("svglide_contract_compile.py", rules.get("checks_chain", []))
        artifact_dirs = rules.get("artifact_dirs")
        self.assertIsInstance(artifact_dirs, dict)
        self.assertEqual(artifact_dirs.get("artboard_raw"), ".lark-slides/plan/<deck-id>/04-artboard/raw/")
        self.assertEqual(artifact_dirs.get("contract_compile"), ".lark-slides/plan/<deck-id>/04-svg/contract/")


if __name__ == "__main__":
    unittest.main()
