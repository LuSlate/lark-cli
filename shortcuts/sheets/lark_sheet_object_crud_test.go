// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"strings"
	"testing"

	"github.com/larksuite/cli/shortcuts/common"
)

// TestObjectCRUDShortcuts_DryRun walks the create / update / delete trio
// for each object skill. Together these cover all 21 CRUD shortcuts plus
// the per-object id flag renames (rule-id, group-id, view-id, etc.).
func TestObjectCRUDShortcuts_DryRun(t *testing.T) {
	t.Parallel()

	type spec struct {
		name      string
		sc        common.Shortcut
		args      []string
		toolName  string
		wantInput map[string]interface{}
	}

	tests := []spec{
		// chart
		{
			name:     "+chart-create",
			sc:       ChartCreate,
			args:     []string{"--url", testURL, "--sheet-id", testSheetID, "--properties", `{"type":"line"}`},
			toolName: "manage_chart_object",
			wantInput: map[string]interface{}{
				"excel_id":   testToken,
				"sheet_id":   testSheetID,
				"operation":  "create",
				"properties": map[string]interface{}{"type": "line"},
			},
		},
		{
			name:     "+chart-update",
			sc:       ChartUpdate,
			args:     []string{"--url", testURL, "--sheet-id", testSheetID, "--chart-id", "chartXYZ", "--properties", `{"type":"bar"}`},
			toolName: "manage_chart_object",
			wantInput: map[string]interface{}{
				"excel_id":   testToken,
				"sheet_id":   testSheetID,
				"operation":  "update",
				"chart_id":   "chartXYZ",
				"properties": map[string]interface{}{"type": "bar"},
			},
		},
		// pivot — has extra create flags incl. required --source.
		// --target-sheet-id is the placement target (where the pivot lands);
		// the placement selector is renamed from the generic --sheet-id /
		// --sheet-name to --target-sheet-id / --target-sheet-name to keep
		// it semantically distinct from the data-source sheet (which is
		// encoded inside --source as `'SheetName'!Range`).
		// pivotSpec.allowEmptySheetSelectorOnCreate lets both target
		// selectors be omitted so the backend auto-creates a sub-sheet —
		// covered separately in the +pivot-create empty-selector / mutex
		// tests below.
		{
			name: "+pivot-create with placement / source / range flags",
			sc:   PivotCreate,
			args: []string{
				"--url", testURL, "--target-sheet-id", testSheetID,
				"--properties", `{"rows":[{"field":"A"}]}`,
				"--source", "Sheet1!A1:F1000",
				"--range", "F1",
				"--target-position", "B5",
			},
			toolName: "manage_pivot_table_object",
			wantInput: map[string]interface{}{
				"excel_id":        testToken,
				"sheet_id":        testSheetID,
				"operation":       "create",
				"target_position": "B5",
				"properties": map[string]interface{}{
					"rows":   []interface{}{map[string]interface{}{"field": "A"}},
					"source": "Sheet1!A1:F1000",
					"range":  "F1",
				},
			},
		},
		// +pivot-create accepts both target selectors empty — backend
		// auto-creates a placement sub-sheet.
		{
			name: "+pivot-create empty --target-sheet-id / --target-sheet-name omits sheet from input",
			sc:   PivotCreate,
			args: []string{
				"--url", testURL,
				"--properties", `{"rows":[{"field":"A"}]}`,
				"--source", "Sheet1!A1:F1000",
			},
			toolName: "manage_pivot_table_object",
			wantInput: map[string]interface{}{
				"excel_id":  testToken,
				"operation": "create",
				"properties": map[string]interface{}{
					"rows":   []interface{}{map[string]interface{}{"field": "A"}},
					"source": "Sheet1!A1:F1000",
				},
			},
		},
		{
			name:     "+pivot-delete",
			sc:       PivotDelete,
			args:     []string{"--url", testURL, "--sheet-id", testSheetID, "--pivot-table-id", "ptA"},
			toolName: "manage_pivot_table_object",
			wantInput: map[string]interface{}{
				"excel_id":       testToken,
				"sheet_id":       testSheetID,
				"operation":      "delete",
				"pivot_table_id": "ptA",
			},
		},
		// cond-format — --rule-id rename + --rule-type / --ranges hoist.
		// rule_type lives at properties.rule_type (flat string), not nested
		// under a `rule` object; enum vocabulary matches server schema
		// (cellIs / duplicateValues / ... — see mcp-tools.json
		// manage_conditional_format_object.properties.rule_type).
		{
			name: "+cond-format-update id rename + rule-type/ranges",
			sc:   CondFormatUpdate,
			args: []string{
				"--url", testURL, "--sheet-id", testSheetID,
				"--rule-id", "ruleA",
				"--properties", `{"attrs":[{"operator":"greaterThan","value":"100"}],"style":{"back_color":"#FFD7D7"}}`,
				"--rule-type", "cellIs",
				"--ranges", `["A1:A100"]`,
			},
			toolName: "manage_conditional_format_object",
			wantInput: map[string]interface{}{
				"excel_id":              testToken,
				"sheet_id":              testSheetID,
				"operation":             "update",
				"conditional_format_id": "ruleA",
				"properties": map[string]interface{}{
					"rule_type": "cellIs",
					"attrs":     []interface{}{map[string]interface{}{"operator": "greaterThan", "value": "100"}},
					"style":     map[string]interface{}{"back_color": "#FFD7D7"},
					"ranges":    []interface{}{"A1:A100"},
				},
			},
		},
		// filter — special, no id flag
		{
			name:     "+filter-create without --properties sends properties.range only",
			sc:       FilterCreate,
			args:     []string{"--url", testURL, "--sheet-id", testSheetID, "--range", "A1:F1000"},
			toolName: "manage_filter_object",
			wantInput: map[string]interface{}{
				"excel_id":   testToken,
				"sheet_id":   testSheetID,
				"operation":  "create",
				"properties": map[string]interface{}{"range": "A1:F1000"},
			},
		},
		{
			name:     "+filter-create with --properties merges rules",
			sc:       FilterCreate,
			args:     []string{"--url", testURL, "--sheet-id", testSheetID, "--range", "A1:F1000", "--properties", `{"rules":[{"col":"B"}]}`},
			toolName: "manage_filter_object",
			wantInput: map[string]interface{}{
				"properties": map[string]interface{}{
					"range": "A1:F1000",
					"rules": []interface{}{map[string]interface{}{"col": "B"}},
				},
			},
		},
		{
			// +filter-delete has no separate --filter-id flag because the
			// server contract sets filter_id === sheet_id; the translator
			// auto-injects filter_id from --sheet-id. update/delete fail
			// hard when only --sheet-name is given (no mid-call lookup).
			name:     "+filter-delete (sheet-scoped, auto-injects filter_id=sheet_id)",
			sc:       FilterDelete,
			args:     []string{"--url", testURL, "--sheet-id", testSheetID},
			toolName: "manage_filter_object",
			wantInput: map[string]interface{}{
				"excel_id":  testToken,
				"sheet_id":  testSheetID,
				"filter_id": testSheetID,
				"operation": "delete",
			},
		},
		{
			// +filter-update auto-injects filter_id from sheet_id, hoists
			// --range out of properties, and merges properties.rules.
			name: "+filter-update auto-injects filter_id, hoists --range",
			sc:   FilterUpdate,
			args: []string{
				"--url", testURL, "--sheet-id", testSheetID,
				"--range", "A1:F1000",
				"--properties", `{"rules":[{"col":"B"}]}`,
			},
			toolName: "manage_filter_object",
			wantInput: map[string]interface{}{
				"excel_id":  testToken,
				"sheet_id":  testSheetID,
				"filter_id": testSheetID,
				"operation": "update",
				"properties": map[string]interface{}{
					"range": "A1:F1000",
					"rules": []interface{}{map[string]interface{}{"col": "B"}},
				},
			},
		},
		// filter-view CRUD (cli-only via callTool)
		{
			name:     "+filter-view-create",
			sc:       FilterViewCreate,
			args:     []string{"--url", testURL, "--sheet-id", testSheetID, "--range", "A1:Z100", "--properties", `{"view_name":"v1"}`},
			toolName: "manage_filter_view_object",
			wantInput: map[string]interface{}{
				"excel_id":   testToken,
				"sheet_id":   testSheetID,
				"operation":  "create",
				"properties": map[string]interface{}{"view_name": "v1", "range": "A1:Z100"},
			},
		},
		{
			name:     "+filter-view-update with --view-id",
			sc:       FilterViewUpdate,
			args:     []string{"--url", testURL, "--sheet-id", testSheetID, "--view-id", "vABC", "--properties", `{"view_name":"renamed"}`},
			toolName: "manage_filter_view_object",
			wantInput: map[string]interface{}{
				"view_id":   "vABC",
				"operation": "update",
			},
		},
		// sparkline --group-id
		{
			name:     "+sparkline-update --group-id → group_id",
			sc:       SparklineUpdate,
			args:     []string{"--url", testURL, "--sheet-id", testSheetID, "--group-id", "grpA", "--properties", `{"type":"line"}`},
			toolName: "manage_sparkline_object",
			wantInput: map[string]interface{}{
				"group_id":   "grpA",
				"operation":  "update",
				"properties": map[string]interface{}{"type": "line"},
			},
		},
		{
			// happy path for the new sparkline_id check: each
			// properties.sparklines[i] carries sparkline_id, so the
			// validator passes through cleanly.
			name: "+sparkline-update properties.sparklines[] with sparkline_id passes",
			sc:   SparklineUpdate,
			args: []string{
				"--url", testURL, "--sheet-id", testSheetID, "--group-id", "grpA",
				"--properties", `{"sparklines":[{"sparkline_id":"sl1","source":"Sheet1!A1:A10"}]}`,
			},
			toolName: "manage_sparkline_object",
			wantInput: map[string]interface{}{
				"group_id":  "grpA",
				"operation": "update",
				"properties": map[string]interface{}{
					"sparklines": []interface{}{
						map[string]interface{}{"sparkline_id": "sl1", "source": "Sheet1!A1:A10"},
					},
				},
			},
		},
		// float-image — fully hoisted to flat flags
		{
			name: "+float-image-create with image-token + position/size",
			sc:   FloatImageCreate,
			args: []string{
				"--url", testURL, "--sheet-id", testSheetID,
				"--image-name", "logo.png",
				"--image-token", "tok_xyz",
				"--position-row", "2", "--position-col", "D",
				"--size-width", "300", "--size-height", "200",
			},
			toolName: "manage_float_image_object",
			wantInput: map[string]interface{}{
				"excel_id":  testToken,
				"sheet_id":  testSheetID,
				"operation": "create",
				"properties": map[string]interface{}{
					"image_name":  "logo.png",
					"image_token": "tok_xyz",
					"position":    map[string]interface{}{"row": float64(2), "col": "D"},
					"size":        map[string]interface{}{"width": float64(300), "height": float64(200)},
				},
			},
		},
		{
			// patch mode: position + size with no image source. The image
			// fields are omitted so the server keeps the current image; only
			// image_name (server-mandated) and the changed geometry are sent.
			// This is the shape that used to be rejected CLI-side.
			name: "+float-image-update patch position+size, no image source",
			sc:   FloatImageUpdate,
			args: []string{
				"--url", testURL, "--sheet-id", testSheetID,
				"--float-image-id", "imgABC", "--image-name", "logo.png",
				"--position-row", "10", "--position-col", "I",
				"--size-width", "90", "--size-height", "70",
			},
			toolName: "manage_float_image_object",
			wantInput: map[string]interface{}{
				"excel_id":       testToken,
				"sheet_id":       testSheetID,
				"operation":      "update",
				"float_image_id": "imgABC",
				"properties": map[string]interface{}{
					"image_name": "logo.png",
					"position":   map[string]interface{}{"row": float64(10), "col": "I"},
					"size":       map[string]interface{}{"width": float64(90), "height": float64(70)},
				},
			},
		},
		{
			// swap the image: an explicit --image-token rides alongside the
			// mandatory core (image_name + position + size).
			name: "+float-image-update swap image via image-token",
			sc:   FloatImageUpdate,
			args: []string{
				"--url", testURL, "--sheet-id", testSheetID,
				"--float-image-id", "imgABC",
				"--image-name", "new.png", "--image-token", "tok_new",
				"--position-row", "2", "--position-col", "B",
				"--size-width", "300", "--size-height", "200",
			},
			toolName: "manage_float_image_object",
			wantInput: map[string]interface{}{
				"excel_id":       testToken,
				"sheet_id":       testSheetID,
				"operation":      "update",
				"float_image_id": "imgABC",
				"properties": map[string]interface{}{
					"image_name":  "new.png",
					"image_token": "tok_new",
					"position":    map[string]interface{}{"row": float64(2), "col": "B"},
					"size":        map[string]interface{}{"width": float64(300), "height": float64(200)},
				},
			},
		},
	}
	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			body := parseDryRunBody(t, tt.sc, tt.args)
			got := decodeToolInput(t, body, tt.toolName)
			assertInputEquals(t, got, tt.wantInput)
		})
	}
}

