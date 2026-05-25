// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"context"
	"fmt"
	"strings"

	"github.com/larksuite/cli/internal/validate"
	"github.com/larksuite/cli/shortcuts/common"
)

// ─── lark_sheet_sheet_structure ───────────────────────────────────────
//
// Wraps get_sheet_structure (read) and modify_sheet_structure (write,
// operation-enum dispatch). CLI's --start/--end are 0-based with exclusive
// end; the tool wants 1-based inclusive row numbers ("3:7") or column
// letters ("C:F"). The conversion lives in dimRange / dimPosition below.
//
// +rows-resize / +cols-resize live in lark_sheet_range_operations (different
// tool); they are only grouped under "工作表" for discoverability.

// SheetInfo wraps get_sheet_structure: row heights, column widths, hidden
// rows/cols, merged cells, row/column groups, and freeze counts for one
// sub-sheet (optionally limited to a range).
var SheetInfo = common.Shortcut{
	Service:     "sheets",
	Command:     "+sheet-info",
	Description: "Get a sub-sheet's layout metadata: row heights, column widths, hidden rows/cols, merges, groups, freeze.",
	Risk:        "read",
	Scopes:      []string{"sheets:spreadsheet:read"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+sheet-info"),
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if _, err := resolveSpreadsheetToken(runtime); err != nil {
			return err
		}
		_, _, err := resolveSheetSelector(runtime)
		return err
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		sheetID, sheetName, _ := resolveSheetSelector(runtime)
		return invokeToolDryRun(token, ToolKindRead, "get_sheet_structure", sheetInfoInput(runtime, token, sheetID, sheetName))
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		sheetID, sheetName, err := resolveSheetSelector(runtime)
		if err != nil {
			return err
		}
		out, err := callTool(ctx, runtime, token, ToolKindRead, "get_sheet_structure", sheetInfoInput(runtime, token, sheetID, sheetName))
		if err != nil {
			return err
		}
		runtime.Out(out, nil)
		return nil
	},
	Tips: []string{
		"Frozen rows / columns are top-level fields and are returned regardless of --include.",
	},
}

func sheetInfoInput(runtime *common.RuntimeContext, token, sheetID, sheetName string) map[string]interface{} {
	input := map[string]interface{}{"excel_id": token}
	sheetSelectorForToolInput(input, sheetID, sheetName)
	if r := strings.TrimSpace(runtime.Str("range")); r != "" {
		input["range"] = r
	}
	if include := runtime.StrSlice("include"); len(include) > 0 {
		if t := infoTypeFromInclude(include); t != "" {
			input["info_type"] = t
		}
	}
	return input
}

// infoTypeFromInclude maps the fine-grained --include vocabulary to the
// tool's coarse info_type enum. When --include spans multiple categories
// (or asks for "frozen", which is always returned), we fall back to "all".
func infoTypeFromInclude(include []string) string {
	groups := map[string]string{
		"row_heights": "row_heights_column_widths",
		"col_widths":  "row_heights_column_widths",
		"hidden_rows": "hidden_infos",
		"hidden_cols": "hidden_infos",
		"groups":      "group_infos",
		"merges":      "merged_cells_infos",
		"frozen":      "", // any info_type returns frozen; falling back to all is fine
	}
	seen := map[string]struct{}{}
	for _, v := range include {
		g, ok := groups[v]
		if !ok || g == "" {
			return "all"
		}
		seen[g] = struct{}{}
	}
	if len(seen) != 1 {
		return "all"
	}
	for g := range seen {
		return g
	}
	return "all"
}

// ─── +dim-* (modify_sheet_structure) ──────────────────────────────────

// DimInsert inserts blank rows / columns and optionally inherits style from
// the adjacent dimension.
var DimInsert = common.Shortcut{
	Service:     "sheets",
	Command:     "+dim-insert",
	Description: "Insert blank rows or columns at a given range.",
	Risk:        "write",
	Scopes:      []string{"sheets:spreadsheet:write_only"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+dim-insert"),
	Validate:    validateViaInput(dimInsertInput),
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		sheetID, sheetName, _ := resolveSheetSelector(runtime)
		input, _ := dimInsertInput(runtime, token, sheetID, sheetName)
		return invokeToolDryRun(token, ToolKindWrite, "modify_sheet_structure", input)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		sheetID, sheetName, err := resolveSheetSelector(runtime)
		if err != nil {
			return err
		}
		input, err := dimInsertInput(runtime, token, sheetID, sheetName)
		if err != nil {
			return err
		}
		out, err := callTool(ctx, runtime, token, ToolKindWrite, "modify_sheet_structure", input)
		if err != nil {
			return err
		}
		runtime.Out(out, nil)
		return nil
	},
}

