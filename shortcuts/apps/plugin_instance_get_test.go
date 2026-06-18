// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"path/filepath"
	"strings"
	"testing"

	"github.com/larksuite/cli/errs"
)

func TestPluginInstanceGet_Basic(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "my-inst.json", map[string]interface{}{
		"id": "my-inst", "pluginKey": "@test/plugin", "pluginVersion": "1.0.0",
		"name": "My Instance", "createdAt": 1718500000000,
	})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceGet,
		[]string{"+plugin-instance-get", "--id", "my-inst", "--project-path", dir, "--as", "user"},
		factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	got := stdout.String()
	if !strings.Contains(got, "my-inst") {
		t.Errorf("output missing instance id: %s", got)
	}
	if !strings.Contains(got, "@test/plugin") {
		t.Errorf("output missing pluginKey: %s", got)
	}
}

func TestPluginInstanceGet_JSON(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "my-inst.json", map[string]interface{}{
		"id": "my-inst", "pluginKey": "@test/plugin", "pluginVersion": "1.0.0", "name": "Test",
	})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceGet,
		[]string{"+plugin-instance-get", "--id", "my-inst", "--project-path", dir, "--format", "json", "--as", "user"},
		factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var env map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("invalid JSON: %v\nraw: %s", err, stdout.String())
	}
	data, _ := env["data"].(map[string]interface{})
	if data["id"] != "my-inst" {
		t.Errorf("id = %v, want my-inst", data["id"])
	}
}

func TestPluginInstanceGet_NotFound(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceGet,
		[]string{"+plugin-instance-get", "--id", "nonexistent", "--project-path", dir, "--as", "user"},
		factory, stdout)
	if err == nil {
		t.Fatal("expected error")
	}
	p, ok := errs.ProblemOf(err)
	if !ok {
		t.Fatalf("expected typed error, got %T: %v", err, err)
	}
	if p.Subtype != errs.SubtypeInvalidArgument {
		t.Errorf("subtype = %q, want invalid_argument", p.Subtype)
	}
}

func TestPluginInstanceGet_MissingID(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceGet,
		[]string{"+plugin-instance-get", "--project-path", dir, "--as", "user"},
		factory, stdout)
	if err == nil {
		t.Fatal("expected error when --id is missing")
	}
}