// TestPivotCreate_SheetSelectorSemantics locks in the "at most one"
// semantics for +pivot-create (and only +pivot-create): both
// --target-sheet-id and --target-sheet-name may be omitted (backend
// auto-creates a placement sub-sheet), but passing both is rejected.
//
// Companion regression — TestObjectCreate_RequiresSheetSelector below —
// confirms every other *-create still rejects empty selector.
func TestPivotCreate_SheetSelectorSemantics(t *testing.T) {
	t.Parallel()

	t.Run("both empty is accepted", func(t *testing.T) {
		t.Parallel()
		body := parseDryRunBody(t, PivotCreate, []string{
			"--url", testURL,
			"--properties", `{"rows":[{"field":"A"}]}`,
			"--source", "Sheet1!A1:F1000",
		})
		input := decodeToolInput(t, body, "manage_pivot_table_object")
		if _, ok := input["sheet_id"]; ok {
			t.Errorf("expected no sheet_id in input; got %v", input["sheet_id"])
		}
		if _, ok := input["sheet_name"]; ok {
			t.Errorf("expected no sheet_name in input; got %v", input["sheet_name"])
		}
	})

	t.Run("both set is rejected", func(t *testing.T) {
		t.Parallel()
		_, stderr, err := runShortcutCapturingErr(t, PivotCreate, []string{
			"--url", testURL,
			"--target-sheet-id", testSheetID,
			"--target-sheet-name", "Sheet1",
			"--properties", `{"rows":[{"field":"A"}]}`,
			"--source", "Sheet1!A1:F1000",
		})
		if err == nil {
			t.Fatalf("expected CLI to reject both --target-sheet-id and --target-sheet-name set; stderr=%s", stderr)
		}
		combined := stderr + err.Error()
		if !strings.Contains(combined, "mutually exclusive") {
			t.Errorf("expected error to say 'mutually exclusive'; got=%s|%v", stderr, err)
		}
		// 错误信息必须用真实的 flag 名（target-*），否则模型按消息提示去
		// 改 --sheet-id 还是错的。
		if !strings.Contains(combined, "--target-sheet-id") {
			t.Errorf("expected error to quote --target-sheet-id flag name; got=%s|%v", stderr, err)
		}
	})

	t.Run("only target-sheet-id is accepted", func(t *testing.T) {
		t.Parallel()
		body := parseDryRunBody(t, PivotCreate, []string{
			"--url", testURL,
			"--target-sheet-id", testSheetID,
			"--properties", `{"rows":[{"field":"A"}]}`,
			"--source", "Sheet1!A1:F1000",
		})
		input := decodeToolInput(t, body, "manage_pivot_table_object")
		if got, _ := input["sheet_id"].(string); got != testSheetID {
			t.Errorf("sheet_id = %q, want %q", got, testSheetID)
		}
	})
}

