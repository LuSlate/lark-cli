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

func TestPluginInstanceCreate_Basic(t *testing.T) {
	dir := setupPluginTestProjectWithManifest(t, "server", "@test/my-plugin")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceCreate, []string{
		"+plugin-instance-create",
		"--plugin", "@test/my-plugin@1.0.0",
		"--name", "My Instance",
		"--form-value", `{"prompt":"hello"}`,
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var env map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("invalid JSON output: %v", err)
	}
	data, _ := env["data"].(map[string]interface{})
	if data["id"] != "test-my-plugin" {
		t.Errorf("id = %v, want test-my-plugin (auto-derived)", data["id"])
	}
	if data["pluginKey"] != "@test/my-plugin" {
		t.Errorf("pluginKey = %v, want @test/my-plugin", data["pluginKey"])
	}

	// Verify file was written
	capPath := filepath.Join(dir, "server", "capabilities", "test-my-plugin.json")
	capData, err := os.ReadFile(capPath) //nolint:forbidigo
	if err != nil {
		t.Fatalf("capability file not created: %v", err)
	}
	var cap map[string]interface{}
	if err := json.Unmarshal(capData, &cap); err != nil {
		t.Fatalf("invalid capability JSON: %v", err)
	}
	if cap["name"] != "My Instance" {
		t.Errorf("cap.name = %v, want My Instance", cap["name"])
	}
}

func TestPluginInstanceCreate_CustomID(t *testing.T) {
	dir := setupPluginTestProjectWithManifest(t, "server", "@test/my-plugin")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceCreate, []string{
		"+plugin-instance-create",
		"--id", "custom-summary",
		"--plugin", "@test/my-plugin@2.0.0",
		"--name", "Custom",
		"--form-value", `{"key":"val"}`,
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	capPath := filepath.Join(dir, "server", "capabilities", "custom-summary.json")
	if _, err := os.Stat(capPath); err != nil { //nolint:forbidigo
		t.Fatalf("capability file not created at custom id path: %v", err)
	}
}

func TestPluginInstanceCreate_WithParamsSchema(t *testing.T) {
	dir := setupPluginTestProjectWithManifest(t, "server", "@test/my-plugin")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceCreate, []string{
		"+plugin-instance-create",
		"--plugin", "@test/my-plugin@1.0.0",
		"--name", "WithSchema",
		"--form-value", `{"prompt":"{{input.text}}"}`,
		"--params-schema", `{"type":"object","properties":{"text":{"type":"string","description":"user input text"}}}`,
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	capPath := filepath.Join(dir, "server", "capabilities", "test-my-plugin.json")
	capData, err := os.ReadFile(capPath) //nolint:forbidigo
	if err != nil {
		t.Fatal(err)
	}
	var cap map[string]interface{}
	if err := json.Unmarshal(capData, &cap); err != nil {
		t.Fatal(err)
	}
	if _, ok := cap["paramsSchema"]; !ok {
		t.Error("paramsSchema should be present in capability")
	}
}

func TestPluginInstanceCreate_DuplicateID(t *testing.T) {
	dir := setupPluginTestProjectWithManifest(t, "server", "@test/my-plugin")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "existing.json", map[string]interface{}{"id": "existing"})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceCreate, []string{
		"+plugin-instance-create",
		"--id", "existing",
		"--plugin", "@test/my-plugin@1.0.0",
		"--name", "Dup",
		"--form-value", `{}`,
		"--project-path", dir,
		"--as", "user",
	}, factory, stdout)
	if err == nil {
		t.Fatal("expected error for duplicate id")
	}
	p, ok := errs.ProblemOf(err)
	if !ok {
		t.Fatalf("expected typed error, got %T: %v", err, err)
	}
	if p.Subtype != errs.SubtypeInvalidArgument {
		t.Errorf("subtype = %q, want invalid_argument", p.Subtype)
	}
}

