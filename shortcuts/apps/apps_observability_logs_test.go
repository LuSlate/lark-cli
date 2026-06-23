// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/larksuite/cli/internal/httpmock"
)

func TestAppsLogList_DryRunBuildsSearchLogsBody(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsLogList, []string{
		"+log-list", "--app-id", "app_x", "--level", "error",
		"--log-id", "LOG1", "--log-id", "LOG2", "--trace-id", "trace-1",
		"--keyword", "timeout", "--min-duration", "200",
		"--page-size", "20", "--dry-run", "--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("dry-run err=%v", err)
	}
	var env struct {
		API []struct {
			Method string                 `json:"method"`
			URL    string                 `json:"url"`
			Body   map[string]interface{} `json:"body"`
		} `json:"api"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode dry-run: %v\n%s", err, stdout.String())
	}
	if env.API[0].Method != "POST" || env.API[0].URL != "/open-apis/spark/v1/apps/app_x/search_logs" {
		t.Fatalf("method/url = %s %s", env.API[0].Method, env.API[0].URL)
	}
	if env.API[0].Body["app_env"] != "online" || env.API[0].Body["limit"] != float64(20) {
		t.Fatalf("body = %#v", env.API[0].Body)
	}
	filter := env.API[0].Body["filter"].(map[string]interface{})
	if got := filter["keyword"]; got != "timeout" {
		t.Fatalf("filter.keyword = %v", got)
	}
}

func TestAppsLogList_RejectsDevEnv(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsLogList, []string{"+log-list", "--app-id", "app_x", "--env", "dev", "--as", "user"}, factory, stdout)
	requireAppsValidationParam(t, err, "--env")
}

func TestAppsLogGet_SearchesByLogIDLimitOne(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	stub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/search_logs",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"log_items": []interface{}{
					map[string]interface{}{"log_id": "LOG1", "level": "INFO"},
				},
			},
		},
	}
	reg.Register(stub)
	if err := runAppsShortcut(t, AppsLogGet, []string{"+log-get", "--app-id", "app_x", "--log-id", "LOG1", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	var sent map[string]interface{}
	if err := json.Unmarshal(stub.CapturedBody, &sent); err != nil {
		t.Fatal(err)
	}
	if sent["limit"] != float64(1) {
		t.Fatalf("limit = %v, want 1", sent["limit"])
	}
}

func TestAppsLogList_NormalizesResponseVariantsAndCanonicalLevel(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/search_logs",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"logItems": []interface{}{
					map[string]interface{}{
						"id":           "LOG1",
						"traceID":      "trace-1",
						"timestampNs":  "1782209472123456789",
						"severityText": "ERROR",
					},
				},
				"nextPageToken": "tok-next",
				"hasMore":       true,
			},
		},
	})

	if err := runAppsShortcut(t, AppsLogList, []string{"+log-list", "--app-id", "app_x", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}

	var env struct {
		Data struct {
			Items     []map[string]interface{} `json:"items"`
			PageToken string                   `json:"page_token"`
			HasMore   bool                     `json:"has_more"`
		} `json:"data"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode output: %v\n%s", err, stdout.String())
	}
	if env.Data.PageToken != "tok-next" || !env.Data.HasMore {
		t.Fatalf("pagination = token %q has_more %v", env.Data.PageToken, env.Data.HasMore)
	}
	if len(env.Data.Items) != 1 {
		t.Fatalf("items len = %d", len(env.Data.Items))
	}
	item := env.Data.Items[0]
	if item["level"] != "ERROR" || item["severity_text"] != "ERROR" || item["severityText"] != "ERROR" {
		t.Fatalf("level fields = %#v", item)
	}
}

