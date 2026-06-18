// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestPluginInstanceDelete_Basic(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "my-inst.json", map[string]interface{}{"id": "my-inst"})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceDelete, []string{
		"+plugin-instance-delete",
		"--id", "my-inst",
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var env map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	data, _ := env["data"].(map[string]interface{})
	if data["deleted"] != true {
		t.Errorf("deleted = %v, want true", data["deleted"])
	}

	if _, err := os.Stat(filepath.Join(capDir, "my-inst.json")); !os.IsNotExist(err) { //nolint:forbidigo
		t.Error("capability file should have been deleted")
	}
}

func TestPluginInstanceDelete_Idempotent(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceDelete, []string{
		"+plugin-instance-delete",
		"--id", "nonexistent",
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("delete of nonexistent instance should be idempotent, got: %v", err)
	}

	var env map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	data, _ := env["data"].(map[string]interface{})
	if data["deleted"] != true {
		t.Errorf("deleted = %v, want true", data["deleted"])
	}
}

func TestPluginInstanceDelete_MissingID(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceDelete, []string{
		"+plugin-instance-delete",
		"--project-path", dir,
		"--as", "user",
	}, factory, stdout)
	if err == nil {
		t.Fatal("expected error when --id is missing")
	}
}
