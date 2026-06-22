#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


CHECK_VERSION = "svglide-artboard-package-check/v1"
CHECK_STAGE = "package_check"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
ARTBOARD_RENDERER_DIR = SCRIPT_DIR / "artboard_renderer"
PACKAGE_CHECK = Path("06-check/artboard-package-check.json")
PACKAGE_RECEIPT = Path("receipts/artboard-package-check.json")

REQUIRED_DEPENDENCIES = {
    "satori": "0.26.0",
    "@resvg/resvg-js": "2.6.2",
}
REQUIRED_EMBED_PATTERNS = {
    "skills/*/prompts",
    "skills/*/scripts/*.py",
    "skills/*/scripts/artboard_renderer/*.mjs",
    "skills/*/scripts/artboard_renderer/package.json",
    "skills/*/scripts/artboard_renderer/pnpm-lock.yaml",
    "skills/*/scripts/artboard_renderer/components",
    "skills/*/scripts/artboard_renderer/dist",
    "skills/*/scripts/artboard_renderer/templates",
    "skills/*/scripts/artboard_renderer/themes",
}
FORBIDDEN_EMBED_PATTERNS = {
    "skills/*/scripts",
    "skills/*/scripts/artboard_renderer",
    "skills/*/scripts/artboard_renderer/node_modules",
}
SCAN_PATHS = (
    "package.json",
    "pnpm-lock.yaml",
    "render.mjs",
    "dist/render.mjs",
    "templates/README.md",
)
LOCAL_SOURCE_MARKERS = (
    "/Users/",
    "file:../",
    "file:../../",
    "SVGlide/satori",
    "../satori",
)
BUNDLED_SATORI_MARKERS = (
    "node_modules/.pnpm/satori@",
    "node_modules/satori/dist/index.js",
)


class PackageCheckError(Exception):
    pass


