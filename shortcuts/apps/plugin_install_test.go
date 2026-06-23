// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/larksuite/cli/internal/httpmock"
)

func TestPluginInstall_SinglePlugin(t *testing.T) {
	dir := t.TempDir()
	writeTestPkgJSON(t, dir, map[string]interface{}{})

	factory, stdout, reg := newAppsExecuteFactory(t)

	// Mock batch_get API
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/plugin/versions/batch_get",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"pluginKeyToVersions": map[string]interface{}{
					"@test/my-plugin": []interface{}{
						map[string]interface{}{
							"version":     "1.0.0",
							"downloadURL": "/open-apis/spark/v1/plugins/test/versions/1.0.0/package",
						},
					},
				},
			},
		},
	})

	// Mock download API (return a valid tgz with manifest.json + package.json)
	tgzData := buildTestTGZ(t, map[string]string{
		"manifest.json": `{"actions":[]}`,
		"package.json":  `{"name":"@test/my-plugin","version":"1.0.0"}`,
	})
	reg.Register(&httpmock.Stub{
		Method:      "GET",
		URL:         "/open-apis/spark/v1/plugin/versions/download_package",
		RawBody:     tgzData,
		ContentType: "application/octet-stream",
	})

	err := runAppsShortcut(t, AppsPluginInstall, []string{
		"+plugin-install", "--name", "@test/my-plugin@1.0.0",
		"--project-path", dir, "--format", "json", "--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Verify file extracted
	manifestPath := filepath.Join(dir, "node_modules", "@test/my-plugin", "manifest.json")
	if _, err := os.Stat(manifestPath); err != nil { //nolint:forbidigo
		t.Fatalf("manifest.json not extracted: %v", err)
	}

	// Verify package.json updated
	pkg, _ := pluginReadPackageJSON(dir)
	ap := pluginGetActionPlugins(pkg)
	if v := ap["@test/my-plugin"]; v != "1.0.0" {
		t.Errorf("actionPlugins[@test/my-plugin] = %q, want 1.0.0", v)
	}

	// Verify output
	var env map[string]interface{}
	json.Unmarshal(stdout.Bytes(), &env)
	data, _ := env["data"].(map[string]interface{})
	if data["status"] != "installed" {
		t.Errorf("status = %v, want installed", data["status"])
	}
}

func TestPluginInstall_AlreadyInstalled(t *testing.T) {
	dir := t.TempDir()
	writeTestPkgJSON(t, dir, map[string]interface{}{
		"actionPlugins": map[string]interface{}{
			"@test/my-plugin": "1.0.0",
		},
	})
	// Create an existing installed plugin with package.json containing version
	pkgDir := filepath.Join(dir, "node_modules", "@test/my-plugin")
	os.MkdirAll(pkgDir, 0o755) //nolint:forbidigo
	os.WriteFile(filepath.Join(pkgDir, "package.json"), []byte(`{"version":"1.0.0"}`), 0o644) //nolint:forbidigo

	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsPluginInstall, []string{
		"+plugin-install", "--name", "@test/my-plugin@1.0.0",
		"--project-path", dir, "--format", "json", "--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var env map[string]interface{}
	json.Unmarshal(stdout.Bytes(), &env)
	data, _ := env["data"].(map[string]interface{})
	if data["status"] != "already_installed" {
		t.Errorf("status = %v, want already_installed", data["status"])
	}
}

// --- tgz helpers ---

func TestPluginExtractTGZ(t *testing.T) {
	tgzData := buildTestTGZ(t, map[string]string{
		"manifest.json": `{"actions":[]}`,
		"README.md":     "# Hello",
	})

	destDir := t.TempDir()
	if err := pluginExtractTGZ(bytes.NewReader(tgzData), destDir); err != nil {
		t.Fatalf("extract error: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(destDir, "manifest.json")) //nolint:forbidigo
	if err != nil {
		t.Fatalf("manifest.json not extracted: %v", err)
	}
	if string(data) != `{"actions":[]}` {
		t.Errorf("manifest.json content = %q", string(data))
	}
}

func TestPluginExtractTGZ_PathTraversal(t *testing.T) {
	var buf bytes.Buffer
	gz := gzip.NewWriter(&buf)
	tw := tar.NewWriter(gz)
	tw.WriteHeader(&tar.Header{
		Name:     "package/../../../etc/passwd",
		Size:     5,
		Mode:     0o644,
		Typeflag: tar.TypeReg,
	})
	tw.Write([]byte("evil!"))
	tw.Close()
	gz.Close()

	destDir := t.TempDir()
	if err := pluginExtractTGZ(&buf, destDir); err != nil {
		t.Fatalf("extract should not error, but skip bad entries: %v", err)
	}
	if _, err := os.Stat(filepath.Join(destDir, "..", "..", "etc", "passwd")); err == nil { //nolint:forbidigo
		t.Error("path traversal should have been blocked")
	}
}

func TestPluginParseInstallTarget(t *testing.T) {
	tests := []struct {
		input       string
		wantKey     string
		wantVersion string
	}{
		{"@scope/name@1.0.0", "@scope/name", "1.0.0"},
		{"@scope/name@latest", "@scope/name", "latest"},
		{"@scope/name", "@scope/name", ""},
		{"simple@2.0.0", "simple", "2.0.0"},
		{"simple", "simple", ""},
		{"", "", ""},
	}
	for _, tt := range tests {
		key, ver := pluginParseInstallTarget(tt.input)
		if key != tt.wantKey || ver != tt.wantVersion {
			t.Errorf("pluginParseInstallTarget(%q) = (%q, %q), want (%q, %q)",
				tt.input, key, ver, tt.wantKey, tt.wantVersion)
		}
	}
}

// buildTestTGZ creates a .tgz in memory with files under a "package/" prefix.
func buildTestTGZ(t *testing.T, files map[string]string) []byte {
	t.Helper()
	var buf bytes.Buffer
	gz := gzip.NewWriter(&buf)
	tw := tar.NewWriter(gz)

	for name, content := range files {
		tw.WriteHeader(&tar.Header{
			Name:     "package/" + name,
			Size:     int64(len(content)),
			Mode:     0o644,
			Typeflag: tar.TypeReg,
		})
		tw.Write([]byte(content))
	}

	tw.Close()
	gz.Close()
	return buf.Bytes()
}