func dimInsertInput(runtime flagView, token, sheetID, sheetName string) (map[string]interface{}, error) {
	if err := requireSheetSelector(sheetID, sheetName); err != nil {
		return nil, err
	}
	if err := requireDimRange(runtime); err != nil {
		return nil, err
	}
	dim := runtime.Str("dimension")
	start := runtime.Int("start")
	end := runtime.Int("end")
	input := map[string]interface{}{
		"excel_id":  token,
		"operation": "insert",
		"position":  dimPosition(dim, start),
		"count":     end - start,
	}
	sheetSelectorForToolInput(input, sheetID, sheetName)
	switch runtime.Str("inherit-style") {
	case "before":
		input["side"] = "before"
	case "after":
		input["side"] = "after"
	}
	return input, nil
}

// DimDelete deletes rows / columns — irreversible, high-risk-write.
var DimDelete = common.Shortcut{
	Service:     "sheets",
	Command:     "+dim-delete",
	Description: "Delete rows or columns (irreversible).",
	Risk:        "high-risk-write",
	Scopes:      []string{"sheets:spreadsheet:write_only"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+dim-delete"),
	Validate:    validateDimRangeOp("delete"),
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		sheetID, sheetName, _ := resolveSheetSelector(runtime)
		input, _ := dimRangeOpInput(runtime, token, sheetID, sheetName, "delete")
		return invokeToolDryRun(token, ToolKindWrite, "modify_sheet_structure", input)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		sheetID, sheetName, err := resolveSheetSelector(runtime)
		if err != nil {
			return err
		}
		input, err := dimRangeOpInput(runtime, token, sheetID, sheetName, "delete")
		if err != nil {
			return err
		}
		out, err := callTool(ctx, runtime, token, ToolKindWrite, "modify_sheet_structure", input)
		if err != nil {
			return err
		}
		runtime.Out(out, nil)
		return nil
	},
	Tips: []string{
		"Row/column deletion is irreversible. Always preview with --dry-run first.",
	},
}

// validateDimRangeOp returns a Validate closure that delegates to
// dimRangeOpInput for shortcuts (delete/hide/unhide) whose builder takes an
// extra `op` argument. Token check happens here; the rest is the builder.
func validateDimRangeOp(op string) func(ctx context.Context, runtime *common.RuntimeContext) error {
	return func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		sheetID := strings.TrimSpace(runtime.Str("sheet-id"))
		sheetName := strings.TrimSpace(runtime.Str("sheet-name"))
		_, err = dimRangeOpInput(runtime, token, sheetID, sheetName, op)
		return err
	}
}

// validateDimGroupOp is the group/ungroup counterpart of validateDimRangeOp.
func validateDimGroupOp(op string) func(ctx context.Context, runtime *common.RuntimeContext) error {
	return func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		sheetID := strings.TrimSpace(runtime.Str("sheet-id"))
		sheetName := strings.TrimSpace(runtime.Str("sheet-name"))
		_, err = dimGroupInput(runtime, token, sheetID, sheetName, op)
		return err
	}
}

// DimHide / DimUnhide toggle visibility on a row/column range.
var DimHide = newDimRangeOpShortcut(
	"+dim-hide", "Hide rows or columns within a range.", "hide", "write",
)
var DimUnhide = newDimRangeOpShortcut(
	"+dim-unhide", "Unhide rows or columns within a range.", "unhide", "write",
)

// DimGroup / DimUngroup manage row/column outline groups.
var DimGroup = newDimGroupShortcut(
	"+dim-group", "Group rows or columns into an outline (collapsible).", "group",
)
var DimUngroup = newDimGroupShortcut(
	"+dim-ungroup", "Remove a row/column outline group.", "ungroup",
)

