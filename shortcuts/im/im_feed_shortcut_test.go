// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package im

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/core"
	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
	"github.com/spf13/cobra"
)

// newFeedShortcutCreateCmd builds a cobra.Command pre-wired with the flags
// ImFeedShortcutCreate registers at runtime. Mirrors the helper used by other
// shortcut tests so tests can exercise the typed Bool/StrSlice accessors.
func newFeedShortcutCreateCmd(t *testing.T) *cobra.Command {
	t.Helper()
	cmd := &cobra.Command{Use: "test"}
	cmd.Flags().StringSlice("chat-id", nil, "")
	cmd.Flags().Bool("head", false, "")
	cmd.Flags().Bool("tail", false, "")
	if err := cmd.ParseFlags(nil); err != nil {
		t.Fatalf("ParseFlags() error = %v", err)
	}
	return cmd
}

func newFeedShortcutRemoveCmd(t *testing.T) *cobra.Command {
	t.Helper()
	cmd := &cobra.Command{Use: "test"}
	cmd.Flags().StringSlice("chat-id", nil, "")
	if err := cmd.ParseFlags(nil); err != nil {
		t.Fatalf("ParseFlags() error = %v", err)
	}
	return cmd
}

func newFeedShortcutListCmd(t *testing.T) *cobra.Command {
	t.Helper()
	cmd := &cobra.Command{Use: "test"}
	if err := cmd.ParseFlags(nil); err != nil {
		t.Fatalf("ParseFlags() error = %v", err)
	}
	return cmd
}