// TestObjectCreate_RequiresSheetSelector regresses the non-pivot create
// shortcuts: pivot-create is the only one whose spec sets
// allowEmptySheetSelectorOnCreate=true. Every other *-create must still
// reject empty --sheet-id / --sheet-name (this is the guardrail that
// keeps the change minimally scoped).
func TestObjectCreate_RequiresSheetSelector(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name string
		sc   common.Shortcut
		args []string // omit sheet selector flags on purpose
	}{
		{"chart", ChartCreate, []string{"--url", testURL, "--properties", `{"type":"line"}`}},
		{"cond-format", CondFormatCreate, []string{"--url", testURL, "--properties", `{"attrs":[]}`, "--rule-type", "cellIs", "--ranges", `["A1:A10"]`}},
		{"sparkline", SparklineCreate, []string{"--url", testURL, "--properties", `{"sparklines":[]}`}},
		{"filter-view", FilterViewCreate, []string{"--url", testURL, "--properties", `{}`, "--range", "A1:F10"}},
	}
	for _, tt := range cases {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			_, stderr, err := runShortcutCapturingErr(t, tt.sc, tt.args)
			if err == nil {
				t.Fatalf("expected CLI to reject empty sheet selector for +%s-create; stderr=%s", tt.name, stderr)
			}
			combined := stderr + err.Error()
			if !strings.Contains(combined, "specify at least one of --sheet-id or --sheet-name") {
				t.Errorf("expected 'specify at least one of --sheet-id or --sheet-name'; got=%s|%v", stderr, err)
			}
		})
	}
}

