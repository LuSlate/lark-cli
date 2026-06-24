#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
"""
sheets_df.py — DataFrame ↔ Feishu Sheet typed I/O via lark-cli's JSON path.

This script is the documented bridge between pandas / pyarrow workflows and
lark-cli's +table-put / +table-get shortcuts. It deliberately uses ONLY the
typed JSON protocol (--sheets / +table-get default output) so the CLI binary
itself stays a thin JSON/REST client — Arrow / DataFrame editing belongs in
Python, not inside the CLI.

Two subcommands, both pandas-only round-trip:

  put: local DataFrame file (parquet / feather / csv / json-split)
       -> one sheet in a Feishu spreadsheet
  get: one sheet in a Feishu spreadsheet
       -> local DataFrame file (parquet / feather / csv / json-split)

Examples:

  # write a parquet table into Sheet1 of a workbook
  python3 sheets_df.py put --url <url> --in data.parquet --sheet-name Sheet1

  # read the same sheet back into a parquet file
  python3 sheets_df.py get --url <url> --sheet-name Sheet1 --out out.parquet

  # CSV in / CSV out for non-typed payloads (lark-cli auto-infers dtypes)
  python3 sheets_df.py put --url <url> --in raw.csv --sheet-name Sheet1
  python3 sheets_df.py get --url <url> --sheet-name Sheet1 --out out.csv

The script shells out to `lark-cli sheets +table-put / +table-get`, so the
caller must already be authenticated (`lark-cli auth login`) and have
network access to Feishu. lark-cli itself stays unchanged — this script
just feeds it the typed-JSON wire shape both shortcuts already accept.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _read_local_df(path: Path):
    """Load a local table file into a pandas DataFrame, picking the reader
    by suffix. pandas is imported lazily so `--help` works without it."""
    import pandas as pd  # noqa: PLC0415 — lazy so --help has no hard dep

    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in (".feather", ".arrow"):
        return pd.read_feather(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".json":
        # Accept pandas's `orient="split"` JSON, the same shape lark-cli emits.
        return pd.read_json(path, orient="split")
    raise SystemExit(f"unsupported input suffix {suffix!r}; want .parquet/.feather/.arrow/.csv/.json")


def _write_local_df(df, path: Path) -> None:
    """Dump a pandas DataFrame to a local table file, picking the writer by
    suffix. Same suffix-set as _read_local_df."""
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".parquet":
        df.to_parquet(path, index=False)
    elif suffix in (".feather", ".arrow"):
        df.to_feather(path)
    elif suffix == ".csv":
        df.to_csv(path, index=False)
    elif suffix == ".json":
        # Mirror lark-cli's +table-get split shape so the file round-trips.
        df.to_json(path, orient="split", date_format="iso", force_ascii=False)
    else:
        raise SystemExit(f"unsupported output suffix {suffix!r}; want .parquet/.feather/.arrow/.csv/.json")


def _spreadsheet_locator_args(args) -> list[str]:
    """Build the (--url XOR --spreadsheet-token) pair for lark-cli."""
    if args.url:
        return ["--url", args.url]
    if args.spreadsheet_token:
        return ["--spreadsheet-token", args.spreadsheet_token]
    raise SystemExit("specify exactly one of --url / --spreadsheet-token")


def _sheet_selector_args(args) -> list[str]:
    if args.sheet_id:
        return ["--sheet-id", args.sheet_id]
    if args.sheet_name:
        return ["--sheet-name", args.sheet_name]
    return []


def cmd_put(args) -> None:
    """Write one DataFrame as one sheet via +table-put --sheets."""
    df = _read_local_df(Path(args.in_path))
    sheet_name = args.sheet_name or "Sheet1"

    # The split shape lines up with lark-cli's typed protocol verbatim:
    # columns + data + (optional) dtypes/formats. date_format="iso" keeps
    # datetime columns as `yyyy-mm-dd` strings, which +table-put recognizes
    # via the matching dtype string (`datetime64[ns]`).
    split = json.loads(df.to_json(orient="split", date_format="iso"))
    sheet = {
        "name": sheet_name,
        "columns": split["columns"],
        "data": split["data"],
        "dtypes": df.dtypes.astype(str).to_dict(),
    }
    payload = {"sheets": [sheet]}

    lark_cmd = [
        args.lark_cli, "sheets", "+table-put",
        *_spreadsheet_locator_args(args),
        "--sheets", "-",
    ]
    if args.as_identity:
        lark_cmd.extend(["--as", args.as_identity])
    if args.dry_run:
        lark_cmd.append("--dry-run")

    proc = subprocess.run(lark_cmd, input=json.dumps(payload), text=True, capture_output=True, check=False)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    sys.exit(proc.returncode)


def cmd_get(args) -> None:
    """Read one sheet via +table-get and write it to a local file."""
    if not (args.sheet_id or args.sheet_name):
        raise SystemExit("specify --sheet-id or --sheet-name (whole-workbook reads aren't single-DataFrame)")

    lark_cmd = [
        args.lark_cli, "sheets", "+table-get",
        *_spreadsheet_locator_args(args),
        *_sheet_selector_args(args),
    ]
    if args.range:
        lark_cmd.extend(["--range", args.range])
    if args.as_identity:
        lark_cmd.extend(["--as", args.as_identity])

    proc = subprocess.run(lark_cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        sys.exit(proc.returncode)

    envelope = json.loads(proc.stdout)
    sheets = envelope.get("data", {}).get("sheets") or []
    if not sheets:
        raise SystemExit(f"+table-get returned no sheets; stdout:\n{proc.stdout}")
    sheet = sheets[0]

    import pandas as pd  # noqa: PLC0415

    df = pd.DataFrame(sheet["data"], columns=sheet["columns"])
    dtypes = sheet.get("dtypes") or {}
    if dtypes:
        # Best-effort dtype restore: pandas needs string columns BEFORE
        # casting to datetime64[ns] (the JSON is already ISO strings).
        for col, dt in dtypes.items():
            if col not in df.columns:
                continue
            if dt.startswith("datetime"):
                df[col] = pd.to_datetime(df[col], errors="coerce")
            else:
                try:
                    df[col] = df[col].astype(dt)
                except (TypeError, ValueError):
                    pass  # leave the column as-is on mismatch
    _write_local_df(df, Path(args.out_path))
    sys.stderr.write(f"wrote {len(df)} rows × {len(df.columns)} cols to {args.out_path}\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sheets_df.py",
        description="Round-trip pandas DataFrames through lark-cli's typed JSON sheet I/O.",
    )
    p.add_argument("--lark-cli", default="lark-cli", help="lark-cli binary (default: from PATH)")
    sub = p.add_subparsers(dest="cmd", required=True)

    common_locator = argparse.ArgumentParser(add_help=False)
    common_locator.add_argument("--url", help="spreadsheet URL (XOR with --spreadsheet-token)")
    common_locator.add_argument("--spreadsheet-token", help="spreadsheet token (XOR with --url)")
    common_locator.add_argument("--as", dest="as_identity", choices=["user", "bot"],
                                help="identity passthrough to lark-cli")

    p_put = sub.add_parser("put", parents=[common_locator],
                           help="Write a local DataFrame file into a Feishu sheet.")
    p_put.add_argument("--in", dest="in_path", required=True,
                       help="local DataFrame file (.parquet/.feather/.arrow/.csv/.json)")
    p_put.add_argument("--sheet-name", default="Sheet1",
                       help="target sheet name (default: Sheet1; the sheet is created if absent)")
    p_put.add_argument("--dry-run", action="store_true", help="forward --dry-run to lark-cli")
    p_put.set_defaults(func=cmd_put)

    p_get = sub.add_parser("get", parents=[common_locator],
                           help="Read a Feishu sheet into a local DataFrame file.")
    p_get.add_argument("--out", dest="out_path", required=True,
                       help="local output file (.parquet/.feather/.arrow/.csv/.json)")
    p_get.add_argument("--sheet-name", help="source sheet name (XOR with --sheet-id)")
    p_get.add_argument("--sheet-id", help="source sheet id (XOR with --sheet-name)")
    p_get.add_argument("--range", help="optional A1 range like 'A1:E100'; default reads the full used range")
    p_get.set_defaults(func=cmd_get)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
