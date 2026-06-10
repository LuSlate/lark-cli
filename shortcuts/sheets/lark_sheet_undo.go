// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"context"

	"github.com/larksuite/cli/shortcuts/common"
)

// ─── lark_sheet_undo ──────────────────────────────────────────────────
//
// Wraps:
//   - undo_last (write) — powers +undo
//
// Reverses the most recent edits this CLI link made to a spreadsheet, addressed
// by document revision. Every write response carries `data.revision`; that
// number is the undo anchor. The backend records an inverse changeset for every
// write and indexes it by the revision it produced (see the undo design doc,
// "方案 A · rev 寻址"); +undo asks the backend executor to locate that inverse
// data through the revision pointer, verify nobody else changed the document
// since (tip / continuity / object-version / identity checks), re-apply it in
// reverse order on the node Workbook, and push the result upstream as a
// collaboration change. The CLI only triggers the tool — the read-back endpoint
// is space-internal and not reachable through the /open-apis gateway, so all
// the heavy lifting stays server-side.
//
// +undo carries no sheet selector: undo is scoped to the spreadsheet + this
// link's edit history, not a single sub-sheet. Selection:
//   - (no flags)  : undo the latest edit, if it was made by this caller
//   - --rev N     : undo anchored at revision N (from a prior write response);
//                   rejected when the document has moved past N
//   - --steps N   : undo the last N edits in one atomic call (default 1)

// Undo wraps undo_last: reverse the most recent edits made through this CLI
// link, anchored by the revision a prior write returned (--rev), defaulting
// to the latest edit.
var Undo = common.Shortcut{
	Service:     "sheets",
	Command:     "+undo",
	Description: "Undo the most recent edits this CLI link made to a spreadsheet (anchored by a write's returned revision).",
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
		"Every write response carries data.revision — remember it; +undo --rev <that> undoes exactly that edit, and +recover --to-revision <that-1> is the full-rollback fallback.",
		"Without --rev, +undo targets the document's latest edit — it succeeds only when that edit was made through this CLI link by you.",
		"Repeated +undo steps back one edit at a time; --steps N undoes the last N edits in one atomic call. Already-undone edits are skipped automatically.",
		"If anyone else edited the document after (or between) the edits you want to undo, +undo refuses entirely and suggests +recover — it never partially undoes or overwrites others' changes.",
		"A success response with undone:0 plus warning_message means nothing was actually undone — the targeted revision wasn't produced by this caller, or was already undone.",
		"Use --dry-run to preview the request before running it.",
	},
}

// undoInput builds the undo_last tool body. --rev anchors the undo at the
// revision a prior write returned (omitted = latest); --steps selects how many
// edits to reverse in one atomic call. Network-free; shared by Validate,
// DryRun, and Execute.
func undoInput(runtime flagView, token string) (map[string]interface{}, error) {
	input := map[string]interface{}{"excel_id": token}

	if runtime.Changed("rev") {
		rev := runtime.Int("rev")
		if rev < 1 {
			return nil, common.FlagErrorf("--rev must be a positive revision number (from a prior write's data.revision)")
		}
		input["rev"] = rev
	}

	steps := runtime.Int("steps")
	if steps < 1 {
		return nil, common.FlagErrorf("--steps must be >= 1")
	}
	input["steps"] = steps
	return input, nil
}
