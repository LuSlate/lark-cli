// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/larksuite/cli/errs"
)

func TestPluginInstanceList_Empty(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceList,
		[]string{"+plugin-instance-list", "--project-path", dir, "--format", "json", "--as", "user"},
		factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var env map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("invalid JSON: %v\nraw: %s", err, stdout.String())
	}
	data, _ := env["data"].(map[string]interface{})
	instances, _ := data["instances"].([]interface{})
	if len(instances) != 0 {
		t.Errorf("expected 0 instances, got %d", len(instances))
	}
}

func TestPluginInstanceList_WithInstances(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "inst-a.json", map[string]interface{}{
		"id": "inst-a", "pluginKey": "@test/plugin-a", "pluginVersion": "1.0.0", "name": "Instance A",
	})
	writeTestCapJSON(t, capDir, "inst-b.json", map[string]interface{}{
		"id": "inst-b", "pluginKey": "@test/plugin-b", "pluginVersion": "2.0.0", "name": "Instance B",
	})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceList,
		[]string{"+plugin-instance-list", "--project-path", dir, "--as", "user"},
		factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	got := stdout.String()
	if !strings.Contains(got, "inst-a") || !strings.Contains(got, "inst-b") {
		t.Errorf("output missing instances: %s", got)
	}
}

func TestPluginInstanceList_Summary(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "inst-a.json", map[string]interface{}{
		"id": "inst-a", "pluginKey": "@test/plugin-a", "pluginVersion": "1.0.0",
		"name": "Instance A", "paramsSchema": map[string]interface{}{"type": "object"},
	})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceList,
		[]string{"+plugin-instance-list", "--summary", "--project-path", dir, "--format", "json", "--as", "user"},
		factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var env map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("invalid JSON: %v\nraw: %s", err, stdout.String())
	}
	data, _ := env["data"].(map[string]interface{})
	instances, _ := data["instances"].([]interface{})
	if len(instances) != 1 {
		t.Fatalf("got %d instances, want 1", len(instances))
	}
	inst := instances[0].(map[string]interface{})
	if _, has := inst["paramsSchema"]; has {
		t.Error("summary should not include paramsSchema")
	}
	if inst["id"] != "inst-a" {
		t.Errorf("id = %v, want inst-a", inst["id"])
	}
}

func TestPluginInstanceList_NoPackageJSON(t *testing.T) {
	dir := t.TempDir()
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceList,
		[]string{"+plugin-instance-list", "--project-path", dir, "--as", "user"},
		factory, stdout)
	if err == nil {
		t.Fatal("expected error when package.json missing")
	}
	p, ok := errs.ProblemOf(err)
	if !ok {
		t.Fatalf("expected typed error, got %T: %v", err, err)
	}
	if p.Subtype != errs.SubtypeFailedPrecondition {
		t.Errorf("subtype = %q, want failed_precondition", p.Subtype)
	}
}

func TestPluginInstanceList_CapDirNotExist(t *testing.T) {
	dir := setupPluginTestProjectNoCapDir(t)
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceList,
		[]string{"+plugin-instance-list", "--project-path", dir, "--as", "user"},
		factory, stdout)
	if err != nil {
		t.Fatalf("should not error when capabilities dir not found, got: %v", err)
	}
}

// --- helpers ---

// setupPluginTestProject creates a temp dir with package.json and a capabilities dir.
// appType is "server" or "shared".
func setupPluginTestProject(t *testing.T, appType string) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "package.json"), []byte("{}"), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	capDir := filepath.Join(dir, appType, "capabilities")
	if err := os.MkdirAll(capDir, 0o755); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	return dir
}

// setupPluginTestProjectNoCapDir creates a temp dir with package.json but no capabilities dir.
func setupPluginTestProjectNoCapDir(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "package.json"), []byte("{}"), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	return dir
}
