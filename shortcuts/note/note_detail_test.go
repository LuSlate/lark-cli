// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package note

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"strings"
	"sync"
	"testing"

	"github.com/spf13/cobra"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/core"
	"github.com/larksuite/cli/internal/httpmock"
	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
)

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

var noteWarmOnce sync.Once

func noteWarmTokenCache(t *testing.T) {
	t.Helper()
	noteWarmOnce.Do(func() {
		f, _, _, reg := cmdutil.TestFactory(t, noteDefaultConfig())
		reg.Register(&httpmock.Stub{
			URL:  "/open-apis/test/v1/warm",
			Body: map[string]interface{}{"code": 0, "msg": "ok", "data": map[string]interface{}{}},
		})
		s := common.Shortcut{
			Service:   "test",
			Command:   "+warm",
			AuthTypes: []string{"bot"},
			Execute: func(_ context.Context, rctx *common.RuntimeContext) error {
				_, err := rctx.CallAPI("GET", "/open-apis/test/v1/warm", nil, nil)
				return err
			},
		}
		parent := &cobra.Command{Use: "test"}
		s.Mount(parent, f)
		parent.SetArgs([]string{"+warm"})
		parent.SilenceErrors = true
		parent.SilenceUsage = true
		parent.Execute()
	})
}

func noteDefaultConfig() *core.CliConfig {
	return &core.CliConfig{
		AppID: "test-app", AppSecret: "test-secret", Brand: core.BrandFeishu,
		UserOpenId: "ou_testuser",
	}
}

func noteMountAndRun(t *testing.T, s common.Shortcut, args []string, f *cmdutil.Factory, stdout *bytes.Buffer) error {
	t.Helper()
	noteWarmTokenCache(t)
	parent := &cobra.Command{Use: "note"}
	s.Mount(parent, f)
	parent.SetArgs(args)
	parent.SilenceErrors = true
	parent.SilenceUsage = true
	if stdout != nil {
		stdout.Reset()
	}
	return parent.Execute()
}

func noteBotExec(t *testing.T, name string, f *cmdutil.Factory, fn func(context.Context, *common.RuntimeContext) error) error {
	t.Helper()
	noteWarmTokenCache(t)
	s := common.Shortcut{
		Service:   "test",
		Command:   "+" + name,
		AuthTypes: []string{"bot"},
		HasFormat: true,
		Execute:   fn,
	}
	parent := &cobra.Command{Use: "note"}
	s.Mount(parent, f)
	parent.SetArgs([]string{"+" + name, "--format", "json"})
	parent.SilenceErrors = true
	parent.SilenceUsage = true
	return parent.Execute()
}

// ---------------------------------------------------------------------------
// Validation tests
// ---------------------------------------------------------------------------

func TestNoteDetail_Validation_MissingNoteID(t *testing.T) {
	f, _, _, _ := cmdutil.TestFactory(t, noteDefaultConfig())
	err := noteMountAndRun(t, NoteDetail, []string{"+detail", "--as", "user"}, f, nil)
	if err == nil {
		t.Fatal("expected validation error for missing --note-id")
	}
}

// ---------------------------------------------------------------------------
// DryRun tests
// ---------------------------------------------------------------------------

func TestNoteDetail_DryRun(t *testing.T) {
	f, stdout, _, _ := cmdutil.TestFactory(t, noteDefaultConfig())
	err := noteMountAndRun(t, NoteDetail, []string{"+detail", "--note-id", "note001", "--dry-run", "--as", "user"}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(stdout.String(), "/open-apis/vc/v1/notes/") {
		t.Errorf("dry-run should show notes API path, got: %s", stdout.String())
	}
}

// ---------------------------------------------------------------------------
// Execute tests with mocked HTTP
// ---------------------------------------------------------------------------

func noteDetailStub(noteID string) *httpmock.Stub {
	return &httpmock.Stub{
		Method: "GET",
		URL:    "/open-apis/vc/v1/notes/" + noteID,
		Body: map[string]interface{}{
			"code": 0, "msg": "ok",
			"data": map[string]interface{}{
				"note": map[string]interface{}{
					"creator_id":  "ou_creator",
					"create_time": "1700000000",
					"artifacts": []interface{}{
						map[string]interface{}{"doc_token": "doc_main", "artifact_type": 1},
						map[string]interface{}{"doc_token": "doc_verbatim", "artifact_type": 2},
					},
					"references": []interface{}{
						map[string]interface{}{"doc_token": "doc_shared1"},
					},
				},
			},
		},
	}
}

func TestNoteDetail_Execute_Success(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, noteDefaultConfig())
	reg.Register(noteDetailStub("note_exec1"))

	err := noteMountAndRun(t, NoteDetail, []string{"+detail", "--note-id", "note_exec1", "--as", "user"}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var resp map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &resp); err != nil {
		t.Fatalf("failed to parse output: %v", err)
	}
	data, _ := resp["data"].(map[string]any)
	notes, _ := data["notes"].(map[string]any)
	if notes == nil {
		t.Fatal("expected notes object in data")
	}
	if notes["note_id"] != "note_exec1" {
		t.Errorf("note_id = %v, want note_exec1", notes["note_id"])
	}
	if notes["note_doc_token"] != "doc_main" {
		t.Errorf("note_doc_token = %v, want doc_main", notes["note_doc_token"])
	}
	if notes["verbatim_doc_token"] != "doc_verbatim" {
		t.Errorf("verbatim_doc_token = %v, want doc_verbatim", notes["verbatim_doc_token"])
	}
}

