#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
SKILL_ROOT = SCRIPT_PATH.parents[1]
DEFAULT_REPO_ROOT = SCRIPT_PATH.parents[3]
PRIVATE_MANIFEST_REL = Path("references/routes/create-svg/private-recipes.manifest.json")

SKILL_SCAN_TARGETS = [
    Path("SKILL.md"),
    Path("references"),
    Path("assets/templates"),
    Path("scripts"),
    Path("tests"),
]

REPO_SCAN_TARGETS = [
    Path("shortcuts/slides"),
    Path("tests"),
    Path("tests/cli_e2e/slides/coverage.md"),
    Path("README.md"),
    Path("README.zh.md"),
    Path("docs"),
]

TEXT_FILE_SUFFIXES = {
    "",
    ".cfg",
    ".css",
    ".go",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".mjs",
    ".py",
    ".svg",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class Issue:
    path: str
    line: int
    column: int
    code: str
    token: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lint public SVGlide create-svg docs for route-private recipe leaks."
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Repository root. Defaults to the root inferred from this script location.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable diagnostics.",
    )
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(f"missing private recipe manifest: {path}") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"invalid JSON in private recipe manifest: {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"private recipe manifest must be a JSON object: {path}")
    return value


def expect_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise SystemExit(f"manifest field must be a non-empty string list: {field}")
    return value


def load_manifest_tokens(manifest: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    recipes = manifest.get("recipes")
    if not isinstance(recipes, (dict, list)) or not recipes:
        raise SystemExit('manifest field must be a non-empty object or list: recipes')

    private_ids: list[str] = []
    if isinstance(recipes, dict):
        private_ids = [str(recipe_id) for recipe_id in recipes.keys() if str(recipe_id)]
        if len(private_ids) != len(recipes):
            raise SystemExit("manifest recipes object must not contain empty ids")
    else:
        for recipe in recipes:
            if not isinstance(recipe, dict):
                raise SystemExit("manifest recipes must contain JSON objects")
            recipe_id = recipe.get("recipe_id")
            if not isinstance(recipe_id, str) or not recipe_id:
                raise SystemExit('each manifest recipe must include a non-empty "recipe_id"')
            private_ids.append(recipe_id)

    dotted_ids = expect_string_list(
        manifest.get("blocked_research_dotted_recipe_ids"),
        "blocked_research_dotted_recipe_ids",
    )
    absolute_paths = expect_string_list(
        manifest.get("blocked_absolute_paths"),
        "blocked_absolute_paths",
    )
    for label, values in (
        ("private recipe ids", private_ids),
        ("research dotted recipe ids", dotted_ids),
        ("blocked absolute paths", absolute_paths),
    ):
        duplicates = sorted({item for item in values if values.count(item) > 1})
        if duplicates:
            raise SystemExit(f"duplicate {label}: {', '.join(duplicates)}")
    return private_ids, dotted_ids, absolute_paths


def normalize_rel(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def is_under(rel_path: str, prefix: str) -> bool:
    return rel_path == prefix or rel_path.startswith(f"{prefix}/")


def is_allowed_route_private_path(path: Path, repo_root: Path) -> bool:
    skill_rel = normalize_rel(path, SKILL_ROOT)
    if skill_rel is not None:
        if skill_rel in {
            "references/routes/create-svg/private-recipes.manifest.json",
        }:
            return True
        if is_under(skill_rel, "references/routes/create-svg/private"):
            return True
        if is_under(skill_rel, "tests/fixtures/routes/create-svg/private"):
            return True
        if is_under(skill_rel, "tests/fixtures/routes/create-svg/internal-reports"):
            return True

    repo_rel = normalize_rel(path, repo_root)
    if repo_rel is not None:
        if is_under(repo_rel, "tests/fixtures/routes/create-svg/private"):
            return True
        if is_under(repo_rel, "tests/fixtures/routes/create-svg/internal-reports"):
            return True

    return False


def iter_existing_scan_roots(repo_root: Path) -> Iterable[Path]:
    yielded: set[Path] = set()
    for target in SKILL_SCAN_TARGETS:
        path = SKILL_ROOT / target
        if path.exists() and path.resolve() not in yielded:
            yielded.add(path.resolve())
            yield path
    for target in REPO_SCAN_TARGETS:
        path = repo_root / target
        if path.exists() and path.resolve() not in yielded:
            yielded.add(path.resolve())
            yield path


def iter_text_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        candidates = [root]
    else:
        candidates = [path for path in root.rglob("*") if path.is_file()]
    for path in candidates:
        if path.suffix.lower() in TEXT_FILE_SUFFIXES:
            yield path


def line_column(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    line_start = text.rfind("\n", 0, index) + 1
    return line, index - line_start + 1


def find_token_issues(path: Path, text: str, tokens: list[str], code: str) -> list[Issue]:
    issues: list[Issue] = []
    for token in tokens:
        pattern = re.compile(rf"(?<![A-Za-z0-9_.-]){re.escape(token)}(?![A-Za-z0-9_.-])")
        for match in pattern.finditer(text):
            line, column = line_column(text, match.start())
            issues.append(
                Issue(
                    path=path.as_posix(),
                    line=line,
                    column=column,
                    code=code,
                    token=token,
                )
            )
    return issues


def lint_file(
    path: Path,
    repo_root: Path,
    private_ids: list[str],
    dotted_ids: list[str],
    absolute_paths: list[str],
) -> list[Issue]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    if is_allowed_route_private_path(path, repo_root):
        return []

    display_path = Path(normalize_rel(path, repo_root) or path.as_posix())
    issues: list[Issue] = []
    issues.extend(find_token_issues(display_path, text, private_ids, "private_recipe_id_leak"))
    issues.extend(find_token_issues(display_path, text, dotted_ids, "research_dotted_recipe_id_leak"))
    issues.extend(find_token_issues(display_path, text, absolute_paths, "research_absolute_path_leak"))
    return issues


def lint(repo_root: Path) -> list[Issue]:
    manifest_path = SKILL_ROOT / PRIVATE_MANIFEST_REL
    manifest = load_json(manifest_path)
    private_ids, dotted_ids, absolute_paths = load_manifest_tokens(manifest)

    issues: list[Issue] = []
    seen_files: set[Path] = set()
    for root in iter_existing_scan_roots(repo_root):
        for path in iter_text_files(root):
            resolved = path.resolve()
            if resolved in seen_files:
                continue
            seen_files.add(resolved)
            issues.extend(lint_file(path, repo_root, private_ids, dotted_ids, absolute_paths))

    return sorted(issues, key=lambda issue: (issue.path, issue.line, issue.column, issue.code, issue.token))


def issue_to_dict(issue: Issue) -> dict[str, Any]:
    return {
        "path": issue.path,
        "line": issue.line,
        "column": issue.column,
        "code": issue.code,
        "token_hash": hashlib.sha256(issue.token.encode("utf-8")).hexdigest(),
    }


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    issues = lint(repo_root)
    if args.json:
        print(json.dumps({"issue_count": len(issues), "issues": [issue_to_dict(issue) for issue in issues]}, indent=2))
    else:
        for issue in issues:
            token_hash = hashlib.sha256(issue.token.encode("utf-8")).hexdigest()[:12]
            print(f"{issue.path}:{issue.line}:{issue.column}: {issue.code}: token_hash={token_hash}")
        if issues:
            print(f"svg-private-docs-lint: found {len(issues)} issue(s)", file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
