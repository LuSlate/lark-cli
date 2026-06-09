// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package vc

import (
	"context"
	"encoding/json"
	"net/http"
	"testing"

	"github.com/spf13/cobra"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/core"
	"github.com/larksuite/cli/internal/httpmock"
	"github.com/larksuite/cli/shortcuts/common"
)

// ---------------------------------------------------------------------------
// Unit tests: validation + param assembly (UAT/TAT identity split)
// ---------------------------------------------------------------------------

func newActiveMeetingsCmd() *cobra.Command {
	cmd := &cobra.Command{Use: "test"}
	cmd.Flags().String("user-id", "", "")
	return cmd
}

func TestMeetingListActive_Validate_BotRequiresUserID(t *testing.T) {
	cmd := newActiveMeetingsCmd()
	runtime := common.TestNewRuntimeContextWithIdentity(cmd, defaultConfig(), core.AsBot)
	if err := VCMeetingListActive.Validate(context.Background(), runtime); err == nil {
		t.Fatal("expected error: --user-id required when --as bot")
	}
}

func TestMeetingListActive_Validate_BotRejectsNonOpenID(t *testing.T) {
	cmd := newActiveMeetingsCmd()
	_ = cmd.Flags().Set("user-id", "123456")
	runtime := common.TestNewRuntimeContextWithIdentity(cmd, defaultConfig(), core.AsBot)
	if err := VCMeetingListActive.Validate(context.Background(), runtime); err == nil {
		t.Fatal("expected error: --user-id must be an open_id")
	}
}

func TestMeetingListActive_Validate_UserNoUserID_OK(t *testing.T) {
	cmd := newActiveMeetingsCmd()
	runtime := common.TestNewRuntimeContextWithIdentity(cmd, defaultConfig(), core.AsUser)
	if err := VCMeetingListActive.Validate(context.Background(), runtime); err != nil {
		t.Fatalf("unexpected error for UAT without user-id: %v", err)
	}
}

func TestBuildActiveMeetingsParams_UAT_OmitsUserID(t *testing.T) {
	cmd := newActiveMeetingsCmd()
	_ = cmd.Flags().Set("user-id", "ou_ignored")
	runtime := common.TestNewRuntimeContextWithIdentity(cmd, defaultConfig(), core.AsUser)
	params := buildActiveMeetingsParams(runtime)
	if _, exists := params["user_id"]; exists {
		t.Errorf("UAT must not send user_id, got %v", params["user_id"])
	}
}

func TestBuildActiveMeetingsParams_TAT_SendsUserID(t *testing.T) {
	cmd := newActiveMeetingsCmd()
	_ = cmd.Flags().Set("user-id", "ou_target")
	runtime := common.TestNewRuntimeContextWithIdentity(cmd, defaultConfig(), core.AsBot)
	params := buildActiveMeetingsParams(runtime)
	if params["user_id"] != "ou_target" {
		t.Errorf("TAT user_id = %v, want ou_target", params["user_id"])
	}
}

// ---------------------------------------------------------------------------
// Execute tests: final observable (no / single / multi meeting semantics)
// ---------------------------------------------------------------------------

func TestMeetingListActive_Execute_UAT_Multi(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, defaultConfig())
	reg.Register(&httpmock.Stub{
		Method: "GET",
		URL:    "/open-apis/vc/v1/bots/active-meetings",
		Body: map[string]interface{}{
			"code": 0, "msg": "ok",
			"data": map[string]interface{}{
				"meetings": []interface{}{
					map[string]interface{}{"meeting_no": "111", "meeting_id": "9001", "meeting_title": "Standup"},
					map[string]interface{}{"meeting_no": "222", "meeting_id": "9002", "meeting_title": "Review"},
				},
			},
		},
	})

	err := mountAndRun(t, VCMeetingListActive, []string{
		"+meeting-list-active", "--as", "user", "--format", "json",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var resp map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &resp); err != nil {
		t.Fatalf("failed to parse stdout: %v", err)
	}
	data, _ := resp["data"].(map[string]any)
	meetings, _ := data["meetings"].([]any)
	if len(meetings) != 2 {
		t.Fatalf("meetings count = %d, want 2 (envelope: %s)", len(meetings), stdout.String())
	}
	first, _ := meetings[0].(map[string]any)
	if first["meeting_id"] != "9001" || first["meeting_title"] != "Standup" {
		t.Errorf("unexpected first meeting: %v", first)
	}
}

func TestMeetingListActive_Execute_Empty(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, defaultConfig())
	reg.Register(&httpmock.Stub{
		Method: "GET",
		URL:    "/open-apis/vc/v1/bots/active-meetings",
		Body: map[string]interface{}{
			"code": 0, "msg": "ok",
			"data": map[string]interface{}{"meetings": []interface{}{}},
		},
	})

	err := mountAndRun(t, VCMeetingListActive, []string{
		"+meeting-list-active", "--as", "user", "--format", "json",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var resp map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &resp); err != nil {
		t.Fatalf("failed to parse stdout: %v", err)
	}
	data, _ := resp["data"].(map[string]any)
	meetings, _ := data["meetings"].([]any)
	if len(meetings) != 0 {
		t.Errorf("meetings count = %d, want 0", len(meetings))
	}
}

func TestMeetingListActive_Execute_TAT_SendsUserIDParam(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, defaultConfig())
	var capturedUserID string
	stub := &httpmock.Stub{
		Method: "GET",
		URL:    "/open-apis/vc/v1/bots/active-meetings",
		OnMatch: func(req *http.Request) {
			capturedUserID = req.URL.Query().Get("user_id")
		},
		Body: map[string]interface{}{
			"code": 0, "msg": "ok",
			"data": map[string]interface{}{
				"meetings": []interface{}{
					map[string]interface{}{"meeting_no": "333", "meeting_id": "9003", "meeting_title": "Bot Meeting"},
				},
			},
		},
	}
	reg.Register(stub)

	err := mountAndRun(t, VCMeetingListActive, []string{
		"+meeting-list-active", "--as", "bot", "--user-id", "ou_target", "--format", "json",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if capturedUserID != "ou_target" {
		t.Errorf("captured user_id query = %q, want ou_target", capturedUserID)
	}
}