func TestNoteDetail_Execute_NoPermission(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, noteDefaultConfig())
	reg.Register(&httpmock.Stub{
		Method: "GET",
		URL:    "/open-apis/vc/v1/notes/note_noperm",
		Body:   map[string]interface{}{"code": 121005, "msg": "no permission"},
	})

	err := noteMountAndRun(t, NoteDetail, []string{"+detail", "--note-id", "note_noperm", "--as", "user"}, f, stdout)
	if err == nil {
		t.Fatal("expected partial failure error")
	}
	var pfErr *output.PartialFailureError
	if !errors.As(err, &pfErr) {
		t.Fatalf("expected *output.PartialFailureError, got %T: %v", err, err)
	}
	if pfErr.Code != output.ExitAPI {
		t.Errorf("Code = %d, want ExitAPI", pfErr.Code)
	}
}

func TestNoteDetail_Execute_NotFound(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, noteDefaultConfig())
	reg.Register(&httpmock.Stub{
		Method: "GET",
		URL:    "/open-apis/vc/v1/notes/note_nf",
		Body:   map[string]interface{}{"code": 121004, "msg": "not found"},
	})

	err := noteMountAndRun(t, NoteDetail, []string{"+detail", "--note-id", "note_nf", "--as", "user"}, f, stdout)
	if err == nil {
		t.Fatal("expected partial failure error")
	}
}

// ---------------------------------------------------------------------------
// Pure function tests
// ---------------------------------------------------------------------------

func TestParseArtifactType(t *testing.T) {
	tests := []struct {
		input any
		want  int
	}{
		{float64(1), 1},
		{float64(2), 2},
		{"unknown", 0},
		{nil, 0},
	}
	for _, tt := range tests {
		got := parseArtifactType(tt.input)
		if got != tt.want {
			t.Errorf("parseArtifactType(%v) = %d, want %d", tt.input, got, tt.want)
		}
	}
}

func TestExtractArtifactTokens(t *testing.T) {
	artifacts := []any{
		map[string]any{"doc_token": "main_doc", "artifact_type": float64(1)},
		map[string]any{"doc_token": "verbatim_doc", "artifact_type": float64(2)},
		map[string]any{"doc_token": "unknown_doc", "artifact_type": float64(99)},
		nil,
	}
	noteDoc, verbatimDoc := extractArtifactTokens(artifacts)
	if noteDoc != "main_doc" {
		t.Errorf("noteDoc = %q, want %q", noteDoc, "main_doc")
	}
	if verbatimDoc != "verbatim_doc" {
		t.Errorf("verbatimDoc = %q, want %q", verbatimDoc, "verbatim_doc")
	}
}

func TestExtractDocTokens(t *testing.T) {
	refs := []any{
		map[string]any{"doc_token": "shared1"},
		map[string]any{"doc_token": "shared2"},
		map[string]any{"doc_token": ""},
		map[string]any{},
		nil,
	}
	tokens := extractDocTokens(refs)
	if len(tokens) != 2 || tokens[0] != "shared1" || tokens[1] != "shared2" {
		t.Errorf("extractDocTokens = %v, want [shared1 shared2]", tokens)
	}
}

func TestExtractDocTokens_Empty(t *testing.T) {
	tokens := extractDocTokens(nil)
	if len(tokens) != 0 {
		t.Errorf("expected empty slice for nil input, got %v", tokens)
	}
}

// ---------------------------------------------------------------------------
// fetchNoteDetail via botExec
// ---------------------------------------------------------------------------

func TestFetchNoteDetail_Success(t *testing.T) {
	t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())
	f, _, _, reg := cmdutil.TestFactory(t, noteDefaultConfig())
	reg.Register(noteDetailStub("note_fn"))

	if err := noteBotExec(t, "detail-fn", f, func(_ context.Context, rctx *common.RuntimeContext) error {
		result := fetchNoteDetail(context.Background(), rctx, "note_fn")
		if result.NoteID != "note_fn" {
			t.Errorf("note_id = %v, want note_fn", result.NoteID)
		}
		if result.NoteDocToken != "doc_main" {
			t.Errorf("note_doc_token = %v, want doc_main", result.NoteDocToken)
		}
		if result.VerbatimDocToken != "doc_verbatim" {
			t.Errorf("verbatim_doc_token = %v, want doc_verbatim", result.VerbatimDocToken)
		}
		if result.Error != "" {
			t.Errorf("unexpected error: %v", result.Error)
		}
		return nil
	}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestFetchNoteDetail_NoPermission(t *testing.T) {
	t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())
	f, _, _, reg := cmdutil.TestFactory(t, noteDefaultConfig())
	reg.Register(&httpmock.Stub{
		Method: "GET",
		URL:    "/open-apis/vc/v1/notes/note_perm",
		Body:   map[string]interface{}{"code": 121005, "msg": "no permission"},
	})

	if err := noteBotExec(t, "detail-perm", f, func(_ context.Context, rctx *common.RuntimeContext) error {
		result := fetchNoteDetail(context.Background(), rctx, "note_perm")
		if result.Error == "" {
			t.Error("expected error for no permission")
		}
		if !strings.Contains(result.Error, "no read permission") {
			t.Errorf("error = %q, want contains 'no read permission'", result.Error)
		}
		return nil
	}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}