func TestCollectChatIDs(t *testing.T) {
	tests := []struct {
		name      string
		input     []string
		want      []string
		wantErr   bool
		errSubstr string
	}{
		{name: "single id", input: []string{"oc_abc"}, want: []string{"oc_abc"}},
		{name: "two repeated flags", input: []string{"oc_abc", "oc_def"}, want: []string{"oc_abc", "oc_def"}},
		// StringSlice handles comma splitting itself, but extra whitespace and
		// duplicates should still be normalized inside collectChatIDs.
		{name: "trims whitespace", input: []string{" oc_abc ", "oc_def"}, want: []string{"oc_abc", "oc_def"}},
		{name: "dedupes", input: []string{"oc_abc", "oc_abc", "oc_def"}, want: []string{"oc_abc", "oc_def"}},
		{name: "rejects empty list", input: nil, wantErr: true, errSubstr: "--chat-id is required"},
		{name: "rejects bad prefix", input: []string{"om_abc"}, wantErr: true, errSubstr: "must be an open_chat_id"},
		{
			name: "accepts limit boundary",
			input: []string{
				"oc_1", "oc_2", "oc_3", "oc_4", "oc_5", "oc_6", "oc_7", "oc_8", "oc_9", "oc_10",
				"oc_11", "oc_12", "oc_13", "oc_14", "oc_15", "oc_16", "oc_17", "oc_18", "oc_19", "oc_20",
				"oc_21", "oc_22", "oc_23", "oc_24", "oc_25", "oc_26", "oc_27", "oc_28", "oc_29", "oc_30",
			},
			want: []string{
				"oc_1", "oc_2", "oc_3", "oc_4", "oc_5", "oc_6", "oc_7", "oc_8", "oc_9", "oc_10",
				"oc_11", "oc_12", "oc_13", "oc_14", "oc_15", "oc_16", "oc_17", "oc_18", "oc_19", "oc_20",
				"oc_21", "oc_22", "oc_23", "oc_24", "oc_25", "oc_26", "oc_27", "oc_28", "oc_29", "oc_30",
			},
		},
		{
			name: "rejects over limit",
			input: []string{
				"oc_1", "oc_2", "oc_3", "oc_4", "oc_5", "oc_6", "oc_7", "oc_8", "oc_9", "oc_10",
				"oc_11", "oc_12", "oc_13", "oc_14", "oc_15", "oc_16", "oc_17", "oc_18", "oc_19", "oc_20",
				"oc_21", "oc_22", "oc_23", "oc_24", "oc_25", "oc_26", "oc_27", "oc_28", "oc_29", "oc_30",
				"oc_31",
			},
			wantErr:   true,
			errSubstr: "too many --chat-id",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cmd := newFeedShortcutCreateCmd(t)
			for _, v := range tt.input {
				if err := cmd.Flags().Set("chat-id", v); err != nil {
					t.Fatalf("Set chat-id %q error = %v", v, err)
				}
			}
			runtime := &common.RuntimeContext{Cmd: cmd}

			got, err := collectChatIDs(runtime)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("collectChatIDs() expected error, got nil")
				}
				if tt.errSubstr != "" && !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("collectChatIDs() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("collectChatIDs() unexpected error: %v", err)
			}
			if strings.Join(got, ",") != strings.Join(tt.want, ",") {
				t.Fatalf("collectChatIDs() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestBuildShortcutItems(t *testing.T) {
	got := buildShortcutItems([]string{"oc_a", "oc_b"})
	if len(got) != 2 {
		t.Fatalf("buildShortcutItems() len = %d, want 2", len(got))
	}
	for i, it := range got {
		if it.Type != int(ShortcutTypeChat) {
			t.Fatalf("item %d type = %d, want %d", i, it.Type, ShortcutTypeChat)
		}
	}
	if got[0].FeedCardID != "oc_a" || got[1].FeedCardID != "oc_b" {
		t.Fatalf("buildShortcutItems() ids = %+v, want oc_a,oc_b", got)
	}
}

func TestShortcutFailedReasonString(t *testing.T) {
	tests := []struct {
		reason int
		want   string
	}{
		{0, "unknown"},
		{1, "no_permission"},
		{2, "invalid_item"},
		{3, "has_pending_delete"},
		{4, "type_not_support"},
		{5, "internal_error"},
		{99, "unknown"},
	}
	for _, tt := range tests {
		if got := shortcutFailedReasonString(tt.reason); got != tt.want {
			t.Fatalf("shortcutFailedReasonString(%d) = %q, want %q", tt.reason, got, tt.want)
		}
	}
}

func TestAnnotateFailedShortcuts(t *testing.T) {
	data := map[string]any{
		"failed_shortcuts": []any{
			map[string]any{"reason": float64(1)},
			map[string]any{"reason": float64(4)},
			map[string]any{"other": "field"}, // no reason field — should be left alone
		},
	}
	annotateFailedShortcuts(data)

	items := data["failed_shortcuts"].([]any)
	if got := items[0].(map[string]any)["reason_label"]; got != "no_permission" {
		t.Fatalf("item 0 reason_label = %v, want no_permission", got)
	}
	if got := items[1].(map[string]any)["reason_label"]; got != "type_not_support" {
		t.Fatalf("item 1 reason_label = %v, want type_not_support", got)
	}
	if _, ok := items[2].(map[string]any)["reason_label"]; ok {
		t.Fatalf("item 2 should not have reason_label set")
	}
}

func TestHasFailedShortcuts(t *testing.T) {
	if hasFailedShortcuts(map[string]any{}) {
		t.Fatalf("missing failed_shortcuts should not count as failure")
	}
	if hasFailedShortcuts(map[string]any{"failed_shortcuts": []any{}}) {
		t.Fatalf("empty failed_shortcuts should not count as failure")
	}
	if !hasFailedShortcuts(map[string]any{"failed_shortcuts": []any{map[string]any{"reason": float64(2)}}}) {
		t.Fatalf("non-empty failed_shortcuts should count as failure")
	}
}

func TestAddFeedShortcutWriteLedger(t *testing.T) {
	data := map[string]any{
		"failed_shortcuts": []any{
			map[string]any{
				"reason": float64(2),
				"shortcut": map[string]any{
					"feed_card_id": "oc_b",
					"type":         float64(1),
				},
			},
		},
	}
	addFeedShortcutWriteLedger(data, []shortcutItem{
		{FeedCardID: "oc_a", Type: int(ShortcutTypeChat)},
		{FeedCardID: "oc_b", Type: int(ShortcutTypeChat)},
	})

	if data["total"] != 2 || data["success_count"] != 1 || data["failure_count"] != 1 {
		t.Fatalf("ledger counts = total:%v success:%v failure:%v",
			data["total"], data["success_count"], data["failure_count"])
	}
	succeeded := data["succeeded_shortcuts"].([]shortcutItem)
	if len(succeeded) != 1 || succeeded[0].FeedCardID != "oc_a" {
		t.Fatalf("succeeded_shortcuts = %+v, want only oc_a", succeeded)
	}
}

func TestAddFeedShortcutWriteLedgerFailedEchoMissingType(t *testing.T) {
	// A failed echo whose shortcut omits `type` (or sends 0) must still
	// exclude its item from the success list: matching is by feed_card_id
	// alone, so the ledger invariant success+failure==total holds.
	data := map[string]any{
		"failed_shortcuts": []any{
			map[string]any{
				"reason":   float64(4),
				"shortcut": map[string]any{"feed_card_id": "oc_b"},
			},
		},
	}
	addFeedShortcutWriteLedger(data, []shortcutItem{
		{FeedCardID: "oc_a", Type: int(ShortcutTypeChat)},
		{FeedCardID: "oc_b", Type: int(ShortcutTypeChat)},
	})

	if data["total"] != 2 || data["success_count"] != 1 || data["failure_count"] != 1 {
		t.Fatalf("ledger counts = total:%v success:%v failure:%v, want 2/1/1",
			data["total"], data["success_count"], data["failure_count"])
	}
	succeeded := data["succeeded_shortcuts"].([]shortcutItem)
	if len(succeeded) != 1 || succeeded[0].FeedCardID != "oc_a" {
		t.Fatalf("succeeded_shortcuts = %+v, want only oc_a", succeeded)
	}
}

func TestAddFeedShortcutWriteLedgerDuplicateFailedEcho(t *testing.T) {
	// A server that echoes the same failed shortcut twice must not break the
	// success+failure==total invariant: counts derive from requested-item
	// accounting, while failed_shortcuts keeps the raw (duplicated) report.
	dup := map[string]any{
		"reason":   float64(2),
		"shortcut": map[string]any{"feed_card_id": "oc_b", "type": float64(1)},
	}
	data := map[string]any{"failed_shortcuts": []any{dup, dup}}
	addFeedShortcutWriteLedger(data, []shortcutItem{
		{FeedCardID: "oc_a", Type: int(ShortcutTypeChat)},
		{FeedCardID: "oc_b", Type: int(ShortcutTypeChat)},
	})

	if data["total"] != 2 || data["success_count"] != 1 || data["failure_count"] != 1 {
		t.Fatalf("ledger counts = total:%v success:%v failure:%v, want 2/1/1",
			data["total"], data["success_count"], data["failure_count"])
	}
}

func TestAnnotateFailedShortcutsNoOpWhenMissing(t *testing.T) {
	// Must not panic when failed_shortcuts is missing or wrong type.
	annotateFailedShortcuts(map[string]any{})
	annotateFailedShortcuts(map[string]any{"failed_shortcuts": "not-a-list"})
}

func TestResolveIsHeader(t *testing.T) {
	tests := []struct {
		name    string
		head    bool
		tail    bool
		want    bool
		wantErr bool
	}{
		{name: "default is head", want: true},
		{name: "--head explicit", head: true, want: true},
		{name: "--tail", tail: true, want: false},
		{name: "both set errors", head: true, tail: true, wantErr: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cmd := newFeedShortcutCreateCmd(t)
			if tt.head {
				if err := cmd.Flags().Set("head", "true"); err != nil {
					t.Fatalf("Set head error = %v", err)
				}
			}
			if tt.tail {
				if err := cmd.Flags().Set("tail", "true"); err != nil {
					t.Fatalf("Set tail error = %v", err)
				}
			}
			rt := &common.RuntimeContext{Cmd: cmd}
			got, err := resolveIsHeader(rt)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("resolveIsHeader() expected error, got nil")
				}
				return
			}
			if err != nil {
				t.Fatalf("resolveIsHeader() unexpected error: %v", err)
			}
			if got != tt.want {
				t.Fatalf("resolveIsHeader() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestFeedShortcutStaticScopes(t *testing.T) {
	if got := ImFeedShortcutCreate.ScopesForIdentity("user"); len(got) != 1 || got[0] != feedShortcutWriteScope {
		t.Fatalf("ImFeedShortcutCreate scopes = %v, want only %s", got, feedShortcutWriteScope)
	}
	if got := ImFeedShortcutRemove.ScopesForIdentity("user"); len(got) != 1 || got[0] != feedShortcutWriteScope {
		t.Fatalf("ImFeedShortcutRemove scopes = %v, want only %s", got, feedShortcutWriteScope)
	}
	if got := ImFeedShortcutList.ScopesForIdentity("user"); len(got) != 1 || got[0] != feedShortcutReadScope {
		t.Fatalf("ImFeedShortcutList scopes = %v, want only %s", got, feedShortcutReadScope)
	}
}

func TestFeedShortcutAuthTypesUserOnly(t *testing.T) {
	for _, sc := range []common.Shortcut{ImFeedShortcutCreate, ImFeedShortcutRemove, ImFeedShortcutList} {
		if len(sc.AuthTypes) != 1 || sc.AuthTypes[0] != "user" {
			t.Fatalf("shortcut %s AuthTypes = %v, want [user]", sc.Command, sc.AuthTypes)
		}
	}
}

func TestImFeedShortcutCreateDryRunReportsValidationError(t *testing.T) {
	cmd := newFeedShortcutCreateCmd(t)
	// no chat-id set → validation error surfaced in DryRun output
	rt := &common.RuntimeContext{Cmd: cmd}
	got := ImFeedShortcutCreate.DryRun(context.Background(), rt).Format()
	if !strings.Contains(got, "--chat-id is required") {
		t.Fatalf("DryRun output = %q, want validation error", got)
	}
	if strings.Contains(got, "feed_shortcuts") {
		t.Fatalf("DryRun output = %q, should not include request for invalid input", got)
	}
}

func TestImFeedShortcutCreateDryRunRendersBody(t *testing.T) {
	cmd := newFeedShortcutCreateCmd(t)
	if err := cmd.Flags().Set("chat-id", "oc_abc"); err != nil {
		t.Fatalf("Set chat-id error = %v", err)
	}
	if err := cmd.Flags().Set("chat-id", "oc_def"); err != nil {
		t.Fatalf("Set chat-id error = %v", err)
	}
	if err := cmd.Flags().Set("tail", "true"); err != nil {
		t.Fatalf("Set tail error = %v", err)
	}
	rt := &common.RuntimeContext{Cmd: cmd}
	got := ImFeedShortcutCreate.DryRun(context.Background(), rt).Format()
	for _, want := range []string{
		"POST",
		"/open-apis/im/v2/feed_shortcuts",
		`"feed_card_id"`,
		"oc_abc",
		"oc_def",
		`"is_header"`,
		`false`,
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("DryRun output = %s, want %q", got, want)
		}
	}
}

func TestImFeedShortcutCreateExecuteCallsAPI(t *testing.T) {
	var gotBody []byte
	var gotPath string
	rt := newUserShortcutRuntime(t, shortcutRoundTripFunc(func(req *http.Request) (*http.Response, error) {
		if !strings.Contains(req.URL.Path, "/open-apis/im/v2/feed_shortcuts") {
			return nil, fmt.Errorf("unexpected request: %s", req.URL.Path)
		}
		// Reject the remove suffix — confirms create uses the bare path.
		if strings.HasSuffix(req.URL.Path, "/remove") {
			return nil, fmt.Errorf("create should not call /remove: %s", req.URL.Path)
		}
		body, _ := io.ReadAll(req.Body)
		gotBody = body
		gotPath = req.URL.Path
		return shortcutJSONResponse(200, map[string]any{
			"code": 0,
			"data": map[string]any{
				"failed_shortcuts": []any{
					map[string]any{
						"reason": float64(2),
						"shortcut": map[string]any{
							"feed_card_id": "oc_abc",
							"type":         float64(1),
						},
					},
				},
			},
		}), nil
	}))

	cmd := newFeedShortcutCreateCmd(t)
	if err := cmd.Flags().Set("chat-id", "oc_abc"); err != nil {
		t.Fatalf("Set chat-id error = %v", err)
	}
	setRuntimeField(t, rt, "Cmd", cmd)

	err := ImFeedShortcutCreate.Execute(context.Background(), rt)
	var pfErr *output.PartialFailureError
	if !errors.As(err, &pfErr) {
		t.Fatalf("Execute() error = %T %v, want partial failure", err, err)
	}
	// Lock the documented exit-code contract: partial failure exits 1 (ExitAPI).
	if pfErr.Code != output.ExitAPI {
		t.Fatalf("partial failure exit code = %d, want %d (ExitAPI)", pfErr.Code, output.ExitAPI)
	}
	if !strings.HasSuffix(gotPath, "/open-apis/im/v2/feed_shortcuts") {
		t.Fatalf("Execute() path = %q, want /open-apis/im/v2/feed_shortcuts", gotPath)
	}
	if !strings.Contains(string(gotBody), `"feed_card_id":"oc_abc"`) {
		t.Fatalf("Execute() body = %s, want feed_card_id oc_abc", gotBody)
	}
	if !strings.Contains(string(gotBody), `"is_header":true`) {
		t.Fatalf("Execute() body = %s, want is_header true (default)", gotBody)
	}

	out := rt.Factory.IOStreams.Out.(interface{ String() string }).String()
	if !strings.Contains(out, `"ok": false`) {
		t.Fatalf("stdout = %s, want ok:false partial-failure envelope", out)
	}
	for _, want := range []string{
		`"total": 1`,
		`"success_count": 0`,
		`"failure_count": 1`,
		`"succeeded_shortcuts": []`,
		`"reason_label": "invalid_item"`,
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("stdout = %s, want %q", out, want)
		}
	}
}

func TestEmitFeedShortcutWriteResultSuccess(t *testing.T) {
	rt := newUserShortcutRuntime(t, shortcutRoundTripFunc(func(req *http.Request) (*http.Response, error) {
		t.Fatalf("must not call API")
		return nil, nil
	}))
	setRuntimeField(t, rt, "Cmd", newFeedShortcutCreateCmd(t))
	err := emitFeedShortcutWriteResult(rt, []shortcutItem{
		{FeedCardID: "oc_a", Type: int(ShortcutTypeChat)},
	}, map[string]any{"failed_shortcuts": []any{}})
	if err != nil {
		t.Fatalf("emitFeedShortcutWriteResult() error = %v, want nil", err)
	}
	out := rt.Factory.IOStreams.Out.(interface{ String() string }).String()
	for _, want := range []string{
		`"ok": true`,
		`"total": 1`,
		`"success_count": 1`,
		`"failure_count": 0`,
		`"feed_card_id": "oc_a"`,
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("stdout = %s, want %q", out, want)
		}
	}
}

func TestEmitFeedShortcutWriteResultNilData(t *testing.T) {
	// A fully-successful write can come back as code:0 with data:null, which
	// DoAPIJSON surfaces as a nil map. The emitter must still produce the
	// ledger instead of panicking on a nil-map write.
	rt := newUserShortcutRuntime(t, shortcutRoundTripFunc(func(req *http.Request) (*http.Response, error) {
		t.Fatalf("must not call API")
		return nil, nil
	}))
	setRuntimeField(t, rt, "Cmd", newFeedShortcutCreateCmd(t))
	err := emitFeedShortcutWriteResult(rt, []shortcutItem{
		{FeedCardID: "oc_a", Type: int(ShortcutTypeChat)},
	}, nil)
	if err != nil {
		t.Fatalf("emitFeedShortcutWriteResult(nil data) error = %v, want nil", err)
	}
	out := rt.Factory.IOStreams.Out.(interface{ String() string }).String()
	for _, want := range []string{
		`"ok": true`,
		`"total": 1`,
		`"success_count": 1`,
		`"failure_count": 0`,
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("stdout = %s, want %q", out, want)
		}
	}
}

func TestImFeedShortcutRemoveExecuteCallsRemovePath(t *testing.T) {
	var gotPath string
	var gotBody []byte
	rt := newUserShortcutRuntime(t, shortcutRoundTripFunc(func(req *http.Request) (*http.Response, error) {
		if !strings.Contains(req.URL.Path, "/open-apis/im/v2/feed_shortcuts/remove") {
			return nil, fmt.Errorf("unexpected request: %s", req.URL.Path)
		}
		body, _ := io.ReadAll(req.Body)
		gotBody = body
		gotPath = req.URL.Path
		return shortcutJSONResponse(200, map[string]any{
			"code": 0,
			"data": map[string]any{"failed_shortcuts": []any{}},
		}), nil
	}))

	cmd := newFeedShortcutRemoveCmd(t)
	if err := cmd.Flags().Set("chat-id", "oc_abc,oc_def"); err != nil {
		t.Fatalf("Set chat-id error = %v", err)
	}
	setRuntimeField(t, rt, "Cmd", cmd)

	if err := ImFeedShortcutRemove.Execute(context.Background(), rt); err != nil {
		t.Fatalf("Execute() error = %v", err)
	}
	if !strings.HasSuffix(gotPath, "/open-apis/im/v2/feed_shortcuts/remove") {
		t.Fatalf("Execute() path = %q, want /open-apis/im/v2/feed_shortcuts/remove", gotPath)
	}
	if !strings.Contains(string(gotBody), `"feed_card_id":"oc_abc"`) {
		t.Fatalf("Execute() body = %s, want feed_card_id oc_abc", gotBody)
	}
	if !strings.Contains(string(gotBody), `"feed_card_id":"oc_def"`) {
		t.Fatalf("Execute() body = %s, want feed_card_id oc_def", gotBody)
	}
	// Remove must not send is_header — that's a create-only field.
	if strings.Contains(string(gotBody), "is_header") {
		t.Fatalf("Execute() body = %s, should NOT contain is_header", gotBody)
	}
}

func TestImFeedShortcutListDryRunRendersGet(t *testing.T) {
	cmd := newFeedShortcutListCmd(t)
	rt := &common.RuntimeContext{Cmd: cmd}
	got := ImFeedShortcutList.DryRun(context.Background(), rt).Format()
	for _, want := range []string{
		"GET",
		"/open-apis/im/v2/feed_shortcuts",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("DryRun output = %s, want %q", got, want)
		}
	}
}