// DimFreeze freezes the first N rows or columns; --count 0 unfreezes that
// dimension.
var DimFreeze = common.Shortcut{
	Service:     "sheets",
	Command:     "+dim-freeze",
	Description: "Freeze the first N rows or columns; --count 0 unfreezes the chosen dimension.",
	Risk:        "write",
	Scopes:      []string{"sheets:spreadsheet:write_only"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+dim-freeze"),
	Validate:    validateViaInput(dimFreezeInput),
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		sheetID, sheetName, _ := resolveSheetSelector(runtime)
		input, _ := dimFreezeInput(runtime, token, sheetID, sheetName)
		return invokeToolDryRun(token, ToolKindWrite, "modify_sheet_structure", input)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		sheetID, sheetName, err := resolveSheetSelector(runtime)
		if err != nil {
			return err
		}
		input, err := dimFreezeInput(runtime, token, sheetID, sheetName)
		if err != nil {
			return err
		}
		out, err := callTool(ctx, runtime, token, ToolKindWrite, "modify_sheet_structure", input)
		if err != nil {
			return err
		}
		runtime.Out(out, nil)
		return nil
	},
}

func dimFreezeInput(runtime flagView, token, sheetID, sheetName string) (map[string]interface{}, error) {
	if err := requireSheetSelector(sheetID, sheetName); err != nil {
		return nil, err
	}
	if !runtime.Changed("dimension") {
		return nil, common.FlagErrorf("--dimension is required")
	}
	if !runtime.Changed("count") {
		return nil, common.FlagErrorf("--count is required (0 unfreezes)")
	}
	if runtime.Int("count") < 0 {
		return nil, common.FlagErrorf("--count must be >= 0")
	}
	dim := runtime.Str("dimension")
	count := runtime.Int("count")
	op := "freeze"
	if count == 0 {
		op = "unfreeze"
	}
	input := map[string]interface{}{"excel_id": token, "operation": op}
	sheetSelectorForToolInput(input, sheetID, sheetName)
	if op == "freeze" {
		if dim == "row" {
			input["freeze_rows"] = count
		} else {
			input["freeze_columns"] = count
		}
	}
	return input, nil
}

// requireDimRange validates the dimension/start/end triple shared by
// insert/delete/hide/unhide/group/ungroup. Pure flag-level checks — the sheet
// selector and token live in their own helpers.
func requireDimRange(runtime flagView) error {
	if !runtime.Changed("dimension") {
		return common.FlagErrorf("--dimension is required")
	}
	if !runtime.Changed("start") || !runtime.Changed("end") {
		return common.FlagErrorf("--start and --end are required")
	}
	start := runtime.Int("start")
	end := runtime.Int("end")
	if start < 0 {
		return common.FlagErrorf("--start must be >= 0")
	}
	if end <= start {
		return common.FlagErrorf("--end (%d) must be greater than --start (%d)", end, start)
	}
	return nil
}

// dimRangeOpInput builds the tool input for delete/hide/unhide which all
// take a `range` field. dimRange handles 0-based exclusive → 1-based inclusive.
func dimRangeOpInput(runtime flagView, token, sheetID, sheetName, op string) (map[string]interface{}, error) {
	if err := requireSheetSelector(sheetID, sheetName); err != nil {
		return nil, err
	}
	if err := requireDimRange(runtime); err != nil {
		return nil, err
	}
	input := map[string]interface{}{
		"excel_id":  token,
		"operation": op,
		"range":     dimRange(runtime.Str("dimension"), runtime.Int("start"), runtime.Int("end")),
	}
	sheetSelectorForToolInput(input, sheetID, sheetName)
	return input, nil
}

