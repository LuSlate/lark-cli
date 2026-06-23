// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"testing"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/internal/httpmock"
)

func assertEnvVarQuery(t *testing.T, req *http.Request, want map[string]string, absent ...string) {
	t.Helper()
	query := req.URL.Query()
	for key, value := range want {
		if got := query.Get(key); got != value {
			t.Fatalf("query %s = %q, want %q (raw query %q)", key, got, value, req.URL.RawQuery)
		}
	}
	for _, key := range absent {
		if _, ok := query[key]; ok {
			t.Fatalf("query %s should be absent (raw query %q)", key, req.URL.RawQuery)
		}
	}
}

func decodeEnvVarEnvelopeData(t *testing.T, stdout string) map[string]interface{} {
	t.Helper()
	var envelope struct {
		OK   bool                   `json:"ok"`
		Data map[string]interface{} `json:"data"`
	}
	if err := json.Unmarshal([]byte(stdout), &envelope); err != nil {
		t.Fatalf("decode stdout: %v\n%s", err, stdout)
	}
	if !envelope.OK {
		t.Fatalf("expected ok envelope, got %s", stdout)
	}
	return envelope.Data
}

func requireEnvVarValidationProblem(t *testing.T, err error, param string) {
	t.Helper()
	p := requireAppsProblem(t, err, errs.CategoryValidation)
	if p.Subtype != errs.SubtypeInvalidArgument {
		t.Fatalf("validation subtype = %q, want %q", p.Subtype, errs.SubtypeInvalidArgument)
	}
	var validation *errs.ValidationError
	if !errors.As(err, &validation) {
		t.Fatalf("expected *errs.ValidationError, got %T: %v", err, err)
	}
	if validation.Param != param {
		t.Fatalf("validation param = %q, want %q", validation.Param, param)
	}
}

func TestAppsEnvVarList_DefaultsToDevAndHidesValues(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "GET",
		URL:    "/open-apis/spark/v1/apps/app_x/env_vars",
		OnMatch: func(req *http.Request) {
			assertEnvVarQuery(t, req, map[string]string{
				"env":            "dev",
				"include_values": "false",
				"page_size":      "50",
			}, "page_token")
		},
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"env_vars": []interface{}{
					map[string]interface{}{"key": "SECRET_TOKEN", "value": "super-secret", "env": "dev"},
				},
				"next_page_token": "",
				"has_more":        false,
			},
		},
	})

	if err := runAppsShortcut(t, AppsEnvVarList,
		[]string{"+envvar-list", "--app-id", "app_x", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}

	got := stdout.String()
	if strings.Contains(got, "super-secret") || strings.Contains(got, `"value"`) {
		t.Fatalf("stdout must not expose values by default: %s", got)
	}
	data := decodeEnvVarEnvelopeData(t, got)
	items, ok := data["items"].([]interface{})
	if !ok || len(items) != 1 {
		t.Fatalf("items = %#v, want one item", data["items"])
	}
	item, ok := items[0].(map[string]interface{})
	if !ok || item["key"] != "SECRET_TOKEN" {
		t.Fatalf("item = %#v, want SECRET_TOKEN", items[0])
	}
	if _, ok := item["value"]; ok {
		t.Fatalf("item must not contain value by default: %#v", item)
	}
}

func TestAppsEnvVarList_IncludeValuesAllowsValues(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "GET",
		URL:    "/open-apis/spark/v1/apps/app_x/env_vars",
		OnMatch: func(req *http.Request) {
			assertEnvVarQuery(t, req, map[string]string{
				"env":            "online",
				"include_values": "true",
				"page_size":      "20",
				"page_token":     "cursor-1",
			})
		},
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"items": []interface{}{
					map[string]interface{}{"key": "SECRET_TOKEN", "value": "super-secret", "env": "online"},
				},
				"nextPageToken": "cursor-2",
				"hasMore":       true,
			},
		},
	})

	if err := runAppsShortcut(t, AppsEnvVarList,
		[]string{"+envvar-list", "--app-id", "app_x", "--env", "online", "--include-values",
			"--page-size", "20", "--page-token", "cursor-1", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}

	got := stdout.String()
	if !strings.Contains(got, "super-secret") {
		t.Fatalf("stdout should include values when requested: %s", got)
	}
	data := decodeEnvVarEnvelopeData(t, got)
	if data["page_token"] != "cursor-2" {
		t.Fatalf("page_token = %v, want cursor-2", data["page_token"])
	}
	if data["has_more"] != true {
		t.Fatalf("has_more = %v, want true", data["has_more"])
	}
}

