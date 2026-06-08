// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"strings"
	"testing"
)

// TestUndo_DryRun asserts the undo_last body for the three selection shapes:
// default (steps=1), explicit --steps, and --op. Numbers round-trip through
// the wire JSON as float64, matching the other dry-run body tests.
func TestUndo_DryRun(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		args      []string
		wantInput map[string]interface{}
	}{
		{
			name: "default undoes last step",
			args: []string{"--url", testURL},
			wantInput: map[string]interface{}{
				"excel_id": testToken,
				"steps":    float64(1),
			},
		},
		{
			name: "explicit --steps",
			args: []string{"--url", testURL, "--steps", "3"},
			wantInput: map[string]interface{}{
				"excel_id": testToken,
				"steps":    float64(3),
			},
		},
		{
			name: "--op targets a specific operation",
			args: []string{"--spreadsheet-token", testToken, "--op", "op_5"},
			wantInput: map[string]interface{}{
				"excel_id":     testToken,
				"operation_id": "op_5",
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			body := parseDryRunBody(t, Undo, tt.args)
			got := decodeToolInput(t, body, "undo_last")
			assertInputEquals(t, got, tt.wantInput)
		})
	}
}

// TestUndo_Validation covers the XOR token check, the --steps/--op
// mutual exclusion, and the --steps lower bound.
func TestUndo_Validation(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name    string
		args    []string
		wantMsg string
	}{
		{
			name:    "needs --url or --spreadsheet-token",
			args:    []string{},
			wantMsg: "at least one of --url or --spreadsheet-token",
		},
		{
			name:    "--steps and --op are mutually exclusive",
			args:    []string{"--url", testURL, "--steps", "2", "--op", "op_5"},
			wantMsg: "mutually exclusive",
		},
		{
			name:    "--steps must be >= 1",
			args:    []string{"--url", testURL, "--steps", "0"},
			wantMsg: "--steps must be >= 1",
		},
	}
	for _, tt := range cases {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			stdout, stderr, err := runShortcutCapturingErr(t, Undo, append(tt.args, "--dry-run"))
			if err == nil {
				t.Fatalf("expected validation error; got nil. stdout=%s stderr=%s", stdout, stderr)
			}
			combined := stdout + stderr + err.Error()
			if !strings.Contains(combined, tt.wantMsg) {
				t.Errorf("error message missing %q; got=%s", tt.wantMsg, combined)
			}
		})
	}
}