def normalize_arch(machine: str) -> str:
    value = machine.strip().lower()
    if value in {"x86_64", "amd64", "x64"}:
        return "x64"
    if value in {"arm64", "aarch64"}:
        return "arm64"
    return value or "unknown"


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise PackageCheckError(f"missing JSON file: {path}") from err
    except json.JSONDecodeError as err:
        raise PackageCheckError(f"invalid JSON file: {path}: {err}") from err
    if not isinstance(payload, dict):
        raise PackageCheckError(f"expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def repo_rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def exact_dependency(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and not value.startswith(("^", "~", "file:", "workspace:", "link:"))


def validate_dependency_policy(package_payload: dict[str, Any], lockfile_text: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    dependencies = package_payload.get("dependencies")
    if not isinstance(dependencies, dict):
        return [{"code": "package_dependencies_missing", "message": "package.json must declare dependencies"}]
    for name, expected in REQUIRED_DEPENDENCIES.items():
        actual = dependencies.get(name)
        if actual != expected:
            issues.append({"code": "package_dependency_version_mismatch", "message": f"{name} must be pinned to {expected}, got {actual!r}"})
        elif not exact_dependency(actual):
            issues.append({"code": "package_dependency_not_exact", "message": f"{name} must use an exact registry version"})
    package_text = json.dumps(package_payload, ensure_ascii=False, sort_keys=True)
    if "file:" in package_text or "workspace:" in package_text or "link:" in package_text:
        issues.append({"code": "package_local_dependency", "message": "package.json must not use file/workspace/link dependencies"})
    for marker in ("file:../", "file:../../", "link:", "workspace:"):
        if marker in lockfile_text:
            issues.append({"code": "lockfile_local_dependency", "message": f"pnpm-lock.yaml must not contain {marker} dependencies"})
    for platform_dep in ("@resvg/resvg-js-darwin-arm64", "@resvg/resvg-js-darwin-x64"):
        if platform_dep not in lockfile_text:
            issues.append({"code": "lockfile_missing_macos_resvg", "message": f"pnpm-lock.yaml must include optional native package {platform_dep}"})
    if "satori@0.26.0" not in lockfile_text:
        issues.append({"code": "lockfile_missing_satori", "message": "pnpm-lock.yaml must lock satori@0.26.0"})
    if "@resvg/resvg-js@2.6.2" not in lockfile_text:
        issues.append({"code": "lockfile_missing_resvg", "message": "pnpm-lock.yaml must lock @resvg/resvg-js@2.6.2"})
    return issues


def validate_embed_policy(embed_text: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    embed_patterns: set[str] = set()
    for line in embed_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("//go:embed"):
            continue
        embed_patterns.update(stripped.removeprefix("//go:embed").strip().split())
    for pattern in sorted(REQUIRED_EMBED_PATTERNS):
        if pattern not in embed_patterns:
            issues.append({"code": "go_embed_missing_pattern", "message": f"skills_embed.go must include {pattern}"})
    for pattern in sorted(FORBIDDEN_EMBED_PATTERNS):
        if pattern in embed_patterns:
            issues.append({"code": "go_embed_forbidden_broad_pattern", "message": f"skills_embed.go must not broadly embed {pattern}"})
    if any("node_modules" in pattern for pattern in embed_patterns):
        issues.append({"code": "go_embed_node_modules", "message": "skills_embed.go must not embed node_modules"})
    return issues


def scan_local_source_references(renderer_dir: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for rel in SCAN_PATHS:
        path = renderer_dir / rel
        if not path.exists():
            issues.append({"code": "package_file_missing", "message": f"required package file is missing: {rel}"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in LOCAL_SOURCE_MARKERS:
            if marker in text:
                issues.append({"code": "package_local_source_reference", "message": f"{rel} contains local source marker {marker!r}"})
    return issues


def scan_bundled_satori(renderer_dir: Path) -> list[dict[str, str]]:
    dist_path = renderer_dir / "dist" / "render.mjs"
    if not dist_path.exists():
        return []
    dist_text = dist_path.read_text(encoding="utf-8", errors="replace")
    issues: list[dict[str, str]] = []
    for marker in BUNDLED_SATORI_MARKERS:
        if marker in dist_text:
            issues.append({"code": "package_bundled_satori", "message": f"dist/render.mjs contains bundled Satori marker {marker!r}; keep satori external"})
    return issues


def run_node_runtime_check(renderer_dir: Path, entry: Path, *, timeout_seconds: int = 30) -> dict[str, Any]:
    command = ["node", entry.as_posix(), "--check-runtime"]
    result = subprocess.run(
        command,
        cwd=renderer_dir,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    payload: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout.strip().splitlines()[-1])
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    return {
        "command": " ".join(command),
        "cwd": renderer_dir.as_posix(),
        "entry": entry.as_posix(),
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "payload": payload,
        "passed": result.returncode == 0 and isinstance(payload, dict) and payload.get("ok") is True,
    }


def inspect_artboard_package(
    repo_root: Path = REPO_ROOT,
    renderer_dir: Path = ARTBOARD_RENDERER_DIR,
    *,
    run_runtime: bool = True,
    require_system: str | None = None,
    require_arch: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    renderer_dir = renderer_dir.resolve()
    package_path = renderer_dir / "package.json"
    lockfile_path = renderer_dir / "pnpm-lock.yaml"
    dist_path = renderer_dir / "dist" / "render.mjs"
    source_path = renderer_dir / "render.mjs"
    embed_path = repo_root / "skills_embed.go"
    gitignore_path = repo_root / ".gitignore"

    issues: list[dict[str, str]] = []
    blockers: list[dict[str, str]] = []
    host_system = platform.system()
    host_machine = platform.machine()
    host_arch = normalize_arch(host_machine)
    required_arch = normalize_arch(require_arch) if require_arch else None
    if require_system and host_system.lower() != require_system.lower():
        blockers.append({"code": "runtime_host_system_mismatch", "message": f"runtime check requires {require_system}, got {host_system or 'unknown'}"})
    if required_arch and host_arch != required_arch:
        blockers.append({"code": "runtime_host_arch_mismatch", "message": f"runtime check requires arch {required_arch}, got {host_arch}"})
    package_payload = read_json(package_path)
    lockfile_text = lockfile_path.read_text(encoding="utf-8") if lockfile_path.exists() else ""
    if not lockfile_path.exists():
        issues.append({"code": "lockfile_missing", "message": f"missing {repo_rel(lockfile_path, repo_root)}"})
    for path in (source_path, dist_path):
        if not path.exists():
            issues.append({"code": "renderer_entry_missing", "message": f"missing {repo_rel(path, repo_root)}"})
    issues.extend(validate_dependency_policy(package_payload, lockfile_text))
    issues.extend(scan_local_source_references(renderer_dir))
    issues.extend(scan_bundled_satori(renderer_dir))

    embed_text = embed_path.read_text(encoding="utf-8") if embed_path.exists() else ""
    if not embed_path.exists():
        issues.append({"code": "go_embed_missing", "message": "skills_embed.go is missing"})
    else:
        issues.extend(validate_embed_policy(embed_text))

    gitignore_text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    if "node_modules/" not in gitignore_text:
        issues.append({"code": "gitignore_node_modules_missing", "message": ".gitignore must ignore node_modules/"})
    if "!skills/lark-slides/scripts/artboard_renderer/dist/render.mjs" not in gitignore_text:
        issues.append({"code": "gitignore_dist_unignore_missing", "message": ".gitignore must keep artboard_renderer/dist/render.mjs visible"})

    runtime_checks: list[dict[str, Any]] = []
    if run_runtime:
        for entry in (source_path, dist_path):
            if entry.exists():
                try:
                    check = run_node_runtime_check(renderer_dir, entry)
                except (subprocess.SubprocessError, OSError) as err:
                    check = {
                        "command": f"node {entry.as_posix()} --check-runtime",
                        "entry": entry.as_posix(),
                        "exit_code": None,
                        "stdout": "",
                        "stderr": str(err),
                        "payload": None,
                        "passed": False,
                    }
                runtime_checks.append(check)
                if not check.get("passed"):
                    issues.append({"code": "runtime_check_failed", "message": f"{repo_rel(entry, repo_root)} --check-runtime failed"})

    status = "passed" if not issues and not blockers else ("blocked" if blockers and not issues else "failed")
    return {
        "version": CHECK_VERSION,
        "stage": CHECK_STAGE,
        "status": status,
        "action": "create_live" if status == "passed" else "repair_and_rerun",
        "checked_at": now_iso(),
        "summary": {
            "error_count": len(issues),
            "blocked_count": len(blockers),
            "warning_count": 0,
            "runtime_check_count": len(runtime_checks),
        },
        "host": {
            "system": host_system,
            "machine": host_machine,
            "normalized_arch": host_arch,
            "python": platform.python_version(),
        },
        "host_requirements": {
            "required_system": require_system,
            "required_arch": required_arch,
            "status": "passed" if not blockers else "blocked",
            "blockers": blockers,
        },
        "renderer": {
            "dir": repo_rel(renderer_dir, repo_root),
            "source_entry": repo_rel(source_path, repo_root),
            "dist_entry": repo_rel(dist_path, repo_root),
            "package_json": repo_rel(package_path, repo_root),
            "lockfile": repo_rel(lockfile_path, repo_root),
        },
        "dependency_policy": {
            "node": ">=18",
            "package_manager": "pnpm",
            "install_command": "pnpm --dir skills/lark-slides/scripts/artboard_renderer install --frozen-lockfile",
            "runtime_check_commands": [
                "node skills/lark-slides/scripts/artboard_renderer/render.mjs --check-runtime",
                "node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime",
            ],
            "dependencies": REQUIRED_DEPENDENCIES,
            "native_dependency": "@resvg/resvg-js",
            "satori_distribution": "external_runtime_dependency_not_bundled",
            "manual_satori_source_checkout_required": False,
            "node_modules_embedded_in_go_binary": False,
        },
        "distribution_decision": {
            "shape": "skill_subpackage_with_whitelisted_go_embed",
            "go_binary_embeds": [
                "agent-readable skill docs",
                "prompts",
                "flat Python scripts",
                "artboard_renderer source/dist/templates/themes/components/package lock",
            ],
            "go_binary_excludes": [
                "node_modules",
                "fixture outputs",
                "runtime project artifacts",
            ],
            "runtime_requires_disk_skill_resources": True,
            "runtime_requires_native_resvg_install": True,
        },
        "fallback_policy": {
            "missing_node_or_resvg": "fail_fast_before_live_create",
            "operator_action": "run pnpm --dir skills/lark-slides/scripts/artboard_renderer install --frozen-lockfile, then node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime",
            "no_network": "do not auto-fetch; use CI/preinstalled pnpm store or a packaged platform dependency layer",
        },
        "runtime_checks": runtime_checks,
        "blockers": blockers,
        "issues": issues,
    }


def write_check_outputs(output_dir: Path, payload: dict[str, Any]) -> None:
    write_json(output_dir / PACKAGE_CHECK, payload)
    write_json(output_dir / PACKAGE_RECEIPT, payload)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SVGlide artboard renderer packaging and runtime dependencies.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--renderer-dir", type=Path, default=ARTBOARD_RENDERER_DIR)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--skip-runtime", action="store_true", help="skip node --check-runtime probes; structural checks still run")
    parser.add_argument("--require-system", help="require a runtime host system, for example Darwin")
    parser.add_argument("--require-arch", choices=["x64", "arm64"], help="require a normalized runtime host architecture")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        payload = inspect_artboard_package(
            args.repo_root,
            args.renderer_dir,
            run_runtime=not args.skip_runtime,
            require_system=args.require_system,
            require_arch=args.require_arch,
        )
        if args.output_dir:
            write_check_outputs(args.output_dir, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    except PackageCheckError as err:
        payload = {
            "version": CHECK_VERSION,
            "stage": CHECK_STAGE,
            "status": "failed",
            "action": "repair_and_rerun",
            "checked_at": now_iso(),
            "summary": {"error_count": 1, "blocked_count": 0, "warning_count": 0, "runtime_check_count": 0},
            "issues": [{"code": "package_check_error", "message": str(err)}],
        }
        if args.output_dir:
            write_check_outputs(args.output_dir, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
