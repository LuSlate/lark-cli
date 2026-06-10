// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package doc

import (
	"context"
	"testing"

	"github.com/larksuite/cli/shortcuts/common"
	"github.com/spf13/cobra"
)

func newCoverTestRuntime() *common.RuntimeContext {
	cmd := &cobra.Command{Use: "+cover"}
	cmd.Flags().String("doc", "", "")
	cmd.Flags().String("token", "", "")
	cmd.Flags().String("offset-ratio-x", "", "")
	cmd.Flags().String("offset-ratio-y", "", "")
	return common.TestNewRuntimeContextWithCtx(context.Background(), cmd, nil)
}

func TestResolveCoverDocumentID(t *testing.T) {
	cases := []struct {
		name    string
		doc     string
		wantID  string
		wantErr bool
	}{
		{"raw token", "doxcnAbc123", "doxcnAbc123", false},
		{"docx url", "https://x.larkoffice.com/docx/doxcnAbc123", "doxcnAbc123", false},
		{"wiki url rejected", "https://x.larkoffice.com/wiki/wikAbc123", "", true},
		{"empty rejected", "", "", true},
	}
	for _, tt := range cases {
		t.Run(tt.name, func(t *testing.T) {
			rt := newCoverTestRuntime()
			_ = rt.Cmd.Flags().Set("doc", tt.doc)
			id, err := resolveCoverDocumentID(rt)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error for %q, got id=%q", tt.doc, id)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if id != tt.wantID {
				t.Fatalf("id = %q, want %q", id, tt.wantID)
			}
		})
	}
}

func TestParseOptionalOffset(t *testing.T) {
	cases := []struct {
		name        string
		val         string
		wantPresent bool
		wantVal     float64
		wantErr     bool
	}{
		{"not provided", "", false, 0, false},
		{"valid float", "0.25", true, 0.25, false},
		{"valid negative", "-0.5", true, -0.5, false},
		{"non-numeric", "abc", false, 0, true},
		{"NaN", "NaN", false, 0, true},
		{"Inf", "Inf", false, 0, true},
	}
	for _, tt := range cases {
		t.Run(tt.name, func(t *testing.T) {
			rt := newCoverTestRuntime()
			_ = rt.Cmd.Flags().Set("offset-ratio-x", tt.val)
			v, present, err := parseOptionalOffset(rt, "offset-ratio-x")
			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error for %q", tt.val)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if present != tt.wantPresent {
				t.Fatalf("present = %v, want %v", present, tt.wantPresent)
			}
			if present && v != tt.wantVal {
				t.Fatalf("val = %v, want %v", v, tt.wantVal)
			}
		})
	}
}

func TestBuildCoverUpdateBodyOmitsOffsetWhenUnset(t *testing.T) {
	rt := newCoverTestRuntime()
	_ = rt.Cmd.Flags().Set("token", "filetokenABC")

	body := buildCoverUpdateBody(rt)
	cover := body["update_cover"].(map[string]interface{})["cover"].(map[string]interface{})
	if cover["token"] != "filetokenABC" {
		t.Fatalf("token = %#v, want filetokenABC", cover["token"])
	}
	if _, ok := cover["offset_ratio_x"]; ok {
		t.Fatalf("offset_ratio_x must be omitted when unset: %#v", cover)
	}
	if _, ok := cover["offset_ratio_y"]; ok {
		t.Fatalf("offset_ratio_y must be omitted when unset: %#v", cover)
	}
}

func TestBuildCoverUpdateBodyIncludesOffsetWhenSet(t *testing.T) {
	rt := newCoverTestRuntime()
	_ = rt.Cmd.Flags().Set("token", "filetokenABC")
	_ = rt.Cmd.Flags().Set("offset-ratio-x", "0.1")
	_ = rt.Cmd.Flags().Set("offset-ratio-y", "0.2")

	body := buildCoverUpdateBody(rt)
	cover := body["update_cover"].(map[string]interface{})["cover"].(map[string]interface{})
	if cover["offset_ratio_x"] != 0.1 {
		t.Fatalf("offset_ratio_x = %#v, want 0.1", cover["offset_ratio_x"])
	}
	if cover["offset_ratio_y"] != 0.2 {
		t.Fatalf("offset_ratio_y = %#v, want 0.2", cover["offset_ratio_y"])
	}
}

func TestBuildCoverDeleteBodyIsNull(t *testing.T) {
	body := buildCoverDeleteBody()
	cover, ok := body["update_cover"].(map[string]interface{})
	if !ok {
		t.Fatalf("update_cover missing: %#v", body)
	}
	v, present := cover["cover"]
	if !present {
		t.Fatalf("cover key must be present (explicit null): %#v", cover)
	}
	if v != nil {
		t.Fatalf("cover must be nil for delete, got %#v", v)
	}
}

func TestValidateCoverUpdateRequiresToken(t *testing.T) {
	rt := newCoverTestRuntime()
	_ = rt.Cmd.Flags().Set("doc", "doxcnAbc123")
	// no --token
	if err := validateCoverUpdate(context.Background(), rt); err == nil {
		t.Fatal("expected error when --token missing")
	}

	_ = rt.Cmd.Flags().Set("token", "filetokenABC")
	if err := validateCoverUpdate(context.Background(), rt); err != nil {
		t.Fatalf("unexpected error with token set: %v", err)
	}
}
