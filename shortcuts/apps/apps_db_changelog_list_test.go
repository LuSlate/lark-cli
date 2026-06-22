// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/larksuite/cli/internal/httpmock"
)

const dbChangelogURL = "/open-apis/spark/v1/apps/app_x/db/changelog_list"

func TestAppsDBChangelogList_RequiresAppID(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsDBChangelogList,
		[]string{"+db-changelog-list", "--app-id", "  ", "--as", "user"}, factory, stdout)
	if err == nil || !strings.Contains(err.Error(), "app-id") {
		t.Fatalf("expected app-id error, got %v", err)
	}
}

func TestAppsDBChangelogList_DryRunFiltersAndTimeNormalize(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	if err := runAppsShortcut(t, AppsDBChangelogList,
		[]string{"+db-changelog-list", "--app-id", "app_x", "--env", "dev", "--table", "orders",
			"--change-id", "01J", "--since", "2026-01-01", "--page-size", "5", "--dry-run", "--as", "user"}, factory, stdout); err != nil {
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
	a := env.API[0]
	if a.Method != "GET" || a.URL != dbChangelogURL {
		t.Fatalf("dry-run = %s %s", a.Method, a.URL)
	}
	if a.Params["env"] != "dev" || a.Params["table"] != "orders" || a.Params["change_id"] != "01J" {
		t.Fatalf("params = %v", a.Params)
	}
	if s, _ := a.Params["since"].(string); !strings.HasSuffix(s, "Z") {
		t.Fatalf("since not normalized to RFC3339 UTC: %v", a.Params["since"])
	}
}

func TestAppsDBChangelogList_RejectsBadSince(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsDBChangelogList,
		[]string{"+db-changelog-list", "--app-id", "app_x", "--since", "notatime", "--as", "user"}, factory, stdout)
	if err == nil || !strings.Contains(err.Error(), "since") {
		t.Fatalf("expected --since validation, got %v", err)
	}
}

func TestAppsDBChangelogList_SuccessParsesOperator(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "GET", URL: dbChangelogURL,
		Body: map[string]interface{}{"code": 0, "data": map[string]interface{}{
			"has_more": false, "page_token": "",
			"items": []interface{}{map[string]interface{}{
				"change_id": "01J", "changed_at": "2026-04-15T10:30:00Z",
				"operator": `{"id":"7311","name":"alice"}`, "target_table": "orders",
				"change_type": "ALTER_TABLE", "summary": "add column", "statement": "ALTER TABLE orders ...",
			}},
		}},
	})
	if err := runAppsShortcut(t, AppsDBChangelogList,
		[]string{"+db-changelog-list", "--app-id", "app_x", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	got := stdout.String()
	for _, want := range []string{`"operator"`, `"name": "alice"`, `"id": "7311"`, `"change_type": "ALTER_TABLE"`, `"statement"`} {
		if !strings.Contains(got, want) {
			t.Errorf("missing %q:\n%s", want, got)
		}
	}
}

func TestAppsDBChangelogList_ChangeIDNotFoundPretty(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "GET", URL: dbChangelogURL,
		Body: map[string]interface{}{"code": 0, "data": map[string]interface{}{"items": []interface{}{}}},
	})
	if err := runAppsShortcut(t, AppsDBChangelogList,
		[]string{"+db-changelog-list", "--app-id", "app_x", "--change-id", "nope", "--format", "pretty", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	if !strings.Contains(stdout.String(), "No DDL change with id=nope found.") {
		t.Fatalf("expected not-found message, got: %s", stdout.String())
	}
}

func TestParseOperator_Cases(t *testing.T) {
	if op := parseOperator(`{"id":"1","name":"a"}`); op == nil || op.ID != "1" || op.Name != "a" {
		t.Fatalf("valid: %#v", op)
	}
	if op := parseOperator(`{"id":"1","name":""}`); op == nil || op.Name != "1" {
		t.Fatalf("name fallback to id: %#v", op)
	}
	if op := parseOperator("plain-user"); op == nil || op.ID != "plain-user" || op.Name != "plain-user" {
		t.Fatalf("non-json raw: %#v", op)
	}
	if op := parseOperator(""); op != nil {
		t.Fatalf("empty → nil, got %#v", op)
	}
	if operatorName(nil) != "—" {
		t.Fatalf("nil operatorName should be —")
	}
}

func TestSafeParseJSON_Cases(t *testing.T) {
	if v := safeParseJSON(`{"a":1}`); v == nil {
		t.Fatalf("valid json → object")
	}
	if v, ok := safeParseJSON("not json").(string); !ok || v != "not json" {
		t.Fatalf("invalid json → raw string, got %v", v)
	}
}
