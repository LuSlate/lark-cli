// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/larksuite/cli/errs"
)

func TestPluginInstanceUpdate_Name(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "my-inst.json", map[string]interface{}{
		"id": "my-inst", "pluginKey": "@test/p", "pluginVersion": "1.0.0",
		"name": "Old Name", "formValue": map[string]interface{}{"k": "v"},
		"createdAt": 1000, "createdBy": 0,
	})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceUpdate, []string{
		"+plugin-instance-update",
		"--id", "my-inst",
		"--name", "New Name",
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	capData, _ := os.ReadFile(filepath.Join(capDir, "my-inst.json")) //nolint:forbidigo
	var cap map[string]interface{}
	json.Unmarshal(capData, &cap)
	if cap["name"] != "New Name" {
		t.Errorf("name = %v, want New Name", cap["name"])
	}
	if cap["pluginKey"] != "@test/p" {
		t.Errorf("pluginKey should be preserved, got %v", cap["pluginKey"])
	}
	if cap["createdBy"] != float64(0) {
		t.Errorf("createdBy should be preserved, got %v", cap["createdBy"])
	}
}

func TestPluginInstanceUpdate_FormValue(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "my-inst.json", map[string]interface{}{
		"id": "my-inst", "pluginKey": "@test/p", "pluginVersion": "1.0.0",
		"name": "Inst", "formValue": map[string]interface{}{"old": true},
	})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceUpdate, []string{
		"+plugin-instance-update",
		"--id", "my-inst",
		"--form-value", `{"new":"value"}`,
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	capData, _ := os.ReadFile(filepath.Join(capDir, "my-inst.json")) //nolint:forbidigo
	var cap map[string]interface{}
	json.Unmarshal(capData, &cap)
	fv, ok := cap["formValue"].(map[string]interface{})
	if !ok {
		t.Fatalf("formValue is not a map: %T", cap["formValue"])
	}
	if fv["new"] != "value" {
		t.Errorf("formValue.new = %v, want value", fv["new"])
	}
}

func TestPluginInstanceUpdate_NotFound(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceUpdate, []string{
		"+plugin-instance-update",
		"--id", "nonexistent",
		"--name", "X",
		"--project-path", dir,
		"--as", "user",
	}, factory, stdout)
	if err == nil {
		t.Fatal("expected error for nonexistent instance")
	}
	p, ok := errs.ProblemOf(err)
	if !ok {
		t.Fatalf("expected typed error, got %T: %v", err, err)
	}
	if p.Subtype != errs.SubtypeInvalidArgument {
		t.Errorf("subtype = %q, want invalid_argument", p.Subtype)
	}
}

func TestPluginInstanceUpdate_NoFieldProvided(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceUpdate, []string{
		"+plugin-instance-update",
		"--id", "my-inst",
		"--project-path", dir,
		"--as", "user",
	}, factory, stdout)
	if err == nil {
		t.Fatal("expected error when no update fields provided")
	}
}

func TestPluginInstanceUpdate_PreservesImmutableFields(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "my-inst.json", map[string]interface{}{
		"id": "my-inst", "pluginKey": "@test/p", "pluginVersion": "1.0.0",
		"name": "Old", "formValue": map[string]interface{}{},
		"createdAt": float64(1000000), "createdBy": float64(0),
	})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceUpdate, []string{
		"+plugin-instance-update",
		"--id", "my-inst",
		"--name", "Updated",
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	capData, _ := os.ReadFile(filepath.Join(capDir, "my-inst.json")) //nolint:forbidigo
	var cap map[string]interface{}
	json.Unmarshal(capData, &cap)

	if cap["id"] != "my-inst" {
		t.Errorf("id should be preserved, got %v", cap["id"])
	}
	if cap["pluginKey"] != "@test/p" {
		t.Errorf("pluginKey should be preserved, got %v", cap["pluginKey"])
	}
	if cap["pluginVersion"] != "1.0.0" {
		t.Errorf("pluginVersion should be preserved, got %v", cap["pluginVersion"])
	}
	if cap["createdAt"] != float64(1000000) {
		t.Errorf("createdAt should be preserved, got %v", cap["createdAt"])
	}
	updatedAt, ok := cap["updatedAt"].(float64)
	if !ok || updatedAt <= 1000000 {
		t.Errorf("updatedAt should be updated to a recent timestamp, got %v", cap["updatedAt"])
	}
}