func TestAppsLogGet_ResolvesSourceStackWhenFieldsPresent(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	search := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/search_logs",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"log_items": []interface{}{
					map[string]interface{}{
						"log_id": "LOG1",
						"level":  "ERROR",
						"attributes": map[string]interface{}{
							"commit_id":              "commit_1",
							"source_map_file_prefix": "sourcemaps/app",
							"frames": []interface{}{
								map[string]interface{}{"file": "main.js", "line": 10, "column": 20},
							},
						},
					},
				},
			},
		},
	}
	resolve := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/resolve_stack_trace",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"source_stack": []interface{}{
					map[string]interface{}{"file": "src/App.tsx", "line": 7, "column": 9},
				},
			},
		},
	}
	reg.Register(search)
	reg.Register(resolve)

	if err := runAppsShortcut(t, AppsLogGet, []string{"+log-get", "--app-id", "app_x", "--log-id", "LOG1", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	var sent map[string]interface{}
	if err := json.Unmarshal(resolve.CapturedBody, &sent); err != nil {
		t.Fatal(err)
	}
	if sent["commit_id"] != "commit_1" || sent["source_map_file_prefix"] != "sourcemaps/app" {
		t.Fatalf("resolve body missing source map fields: %#v", sent)
	}
	frames, ok := sent["frames"].([]interface{})
	if !ok || len(frames) != 1 {
		t.Fatalf("resolve frames = %#v", sent["frames"])
	}
	if got := stdout.String(); !strings.Contains(got, `"source_stack_status": "resolved"`) || !strings.Contains(got, "src/App.tsx") {
		t.Fatalf("stdout missing resolved source stack: %s", got)
	}
}

func TestAppsLogGet_SourceStackMissingFieldsDoesNotFail(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	search := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/search_logs",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"log_items": []interface{}{
					map[string]interface{}{
						"log_id":     "LOG1",
						"level":      "ERROR",
						"message":    "TypeError at https://cdn.example.com/main.js:10:20",
						"attributes": map[string]interface{}{"commit_id": "commit_1"},
					},
				},
			},
		},
	}
	reg.Register(search)

	if err := runAppsShortcut(t, AppsLogGet, []string{"+log-get", "--app-id", "app_x", "--log-id", "LOG1", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	if got := stdout.String(); !strings.Contains(got, `"log_id": "LOG1"`) {
		t.Fatalf("stdout missing original log: %s", got)
	} else if !strings.Contains(got, `"source_stack_status": "unresolved"`) {
		t.Fatalf("stdout missing unresolved source stack status: %s", got)
	} else if !strings.Contains(got, `"source_stack_reason"`) {
		t.Fatalf("stdout missing sanitized source stack reason: %s", got)
	}
	for _, banned := range []string{"secret", "token", "raw request payload"} {
		if strings.Contains(strings.ToLower(stdout.String()), banned) {
			t.Fatalf("stdout leaked %q: %s", banned, stdout.String())
		}
	}
}

func TestAppsLogGet_ErrorNonFrontendMissingFieldsDoesNotMarkUnresolved(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/search_logs",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"log_items": []interface{}{
					map[string]interface{}{
						"log_id":  "LOG1",
						"level":   "ERROR",
						"message": "go stack trace: database query failed",
					},
				},
			},
		},
	})

	if err := runAppsShortcut(t, AppsLogGet, []string{"+log-get", "--app-id", "app_x", "--log-id", "LOG1", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	if got := stdout.String(); strings.Contains(got, "source_stack_status") {
		t.Fatalf("non-frontend error log should not be marked unresolved: %s", got)
	}
}

func TestAppsLogGet_SourceStackResolveFailureIsRedacted(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	search := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/search_logs",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"log_items": []interface{}{
					map[string]interface{}{
						"log_id": "LOG1",
						"level":  "ERROR",
						"attributes": map[string]interface{}{
							"commit_id":              "commit_1",
							"source_map_file_prefix": "sourcemaps/app",
							"frames": []interface{}{
								map[string]interface{}{"file": "main.js", "line": 10, "column": 20},
							},
						},
					},
				},
			},
		},
	}
	resolve := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/resolve_stack_trace",
		Body: map[string]interface{}{
			"code": 999,
			"msg":  "secret token raw request payload should be redacted",
		},
	}
	reg.Register(search)
	reg.Register(resolve)

	if err := runAppsShortcut(t, AppsLogGet, []string{"+log-get", "--app-id", "app_x", "--log-id", "LOG1", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	got := stdout.String()
	if !strings.Contains(got, `"source_stack_status": "unresolved"`) {
		t.Fatalf("stdout missing unresolved status: %s", got)
	}
	for _, banned := range []string{"secret", "token", "raw request payload"} {
		if strings.Contains(strings.ToLower(got), banned) {
			t.Fatalf("stdout leaked %q: %s", banned, got)
		}
	}
}
