// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package minutes

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/httpmock"
)

func todoStub(token string) *httpmock.Stub {
	return &httpmock.Stub{
		Method: "PUT",
		URL:    "/open-apis/minutes/v1/minutes/" + token + "/todo",
		Body:   map[string]interface{}{"code": 0, "msg": "ok", "data": map[string]interface{}{}},
	}
}

func firstTodoItem(t *testing.T, raw []byte) map[string]any {
	t.Helper()
	if len(raw) == 0 {
		t.Fatal("request body was not captured")
	}
	var body map[string]any
	if err := json.Unmarshal(raw, &body); err != nil {
		t.Fatalf("failed to parse captured body: %v", err)
	}
	items, _ := body["todo_items"].([]any)
	if len(items) != 1 {
		t.Fatalf("todo_items: want 1 item, got %d (%v)", len(items), body["todo_items"])
	}
	item, _ := items[0].(map[string]any)
	return item
}

func TestMinutesSummary_DryRun(t *testing.T) {
	f, stdout, _, _ := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)

	err := mountAndRun(t, MinutesSummary, []string{
		"+summary",
		"--minute-token", "obcn123456789",
		"--summary", "**Weekly sync**\n- follow up",
		"--dry-run",
		"--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	out := stdout.String()
	if !strings.Contains(out, "PUT") || !strings.Contains(out, "/open-apis/minutes/v1/minutes/obcn123456789/summary") {
		t.Fatalf("dry-run output = %q", out)
	}
}

func TestMinutesTodo_DryRun(t *testing.T) {
	f, stdout, _, _ := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)

	err := mountAndRun(t, MinutesTodo, []string{
		"+todo",
		"--minute-token", "obcn123456789",
		"--todo", "- finish deck",
		"--is-done",
		"--dry-run",
		"--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	out := stdout.String()
	if !strings.Contains(out, "PUT") || !strings.Contains(out, "/open-apis/minutes/v1/minutes/obcn123456789/todo") {
		t.Fatalf("dry-run output = %q", out)
	}
	if !strings.Contains(out, "todo_items") {
		t.Fatalf("dry-run output should contain todo_items, got %q", out)
	}
}

func TestMinutesTodo_RequiresIsDone(t *testing.T) {
	f, _, stderr, _ := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)

	err := mountAndRun(t, MinutesTodo, []string{
		"+todo",
		"--minute-token", "obcn123456789",
		"--todo", "finish deck",
		"--as", "user",
	}, f, stderr)
	if err == nil {
		t.Fatal("expected validation error for missing --is-done")
	}
	if !strings.Contains(err.Error(), "is-done") && !strings.Contains(err.Error(), "todo-list") {
		t.Fatalf("error = %q, want message mentioning is-done or todo-list", err.Error())
	}
}

func TestMinutesTodo_Add_RequestBody(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)
	stub := todoStub("obcn123456789")
	reg.Register(stub)

	err := mountAndRun(t, MinutesTodo, []string{
		"+todo", "--minute-token", "obcn123456789",
		"--todo", "finish deck", "--is-done=false", "--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	item := firstTodoItem(t, stub.CapturedBody)
	if item["content"] != "finish deck" {
		t.Errorf("content = %v, want finish deck", item["content"])
	}
	if item["is_done"] != false {
		t.Errorf("is_done = %v, want false", item["is_done"])
	}
	if _, ok := item["todo_id"]; ok {
		t.Errorf("add should not send todo_id, got %v", item["todo_id"])
	}
	if !strings.Contains(stdout.String(), "add") {
		t.Errorf("output should report add operation, got %q", stdout.String())
	}
}

func TestMinutesTodo_Update_RequestBody(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)
	stub := todoStub("obcn123456789")
	reg.Register(stub)

	err := mountAndRun(t, MinutesTodo, []string{
		"+todo", "--minute-token", "obcn123456789",
		"--todo-id", "99", "--todo", "updated deck", "--is-done", "--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	item := firstTodoItem(t, stub.CapturedBody)
	if item["todo_id"] != "99" {
		t.Errorf("todo_id = %v, want 99", item["todo_id"])
	}
	if item["content"] != "updated deck" {
		t.Errorf("content = %v, want updated deck", item["content"])
	}
	if item["is_done"] != true {
		t.Errorf("is_done = %v, want true", item["is_done"])
	}
}

func TestMinutesTodo_Delete_RequestBody(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)
	stub := todoStub("obcn123456789")
	reg.Register(stub)

	err := mountAndRun(t, MinutesTodo, []string{
		"+todo", "--minute-token", "obcn123456789",
		"--todo-id", "88", "--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	item := firstTodoItem(t, stub.CapturedBody)
	if item["todo_id"] != "88" {
		t.Errorf("todo_id = %v, want 88", item["todo_id"])
	}
	if _, ok := item["content"]; ok {
		t.Errorf("delete should not send content, got %v", item["content"])
	}
	if _, ok := item["is_done"]; ok {
		t.Errorf("delete should not send is_done, got %v", item["is_done"])
	}
	// the todo id must never be surfaced to the user in the command output
	if strings.Contains(stdout.String(), "88") {
		t.Errorf("output must not expose the todo id, got %q", stdout.String())
	}
}

func TestMinutesTodo_DeleteRejectsIsDone(t *testing.T) {
	f, _, _, _ := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)

	err := mountAndRun(t, MinutesTodo, []string{
		"+todo", "--minute-token", "obcn123456789",
		"--todo-id", "88", "--is-done", "--as", "user",
	}, f, nil)
	if err == nil {
		t.Fatal("expected validation error when --is-done is used to delete")
	}
}

func TestMinutesTodo_RequiresAnyInput(t *testing.T) {
	f, _, _, _ := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)

	err := mountAndRun(t, MinutesTodo, []string{
		"+todo", "--minute-token", "obcn123456789", "--as", "user",
	}, f, nil)
	if err == nil {
		t.Fatal("expected validation error when neither --todo nor --todo-id is provided")
	}
}

func TestMinutesSummaryAndTodo_HelpMetadata(t *testing.T) {
	for _, tip := range MinutesSummary.Tips {
		if strings.Contains(tip, "raw text") {
			return
		}
	}
	t.Fatal("MinutesSummary tips should mention unsupported markdown display behavior")
}
