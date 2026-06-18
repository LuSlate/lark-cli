// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"context"
	"strings"

	"github.com/larksuite/cli/shortcuts/common"
)

// ─── lark_sheet_history ───────────────────────────────────────────────
//
// Wraps:
//   - list_history_versions (read)  — powers +history-list
//   - revert_to_revision    (write) — powers +history-revert
//   - get_revert_status     (read)  — powers +history-revert-status
//
// The version-history "方案 B": list the spreadsheet's saved revisions, submit
// a whole-document revert to one of them, then poll the async revert task for
// completion. The facade gateway owns the work; the CLI only forwards the
// target revision (and later the task id) and the server does the rest.
//
// ⚠️ Full-table overwrite: +history-revert rolls the WHOLE spreadsheet back to
// the target revision, discarding every change made afterwards — including
// other collaborators' (and the web UI's) edits. Use it only on agent scratch
// spreadsheets, or when a whole-document rollback is acceptable.

// HistoryList wraps list_history_versions: page through the spreadsheet's saved
// revisions so a later +history-revert can target one by revision_id.
var HistoryList = common.Shortcut{
	Service:     "sheets",
	Command:     "+history-list",
	Description: "List the spreadsheet's saved history versions (paginated); use a returned revision_id with +history-revert.",
	Risk:        "read",
	Scopes:      []string{"sheets:spreadsheet:read"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+history-list"),
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		_, err := resolveSpreadsheetToken(runtime)
		return err
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		return invokeToolDryRun(token, ToolKindRead, "list_history_versions", historyListInput(runtime))
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		out, err := callTool(ctx, runtime, token, ToolKindRead, "list_history_versions", historyListInput(runtime))
		if err != nil {
			return err
		}
		runtime.Out(out, nil)
		return nil
	},
	Tips: []string{
		"Omit --cursor for the first page; pass the previous response's next_cursor to fetch the next page.",
		"Pick a revision_id from a listing entry and pass it (plus that entry's edit_time to --edit-time) to +history-revert to roll the whole spreadsheet back.",
	},
}

// HistoryRevert wraps revert_to_revision: roll the whole spreadsheet back to a
// past revision. Returns an async task id to poll via +history-revert-status.
var HistoryRevert = common.Shortcut{
	Service:     "sheets",
	Command:     "+history-revert",
	Description: "Roll the whole spreadsheet back to a past revision (full-document restore; discards all later edits).",
	Risk:        "write",
	Scopes:      []string{"sheets:spreadsheet:write_only"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+history-revert"),
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if _, err := resolveSpreadsheetToken(runtime); err != nil {
			return err
		}
		_, err := historyRevertInput(runtime)
		return err
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		input, _ := historyRevertInput(runtime)
		return invokeToolDryRun(token, ToolKindWrite, "revert_to_revision", input)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		input, err := historyRevertInput(runtime)
		if err != nil {
			return err
		}
		out, err := callTool(ctx, runtime, token, ToolKindWrite, "revert_to_revision", input)
		if err != nil {
			return err
		}
		runtime.Out(out, nil)
		return nil
	},
	Tips: []string{
		"+history-revert is a FULL-DOCUMENT rollback — it discards every edit made after the target version, including other collaborators'.",
		"--revision-id takes a revision_id (minor id) from +history-list; pass the same entry's edit_time to --edit-time to locate the version faster. Poll the returned task id with +history-revert-status.",
	},
}

// HistoryRevertStatus wraps get_revert_status: poll an async revert task
// started by +history-revert for completion.
var HistoryRevertStatus = common.Shortcut{
	Service:     "sheets",
	Command:     "+history-revert-status",
	Description: "Poll the status of an async revert task started by +history-revert.",
	Risk:        "read",
	Scopes:      []string{"sheets:spreadsheet:read"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+history-revert-status"),
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if _, err := resolveSpreadsheetToken(runtime); err != nil {
			return err
		}
		_, err := historyRevertStatusInput(runtime)
		return err
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		input, _ := historyRevertStatusInput(runtime)
		return invokeToolDryRun(token, ToolKindRead, "get_revert_status", input)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		input, err := historyRevertStatusInput(runtime)
		if err != nil {
			return err
		}
		out, err := callTool(ctx, runtime, token, ToolKindRead, "get_revert_status", input)
		if err != nil {
			return err
		}
		runtime.Out(out, nil)
		return nil
	},
	Tips: []string{
		"--task-id is the task id returned by +history-revert; re-run this until the task reports completion.",
	},
}

// historyListInput builds the list_history_versions tool body. Network-free;
// shared by DryRun and Execute. Both flags are optional: cursor is forwarded
// only when set, count only when a positive value is given.
func historyListInput(runtime flagView) map[string]interface{} {
	input := map[string]interface{}{}
	if cursor := strings.TrimSpace(runtime.Str("cursor")); cursor != "" {
		input["cursor"] = cursor
	}
	if count := runtime.Int("count"); count > 0 {
		input["count"] = count
	}
	return input
}

// historyRevertInput builds the revert_to_revision tool body. Network-free;
// shared by Validate, DryRun, and Execute. revision_id 是 +history-list 返回的
// revision_id（minor id）；edit_time 可选，传同一条 entry 的 edit_time 让服务端更快定位该版本。
func historyRevertInput(runtime flagView) (map[string]interface{}, error) {
	rev := strings.TrimSpace(runtime.Str("revision-id"))
	if rev == "" {
		return nil, common.FlagErrorf("--revision-id is required (a revision_id from +history-list)")
	}
	input := map[string]interface{}{
		"revision_id": rev,
	}
	if et := strings.TrimSpace(runtime.Str("edit-time")); et != "" {
		input["edit_time"] = et
	}
	return input, nil
}

// historyRevertStatusInput builds the get_revert_status tool body.
// Network-free; shared by Validate, DryRun, and Execute.
func historyRevertStatusInput(runtime flagView) (map[string]interface{}, error) {
	tid := strings.TrimSpace(runtime.Str("task-id"))
	if tid == "" {
		return nil, common.FlagErrorf("--task-id is required")
	}
	return map[string]interface{}{
		"task_id": tid,
	}, nil
}
