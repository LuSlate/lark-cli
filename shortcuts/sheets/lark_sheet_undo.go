// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"context"
	"strings"

	"github.com/larksuite/cli/internal/validate"
	"github.com/larksuite/cli/shortcuts/common"
)

// ─── lark_sheet_undo ──────────────────────────────────────────────────
//
// Wraps:
//   - undo_last (write) — powers +undo
//
// Reverses the most recent edits this CLI link made to a spreadsheet. The
// backend already records an inverse changeset for every write (see the
// undo design doc, "方案 A"); +undo asks the backend executor to read that
// changeset back and re-apply it in reverse order on the node Workbook, then
// push the result upstream as a collaboration change. The CLI only triggers
// the tool — the read-back endpoint is space-internal and not reachable
// through the /open-apis gateway, so all the heavy lifting stays server-side.
//
// +undo carries no sheet selector: undo is scoped to the spreadsheet + this
// link's edit history, not a single sub-sheet. The two selection modes are
// XOR:
//   - --steps N : undo the last N edits (default 1)
//   - --op <id> : undo one specific operation_id surfaced by a prior write's
//                 undo handle

// Undo wraps undo_last: reverse the most recent edits made through this CLI
// link, either the last N steps (--steps) or one specific operation (--op).
var Undo = common.Shortcut{
	Service:     "sheets",
	Command:     "+undo",
	Description: "Undo the most recent edits this CLI link made to a spreadsheet (last N steps, or a specific operation).",
	Risk:        "write",
	Scopes:      []string{"sheets:spreadsheet:write_only"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+undo"),
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		_, err = undoInput(runtime, token)
		return err
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		input, _ := undoInput(runtime, token)
		return invokeToolDryRun(token, ToolKindWrite, "undo_last", input)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		input, err := undoInput(runtime, token)
		if err != nil {
			return err
		}
		out, err := callTool(ctx, runtime, token, ToolKindWrite, "undo_last", input)
		if err != nil {
			return err
		}
		runtime.Out(out, nil)
		return nil
	},
	Tips: []string{
		"Undo is scoped to edits made through this CLI link — it never touches changes other collaborators (or the web UI) made to the same range.",
		"Use --dry-run to preview which steps would be undone before running it.",
	},
}

// undoInput builds the undo_last tool body and enforces the --steps / --op
// XOR. --steps carries a default of 1, so the mutual-exclusion check keys off
// Changed("steps") (whether the user actually passed it) rather than its
// value. Network-free; shared by Validate, DryRun, and Execute.
func undoInput(runtime flagView, token string) (map[string]interface{}, error) {
	op := strings.TrimSpace(runtime.Str("op"))
	stepsSet := runtime.Changed("steps")

	if op != "" && stepsSet {
		return nil, common.FlagErrorf("--steps and --op are mutually exclusive")
	}

	input := map[string]interface{}{"excel_id": token}

	if op != "" {
		if err := validate.RejectControlChars(op, "op"); err != nil {
			return nil, common.FlagErrorf("%v", err)
		}
		input["operation_id"] = op
		return input, nil
	}

	steps := runtime.Int("steps")
	if steps < 1 {
		return nil, common.FlagErrorf("--steps must be >= 1")
	}
	input["steps"] = steps
	return input, nil
}