// newDimRangeOpShortcut builds the shared shape for hide / unhide.
func newDimRangeOpShortcut(command, desc, op, risk string) common.Shortcut {
	return common.Shortcut{
		Service:     "sheets",
		Command:     command,
		Description: desc,
		Risk:        risk,
		Scopes:      []string{"sheets:spreadsheet:write_only"},
		AuthTypes:   []string{"user", "bot"},
		HasFormat:   true,
		Flags:       flagsFor(command),
		Validate:    validateDimRangeOp(op),
		DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
			token, _ := resolveSpreadsheetToken(runtime)
			sheetID, sheetName, _ := resolveSheetSelector(runtime)
			input, _ := dimRangeOpInput(runtime, token, sheetID, sheetName, op)
			return invokeToolDryRun(token, ToolKindWrite, "modify_sheet_structure", input)
		},
		Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
			token, err := resolveSpreadsheetToken(runtime)
			if err != nil {
				return err
			}
			sheetID, sheetName, err := resolveSheetSelector(runtime)
			if err != nil {
				return err
			}
			input, err := dimRangeOpInput(runtime, token, sheetID, sheetName, op)
			if err != nil {
				return err
			}
			out, err := callTool(ctx, runtime, token, ToolKindWrite, "modify_sheet_structure", input)
			if err != nil {
				return err
			}
			runtime.Out(out, nil)
			return nil
		},
	}
}

// newDimGroupShortcut builds the shared shape for group / ungroup. It adds
// --depth (currently unused server-side — accepted for forward-compat per
// the canonical spec) and --group-state (group only, defaults to expand).
func newDimGroupShortcut(command, desc, op string) common.Shortcut {
	flags := flagsFor(command)
	return common.Shortcut{
		Service:     "sheets",
		Command:     command,
		Description: desc,
		Risk:        "write",
		Scopes:      []string{"sheets:spreadsheet:write_only"},
		AuthTypes:   []string{"user", "bot"},
		HasFormat:   true,
		Flags:       flags,
		Validate:    validateDimGroupOp(op),
		DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
			token, _ := resolveSpreadsheetToken(runtime)
			sheetID, sheetName, _ := resolveSheetSelector(runtime)
			input, _ := dimGroupInput(runtime, token, sheetID, sheetName, op)
			return invokeToolDryRun(token, ToolKindWrite, "modify_sheet_structure", input)
		},
		Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
			token, err := resolveSpreadsheetToken(runtime)
			if err != nil {
				return err
			}
			sheetID, sheetName, err := resolveSheetSelector(runtime)
			if err != nil {
				return err
			}
			input, err := dimGroupInput(runtime, token, sheetID, sheetName, op)
			if err != nil {
				return err
			}
			out, err := callTool(ctx, runtime, token, ToolKindWrite, "modify_sheet_structure", input)
			if err != nil {
				return err
			}
			runtime.Out(out, nil)
			return nil
		},
	}
}

func dimGroupInput(runtime flagView, token, sheetID, sheetName, op string) (map[string]interface{}, error) {
	input, err := dimRangeOpInput(runtime, token, sheetID, sheetName, op)
	if err != nil {
		return nil, err
	}
	if op == "group" {
		if gs := runtime.Str("group-state"); gs != "" {
			input["group_state"] = gs
		}
	}
	return input, nil
}

// ─── dimension formatting helpers ─────────────────────────────────────

// dimRange formats a CLI (0-based exclusive end) range as the tool's
// 1-based inclusive A1-style range string. row → "3:7", column → "C:F".
// A single-element range collapses to "3" / "C".
func dimRange(dimension string, start, end int) string {
	if dimension == "column" {
		startLetter := columnIndexToLetter(start)
		endLetter := columnIndexToLetter(end - 1)
		if start == end-1 {
			return startLetter
		}
		return startLetter + ":" + endLetter
	}
	if start == end-1 {
		return fmt.Sprintf("%d", start+1)
	}
	return fmt.Sprintf("%d:%d", start+1, end)
}

// dimRangeFull is like dimRange but never collapses a single-element range to
// a bare index — it always emits the two-sided "N:N" / "C:C" form. resize_range
// rejects a bare index ("23" → Invalid range), so single-row/column resizes
// must keep both sides.
func dimRangeFull(dimension string, start, end int) string {
	if dimension == "column" {
		return columnIndexToLetter(start) + ":" + columnIndexToLetter(end-1)
	}
	return fmt.Sprintf("%d:%d", start+1, end)
}

// dimPosition formats a single CLI 0-based index as the tool's 1-based row
// number string or column letter.
func dimPosition(dimension string, idx int) string {
	if dimension == "column" {
		return columnIndexToLetter(idx)
	}
	return fmt.Sprintf("%d", idx+1)
}

