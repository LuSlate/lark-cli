// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"context"

	"github.com/larksuite/cli/shortcuts/common"
)

// ─── lark_sheet_recover ───────────────────────────────────────────────
//
// Wraps:
//   - recover_to_revision (write) — powers +recover
//
// Rolls the WHOLE spreadsheet back to a past revision (the undo design doc's
// "方案 B"). Unlike +undo — which is precise, per-edit, and scoped to this CLI
// link — +recover is a full-document version restore. The facade gateway
// already owns this capability (the same revert-by-revision path the web
// "history" panel drives): it submits a single RECOVER changeset that reverts
// every sheet to the target revision and produces a new revision. The CLI only
// passes the target revision; all the work stays server-side.
//
// ⚠️ Full-table overwrite: +recover discards EVERY change made after
// --to-revision, including other collaborators' (and the web UI's) edits. Use
// it only on agent scratch spreadsheets, or when a whole-document rollback is
// acceptable. For precise, this-link-only undo, use +undo instead.
var Recover = common.Shortcut{
	Service:     "sheets",
	Command:     "+recover",
	Description: "Roll the whole spreadsheet back to a past revision (full-document restore; discards all later edits).",
	Risk:        "write",
	Scopes:      []string{"sheets:spreadsheet:write_only"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+recover"),
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		_, err = recoverInput(runtime, token)
		return err
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		input, _ := recoverInput(runtime, token)
		return invokeToolDryRun(token, ToolKindWrite, "recover_to_revision", input)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		input, err := recoverInput(runtime, token)
		if err != nil {
			return err
		}
		out, err := callTool(ctx, runtime, token, ToolKindWrite, "recover_to_revision", input)
		if err != nil {
			return err
		}
		runtime.Out(out, nil)
		return nil
	},
	Tips: []string{
		"+recover is a FULL-DOCUMENT rollback — it discards every edit made after --to-revision, including other collaborators'. For precise, this-link-only undo, use +undo instead.",
		"--to-revision takes a revision number returned by a prior write (the `revision` field in the response).",
		"Use --dry-run to preview the recover request before running it.",
	},
}

// recoverInput builds the recover_to_revision tool body. Network-free; shared
// by Validate, DryRun, and Execute.
func recoverInput(runtime flagView, token string) (map[string]interface{}, error) {
	rev := runtime.Int("to-revision")
	if rev < 1 {
		return nil, common.FlagErrorf("--to-revision must be a positive revision number")
	}
	return map[string]interface{}{
		"excel_id":    token,
		"to_revision": rev,
	}, nil
}