func TestAppsEnvVarSet_OnlineRequiresYesOutsideDryRun(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsEnvVarSet,
		[]string{"+envvar-set", "--app-id", "app_x", "--env", "online",
			"--key", "SECRET_TOKEN", "--value", "super-secret", "--as", "user"}, factory, stdout)

	p := requireAppsProblem(t, err, errs.CategoryConfirmation)
	if p.Subtype != errs.SubtypeConfirmationRequired {
		t.Fatalf("confirmation subtype = %q, want %q", p.Subtype, errs.SubtypeConfirmationRequired)
	}
	if !strings.Contains(p.Hint, "add --yes") {
		t.Fatalf("confirmation hint missing --yes guidance: %#v", p)
	}
}

func TestAppsEnvVarSet_OnlineDryRunDoesNotRequireYes(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	if err := runAppsShortcut(t, AppsEnvVarSet,
		[]string{"+envvar-set", "--app-id", "app_x", "--env", "online",
			"--key", "SECRET_TOKEN", "--value", "super-secret", "--dry-run", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("dry-run err=%v", err)
	}

	got := stdout.String()
	if strings.Contains(got, "super-secret") {
		t.Fatalf("dry-run must redact value: %s", got)
	}
	for _, want := range []string{`"method": "PUT"`, `/open-apis/spark/v1/apps/app_x/env_vars/SECRET_TOKEN`} {
		if !strings.Contains(got, want) {
			t.Fatalf("dry-run missing %q: %s", want, got)
		}
	}
	var dryRun struct {
		API []struct {
			Body map[string]interface{} `json:"body"`
		} `json:"api"`
	}
	if err := json.Unmarshal([]byte(got), &dryRun); err != nil {
		t.Fatalf("decode dry-run: %v\n%s", err, got)
	}
	if len(dryRun.API) != 1 || dryRun.API[0].Body["value"] != "<redacted>" {
		t.Fatalf("dry-run body value = %#v, want <redacted>", dryRun.API)
	}
}

func TestAppsEnvVarSet_ExecutesWithYesAndDoesNotEchoValue(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	stub := &httpmock.Stub{
		Method: "PUT",
		URL:    "/open-apis/spark/v1/apps/app_x/env_vars/SECRET_TOKEN",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{}},
	}
	reg.Register(stub)

	if err := runAppsShortcut(t, AppsEnvVarSet,
		[]string{"+envvar-set", "--app-id", "app_x", "--env", "online",
			"--key", "SECRET_TOKEN", "--value", "super-secret", "--yes", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}

	var sent map[string]interface{}
	if err := json.Unmarshal(stub.CapturedBody, &sent); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if sent["env"] != "online" || sent["value"] != "super-secret" {
		t.Fatalf("body = %#v, want real online value", sent)
	}
	got := stdout.String()
	if strings.Contains(got, "super-secret") || strings.Contains(got, `"value"`) {
		t.Fatalf("stdout must not echo value: %s", got)
	}
	for _, want := range []string{`"key": "SECRET_TOKEN"`, `"env": "online"`, `"action": "set"`} {
		if !strings.Contains(got, want) {
			t.Fatalf("stdout missing %q: %s", want, got)
		}
	}
}

func TestAppsEnvVarDelete_IsHighRiskWrite(t *testing.T) {
	if AppsEnvVarDelete.Risk != "high-risk-write" {
		t.Fatalf("risk = %q, want high-risk-write", AppsEnvVarDelete.Risk)
	}
}

func TestAppsEnvVarDelete_BuildsDeleteBodyWithKeys(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	stub := &httpmock.Stub{
		Method: "DELETE",
		URL:    "/open-apis/spark/v1/apps/app_x/env_vars",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{}},
	}
	reg.Register(stub)

	if err := runAppsShortcut(t, AppsEnvVarDelete,
		[]string{"+envvar-delete", "--app-id", "app_x", "--env", "online",
			"--key", "SECRET_ONE", "--key", "SECRET_TWO", "--yes", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}

	var sent map[string]interface{}
	if err := json.Unmarshal(stub.CapturedBody, &sent); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if sent["env"] != "online" {
		t.Fatalf("body.env = %v, want online", sent["env"])
	}
	keys, ok := sent["keys"].([]interface{})
	if !ok || len(keys) != 2 || keys[0] != "SECRET_ONE" || keys[1] != "SECRET_TWO" {
		t.Fatalf("body.keys = %#v, want SECRET_ONE/SECRET_TWO", sent["keys"])
	}
	got := stdout.String()
	for _, want := range []string{`"env": "online"`, `"deleted_keys"`, `"SECRET_ONE"`, `"SECRET_TWO"`} {
		if !strings.Contains(got, want) {
			t.Fatalf("stdout missing %q: %s", want, got)
		}
	}
}

func TestAppsEnvVarDelete_OnlineDryRunDoesNotRequireYes(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	if err := runAppsShortcut(t, AppsEnvVarDelete,
		[]string{"+envvar-delete", "--app-id", "app_x", "--env", "online",
			"--key", "SECRET_ONE", "--key", "SECRET_TWO", "--dry-run", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("dry-run err=%v", err)
	}

	var dryRun struct {
		API []struct {
			Method string                 `json:"method"`
			URL    string                 `json:"url"`
			Body   map[string]interface{} `json:"body"`
		} `json:"api"`
	}
	got := stdout.String()
	if err := json.Unmarshal([]byte(got), &dryRun); err != nil {
		t.Fatalf("decode dry-run: %v\n%s", err, got)
	}
	if len(dryRun.API) != 1 || dryRun.API[0].Method != "DELETE" || dryRun.API[0].URL != "/open-apis/spark/v1/apps/app_x/env_vars" {
		t.Fatalf("dry-run api = %#v", dryRun.API)
	}
	if dryRun.API[0].Body["env"] != "online" {
		t.Fatalf("dry-run body.env = %v, want online", dryRun.API[0].Body["env"])
	}
	keys, ok := dryRun.API[0].Body["keys"].([]interface{})
	if !ok || len(keys) != 2 || keys[0] != "SECRET_ONE" || keys[1] != "SECRET_TWO" {
		t.Fatalf("dry-run body.keys = %#v, want SECRET_ONE/SECRET_TWO", dryRun.API[0].Body["keys"])
	}
}

func TestAppsEnvVarList_InvalidEnvTypedValidation(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsEnvVarList,
		[]string{"+envvar-list", "--app-id", "app_x", "--env", "prod", "--as", "user"}, factory, stdout)
	requireEnvVarValidationProblem(t, err, "--env")
}

func TestAppsEnvVarSet_InvalidKeyTypedValidation(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsEnvVarSet,
		[]string{"+envvar-set", "--app-id", "app_x", "--key", "bad-key",
			"--value", "super-secret", "--as", "user"}, factory, stdout)
	requireEnvVarValidationProblem(t, err, "--key")
}

func TestAppsEnvVarDelete_InvalidKeyTypedValidation(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsEnvVarDelete,
		[]string{"+envvar-delete", "--app-id", "app_x", "--key", "bad-key",
			"--yes", "--as", "user"}, factory, stdout)
	requireEnvVarValidationProblem(t, err, "--key")
}