// columnIndexToLetter converts a 0-based column index to the spreadsheet
// letter notation (0 → "A", 25 → "Z", 26 → "AA", 701 → "ZZ", 702 → "AAA").
func columnIndexToLetter(idx int) string {
	if idx < 0 {
		return ""
	}
	idx++
	var out []byte
	for idx > 0 {
		idx--
		out = append([]byte{byte('A' + idx%26)}, out...)
		idx /= 26
	}
	return string(out)
}

// ─── +dim-move (native v3 move_dimension, cli_status: cli-only) ──────
//
// Moves a contiguous block of rows or columns to a new index in the same
// sheet via the native v3 move_dimension endpoint (not the One-OpenAPI
// dispatcher). CLI's --start / --end are 0-based inclusive; v3
// move_dimension's source.{start_index,end_index} are likewise 0-based
// inclusive, so they pass straight through. The earlier build POSTed a
// {source,destinationIndex} body to the v2 dimension_range endpoint, which
// is the add/update/delete surface and expects a `dimension` object —
// hence the server rejected it with "[9499] Missing required parameter:
// Dimension".

var DimMove = common.Shortcut{
	Service:     "sheets",
	Command:     "+dim-move",
	Description: "Move a contiguous block of rows or columns to a new position (re-numbers neighbors).",
	Risk:        "write",
	Scopes:      []string{"sheets:spreadsheet:write_only", "sheets:spreadsheet:read"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+dim-move"),
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if _, err := resolveSpreadsheetToken(runtime); err != nil {
			return err
		}
		if _, _, err := resolveSheetSelector(runtime); err != nil {
			return err
		}
		if !runtime.Changed("dimension") || !runtime.Changed("start") || !runtime.Changed("end") || !runtime.Changed("target") {
			return common.FlagErrorf("--dimension / --start / --end / --target are all required")
		}
		if runtime.Int("start") < 0 || runtime.Int("end") < runtime.Int("start") {
			return common.FlagErrorf("--end (%d) must be >= --start (%d) (both 0-indexed, inclusive)", runtime.Int("end"), runtime.Int("start"))
		}
		if runtime.Int("target") < 0 {
			return common.FlagErrorf("--target must be >= 0")
		}
		return nil
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		sheetID, sheetName, _ := resolveSheetSelector(runtime)
		return common.NewDryRunAPI().
			POST(dimMovePath(token, sheetSelectorPlaceholder(sheetID, sheetName))).
			Body(dimMoveBody(runtime)).
			Set("spreadsheet_token", token)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		sheetID, sheetName, err := resolveSheetSelector(runtime)
		if err != nil {
			return err
		}
		// v3 move_dimension carries sheet_id in the path. Resolve
		// sheet_name client-side when needed (reuses lookupSheetIndex
		// which fetches workbook structure).
		if sheetID == "" {
			lookedID, _, err := lookupSheetIndex(ctx, runtime, token, "", sheetName)
			if err != nil {
				return err
			}
			sheetID = lookedID
		}
		data, err := runtime.CallAPI("POST", dimMovePath(token, sheetID), nil, dimMoveBody(runtime))
		if err != nil {
			return err
		}
		runtime.Out(data, nil)
		return nil
	},
}

// dimMovePath builds the native v3 move_dimension endpoint. sheet_id lives in
// the path (unlike the v2 dimension_range body that the earlier build used).
func dimMovePath(token, sheetID string) string {
	return fmt.Sprintf("/open-apis/sheets/v3/spreadsheets/%s/sheets/%s/move_dimension",
		validate.EncodePathSegment(token), validate.EncodePathSegment(sheetID))
}

func dimMoveBody(runtime *common.RuntimeContext) map[string]interface{} {
	dim := "ROWS"
	if runtime.Str("dimension") == "column" {
		dim = "COLUMNS"
	}
	return map[string]interface{}{
		"source": map[string]interface{}{
			"major_dimension": dim,
			"start_index":     runtime.Int("start"),
			"end_index":       runtime.Int("end"), // both CLI --end and v3 end_index are 0-based inclusive
		},
		"destination_index": runtime.Int("target"),
	}
}
