// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestPluginUninstall_Basic(t *testing.T) {
	dir := t.TempDir()
	writeTestPkgJSON(t, dir, map[string]interface{}{
		"actionPlugins": map[string]interface{}{
			"@test/my-plugin": "1.0.0",
		},
	})
	pluginDir := filepath.Join(dir, "node_modules", "@test/my-plugin")
	os.MkdirAll(pluginDir, 0o755) //nolint:forbidigo
	os.WriteFile(filepath.Join(pluginDir, "manifest.json"), []byte("{}"), 0o644) //nolint:forbidigo

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginUninstall, []string{
		"+plugin-uninstall", "--name", "@test/my-plugin",
		"--project-path", dir, "--format", "json", "--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Verify node_modules removed
	if _, err := os.Stat(pluginDir); !os.IsNotExist(err) { //nolint:forbidigo
		t.Error("node_modules plugin dir should be removed")
	}

	// Verify package.json updated
	pkg, _ := pluginReadPackageJSON(dir)
	ap := pluginGetActionPlugins(pkg)
	if _, ok := ap["@test/my-plugin"]; ok {
		t.Error("actionPlugins should no longer contain @test/my-plugin")
	}
}

func TestPluginUninstall_NotInstalled(t *testing.T) {
	dir := t.TempDir()
	writeTestPkgJSON(t, dir, map[string]interface{}{})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginUninstall, []string{
		"+plugin-uninstall", "--name", "@test/not-here",
		"--project-path", dir, "--format", "json", "--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("uninstalling non-existent plugin should succeed: %v", err)
	}

	var env map[string]interface{}
	json.Unmarshal(stdout.Bytes(), &env)
	data, _ := env["data"].(map[string]interface{})
	if data["removed"] != true {
		t.Errorf("removed = %v, want true", data["removed"])
	}
}

func TestPluginUninstall_PreservesOtherPlugins(t *testing.T) {
	dir := t.TempDir()
	writeTestPkgJSON(t, dir, map[string]interface{}{
		"name": "my-app",
		"actionPlugins": map[string]interface{}{
			"@test/remove-me": "1.0.0",
			"@test/keep-me":   "2.0.0",
		},
	})

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginUninstall, []string{
		"+plugin-uninstall", "--name", "@test/remove-me",
		"--project-path", dir, "--format", "json", "--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	pkg, _ := pluginReadPackageJSON(dir)
	ap := pluginGetActionPlugins(pkg)
	if _, ok := ap["@test/remove-me"]; ok {
		t.Error("@test/remove-me should be removed from actionPlugins")
	}
	if v, ok := ap["@test/keep-me"]; !ok || v != "2.0.0" {
		t.Errorf("@test/keep-me should be preserved, got %q", v)
	}
	if name, _ := pkg["name"].(string); name != "my-app" {
		t.Errorf("other fields should be preserved, name = %q", name)
	}
}