func TestImFeedShortcutListHasNoCustomFlags(t *testing.T) {
	if len(ImFeedShortcutList.Flags) != 0 {
		t.Fatalf("ImFeedShortcutList.Flags = %v, want no shortcut-specific flags", ImFeedShortcutList.Flags)
	}
}

func TestImFeedShortcutListHelpShowsNoLegacyFlags(t *testing.T) {
	f, _, _, _ := cmdutil.TestFactory(t, &core.CliConfig{
		AppID: "app", AppSecret: "secret", Brand: core.BrandFeishu,
	})
	parent := &cobra.Command{Use: "im"}
	ImFeedShortcutList.Mount(parent, f)

	cmd, _, err := parent.Find([]string{"+feed-shortcut-list"})
	if err != nil {
		t.Fatalf("Find() error = %v", err)
	}
	var out bytes.Buffer
	cmd.SetOut(&out)
	cmd.SetErr(&out)
	if err := cmd.Help(); err != nil {
		t.Fatalf("Help() error = %v", err)
	}
	got := out.String()
	for _, banned := range []string{"--no-detail", "--page-token"} {
		if strings.Contains(got, banned) {
			t.Fatalf("help output should not mention legacy flag %s:\n%s", banned, got)
		}
	}
}

func TestFeedShortcutChatIDNotCobraRequired(t *testing.T) {
	// --chat-id is mandatory, but must NOT be cobra-Required: cobra would
	// intercept a missing flag before Validate runs and emit a plain-text
	// "required flag(s) not set" error (exit 1) instead of collectChatIDs'
	// structured validation envelope (exit 2).
	for _, sc := range []common.Shortcut{ImFeedShortcutCreate, ImFeedShortcutRemove} {
		for _, fl := range sc.Flags {
			if fl.Name == "chat-id" && fl.Required {
				t.Fatalf("%s: --chat-id must not be cobra-Required; requiredness is enforced by collectChatIDs", sc.Command)
			}
		}
	}
}

