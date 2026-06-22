// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/larksuite/cli/internal/httpmock"
)

const fileGetURL = "/open-apis/spark/v1/apps/app_x/storage/file"

func TestAppsFileGet_RequiresAppIDAndPath(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	if err := runAppsShortcut(t, AppsFileGet,
		[]string{"+file-get", "--app-id", "  ", "--path", "/x.png", "--as", "user"}, factory, stdout); err == nil || !strings.Contains(err.Error(), "app-id") {
		t.Fatalf("expected app-id error, got %v", err)
	}
	factory2, stdout2, _ := newAppsExecuteFactory(t)
	if err := runAppsShortcut(t, AppsFileGet,
		[]string{"+file-get", "--app-id", "app_x", "--path", "  ", "--as", "user"}, factory2, stdout2); err == nil || !strings.Contains(err.Error(), "path") {
		t.Fatalf("expected path error, got %v", err)
	}
}

func TestAppsFileGet_DryRunSendsPathQuery(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	if err := runAppsShortcut(t, AppsFileGet,
		[]string{"+file-get", "--app-id", "app_x", "--path", "/x.png", "--dry-run", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("dry-run err=%v", err)
	}
	var env struct {
		API []struct {
			Method string                 `json:"method"`
			URL    string                 `json:"url"`
			Params map[string]interface{} `json:"params"`
		} `json:"api"`
	}
	_ = json.Unmarshal([]byte(stdout.String()), &env)
	if env.API[0].Method != "GET" || env.API[0].URL != fileGetURL || env.API[0].Params["path"] != "/x.png" {
		t.Fatalf("dry-run = %s %s params=%v", env.API[0].Method, env.API[0].URL, env.API[0].Params)
	}
}

func TestAppsFileGet_SuccessAndPrettyKeyValue(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "GET", URL: fileGetURL,
		Body: map[string]interface{}{"code": 0, "data": map[string]interface{}{
			"file_name": "logo.png", "path": "/1858537546760216.png",
			"size_bytes": 24580, "type": "image/png",
			"created_at": "2026-04-15T10:30:00Z",
			"created_by": `{"id":"7311","name":"alice"}`,
		}},
	})
	if err := runAppsShortcut(t, AppsFileGet,
		[]string{"+file-get", "--app-id", "app_x", "--path", "/1858537546760216.png", "--format", "pretty", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	got := stdout.String()
	// pretty key/value：size 含 bytes、uploaded_by 只展示 name。
	for _, want := range []string{"file_name:", "24 KB (24580 bytes)", "uploaded_by: alice", "uploaded_at: 2026-04-15T10:30:00Z"} {
		if !strings.Contains(got, want) {
			t.Errorf("pretty missing %q:\n%s", want, got)
		}
	}
	// pretty 不该泄漏 user id。
	if strings.Contains(got, "7311") {
		t.Errorf("pretty should show name only, not id:\n%s", got)
	}
}