// TestSparklineUpdate_MissingSparklineID confirms the standalone-path
// pre-check fires: +sparkline-update with properties.sparklines[] but no
// per-item sparkline_id must fail CLI-side with a pointer to
// +sparkline-list, before any server call goes out.
func TestSparklineUpdate_MissingSparklineID(t *testing.T) {
	t.Parallel()
	_, stderr, err := runShortcutCapturingErr(t, SparklineUpdate, []string{
		"--url", testURL, "--sheet-id", testSheetID, "--group-id", "grpA",
		"--properties", `{"sparklines":[{"source":"Sheet1!A1:A10"}]}`,
	})
	if err == nil {
		t.Fatalf("expected CLI to reject missing sparkline_id; stderr=%s", stderr)
	}
	combined := stderr + err.Error()
	if !strings.Contains(combined, "missing sparkline_id") {
		t.Errorf("expected error to mention missing sparkline_id; got=%s|%v", stderr, err)
	}
	if !strings.Contains(combined, "+sparkline-list") {
		t.Errorf("expected error to point at +sparkline-list; got=%s|%v", stderr, err)
	}
}

// Note: +float-image-update's image_name / position / size are cobra-required
// (flag-defs.json), so the standalone path is gated by the flag layer — its
// "required flag(s) … not set" wording is framework-owned and intentionally not
// re-asserted here. The CLI-side enforcement that matters is on the
// +batch-update sub-op path (no cobra layer); that is covered by
// TestBatchOp_RejectsBadSubOpInput in batch_op_contract_test.go.