func TestImFeedShortcutListExecuteRequestsFullList(t *testing.T) {
	var calls int
	var rawQuery string
	rt := newUserShortcutRuntime(t, shortcutRoundTripFunc(func(req *http.Request) (*http.Response, error) {
		if !strings.Contains(req.URL.Path, "/open-apis/im/v2/feed_shortcuts") {
			return nil, fmt.Errorf("unexpected request: %s", req.URL.Path)
		}
		calls++
		rawQuery = req.URL.RawQuery
		return shortcutJSONResponse(200, map[string]any{
			"code": 0,
			"data": map[string]any{
				"shortcuts": []any{
					map[string]any{"feed_card_id": "oc_a", "type": float64(1)},
				},
			},
		}), nil
	}))

	cmd := newFeedShortcutListCmd(t)
	setRuntimeField(t, rt, "Cmd", cmd)

	if err := ImFeedShortcutList.Execute(context.Background(), rt); err != nil {
		t.Fatalf("Execute() error = %v", err)
	}
	if calls != 1 {
		t.Fatalf("expected 1 API call, got %d", calls)
	}
	if rawQuery != "" {
		t.Fatalf("request query = %q, want empty query string", rawQuery)
	}
	stdout := rt.Factory.IOStreams.Out.(interface{ String() string }).String()
	for _, want := range []string{`"feed_card_id": "oc_a"`, `"type": 1`} {
		if !strings.Contains(stdout, want) {
			t.Fatalf("stdout = %s, want %q", stdout, want)
		}
	}
	for _, banned := range []string{`"detail"`, `"_notice"`, `"page_token"`, `"has_more"`} {
		if strings.Contains(stdout, banned) {
			t.Fatalf("stdout should not contain legacy field %s; got:\n%s", banned, stdout)
		}
	}
}