func TestPluginInstanceCreate_ForceOverwrite(t *testing.T) {
	dir := setupPluginTestProjectWithManifest(t, "server", "@test/my-plugin")
	capDir := filepath.Join(dir, "server", "capabilities")
	writeTestCapJSON(t, capDir, "existing.json", map[string]interface{}{"id": "existing", "name": "Old"})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceCreate, []string{
		"+plugin-instance-create",
		"--id", "existing",
		"--plugin", "@test/my-plugin@1.0.0",
		"--name", "New",
		"--form-value", `{}`,
		"--force",
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error with --force: %v", err)
	}

	capData, _ := os.ReadFile(filepath.Join(capDir, "existing.json")) //nolint:forbidigo
	var cap map[string]interface{}
	json.Unmarshal(capData, &cap)
	if cap["name"] != "New" {
		t.Errorf("name = %v, want New (overwritten)", cap["name"])
	}
}

func TestPluginInstanceCreate_PluginNotInstalled(t *testing.T) {
	dir := setupPluginTestProject(t, "server")
	factory, stdout, _ := newAppsExecuteFactory(t)

	err := runAppsShortcut(t, AppsPluginInstanceCreate, []string{
		"+plugin-instance-create",
		"--plugin", "@test/not-installed@1.0.0",
		"--name", "Fail",
		"--form-value", `{}`,
		"--project-path", dir,
		"--as", "user",
	}, factory, stdout)
	if err == nil {
		t.Fatal("expected error when plugin not installed")
	}
	p, ok := errs.ProblemOf(err)
	if !ok {
		t.Fatalf("expected typed error, got %T: %v", err, err)
	}
	if p.Subtype != errs.SubtypeFailedPrecondition {
		t.Errorf("subtype = %q, want failed_precondition", p.Subtype)
	}
}

func TestPluginInstanceCreate_InvalidPluginFormat(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	dir := setupPluginTestProject(t, "server")

	err := runAppsShortcut(t, AppsPluginInstanceCreate, []string{
		"+plugin-instance-create",
		"--plugin", "no-version",
		"--name", "Fail",
		"--form-value", `{}`,
		"--project-path", dir,
		"--as", "user",
	}, factory, stdout)
	if err == nil {
		t.Fatal("expected error for invalid plugin format")
	}
}

func TestPluginInstanceCreate_InvalidJSON(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	dir := setupPluginTestProject(t, "server")

	err := runAppsShortcut(t, AppsPluginInstanceCreate, []string{
		"+plugin-instance-create",
		"--plugin", "@test/p@1.0.0",
		"--name", "Fail",
		"--form-value", `not json`,
		"--project-path", dir,
		"--as", "user",
	}, factory, stdout)
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

func TestPluginInstanceCreate_AutoCreateCapDir(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "package.json"), []byte("{}"), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, ".env.local"), []byte("MIAODA_APP_TYPE=2\n"), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	pluginKey := "@test/my-plugin"
	manifestDir := filepath.Join(dir, "node_modules", pluginKey)
	if err := os.MkdirAll(manifestDir, 0o755); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(manifestDir, "manifest.json"), []byte(`{}`), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	writeTestPkgJSON(t, dir, map[string]interface{}{
		"actionPlugins": map[string]interface{}{
			pluginKey: "1.0.0",
		},
	})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstanceCreate, []string{
		"+plugin-instance-create",
		"--plugin", "@test/my-plugin@1.0.0",
		"--name", "AutoDir",
		"--form-value", `{}`,
		"--project-path", dir,
		"--format", "json",
		"--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("should auto-create capabilities dir: %v", err)
	}

	capPath := filepath.Join(dir, "server", "capabilities", "test-my-plugin.json")
	if _, err := os.Stat(capPath); err != nil { //nolint:forbidigo
		t.Fatalf("capability file not created: %v", err)
	}
}

// --- helpers ---

// setupPluginTestProjectWithManifest creates a project dir with package.json,
// capabilities dir, and a minimal manifest.json for the given plugin key.
func setupPluginTestProjectWithManifest(t *testing.T, appType, pluginKey string) string {
	t.Helper()
	dir := setupPluginTestProject(t, appType)
	manifestDir := filepath.Join(dir, "node_modules", pluginKey)
	if err := os.MkdirAll(manifestDir, 0o755); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(manifestDir, "manifest.json"), []byte(`{"actions":[]}`), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	// Register the plugin in actionPlugins so create's actionPlugins check passes
	writeTestPkgJSON(t, dir, map[string]interface{}{
		"actionPlugins": map[string]interface{}{
			pluginKey: "1.0.0",
		},
	})
	return dir
}