// TestFloatImageCreate_RequiresImageSource guards the asymmetry with update:
// create still mandates one of --image / --image-token / --image-uri.
func TestFloatImageCreate_RequiresImageSource(t *testing.T) {
	t.Parallel()
	_, stderr, err := runShortcutCapturingErr(t, FloatImageCreate, []string{
		"--url", testURL, "--sheet-id", testSheetID,
		"--image-name", "x.png",
		"--position-row", "0", "--position-col", "A",
		"--size-width", "10", "--size-height", "10",
	})
	if err == nil {
		t.Fatalf("expected CLI to require an image source on create; stderr=%s", stderr)
	}
	if combined := stderr + err.Error(); !strings.Contains(combined, "one of --image, --image-token, or --image-uri is required") {
		t.Errorf("expected error to require an image source; got=%s|%v", stderr, err)
	}
}

// TestObjectDelete_AllHighRisk asserts every delete shortcut blocks
// without --yes (framework-enforced).
func TestObjectDelete_AllHighRisk(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name string
		sc   common.Shortcut
		args []string
	}{
		{"chart", ChartDelete, []string{"--url", testURL, "--sheet-id", testSheetID, "--chart-id", "x"}},
		{"pivot", PivotDelete, []string{"--url", testURL, "--sheet-id", testSheetID, "--pivot-table-id", "x"}},
		{"cond-format", CondFormatDelete, []string{"--url", testURL, "--sheet-id", testSheetID, "--rule-id", "x"}},
		{"filter", FilterDelete, []string{"--url", testURL, "--sheet-id", testSheetID}},
		{"filter-view", FilterViewDelete, []string{"--url", testURL, "--sheet-id", testSheetID, "--view-id", "x"}},
		{"sparkline", SparklineDelete, []string{"--url", testURL, "--sheet-id", testSheetID, "--group-id", "x"}},
		{"float-image", FloatImageDelete, []string{"--url", testURL, "--sheet-id", testSheetID, "--float-image-id", "x"}},
	}
	for _, tt := range cases {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			stdout, stderr, err := runShortcutCapturingErr(t, tt.sc, tt.args)
			if err == nil {
				t.Fatalf("expected confirmation_required; stdout=%s stderr=%s", stdout, stderr)
			}
			combined := stdout + stderr + err.Error()
			if !strings.Contains(combined, "confirmation_required") && !strings.Contains(combined, "requires confirmation") {
				t.Errorf("expected confirmation gate; got=%s|%s|%v", stdout, stderr, err)
			}
		})
	}
}
