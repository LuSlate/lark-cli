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

// --- pluginResolveProjectPath ---

func TestPluginResolveProjectPath_DefaultToCwd(t *testing.T) {
	got, err := pluginResolveProjectPath("")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	cwd, _ := os.Getwd() //nolint:forbidigo
	if got != cwd {
		t.Errorf("got %q, want cwd %q", got, cwd)
	}
}

func TestPluginResolveProjectPath_ExplicitPath(t *testing.T) {
	got, err := pluginResolveProjectPath("/tmp/myapp")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != "/tmp/myapp" {
		t.Errorf("got %q, want /tmp/myapp", got)
	}
}

// --- pluginCheckProjectDir ---

func TestPluginCheckProjectDir_OK(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "package.json"), []byte("{}"), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	if err := pluginCheckProjectDir(dir); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestPluginCheckProjectDir_Missing(t *testing.T) {
	dir := t.TempDir()
	err := pluginCheckProjectDir(dir)
	if err == nil {
		t.Fatal("expected error")
	}
	p, ok := errs.ProblemOf(err)
	if !ok {
		t.Fatalf("expected typed error, got %T: %v", err, err)
	}
	if p.Subtype != errs.SubtypeFailedPrecondition {
		t.Errorf("subtype = %q, want failed_precondition", p.Subtype)
	}
}

// --- pluginResolveCapDir ---

func TestPluginResolveCapDir_ExplicitFlag(t *testing.T) {
	got, err := pluginResolveCapDir("/proj", "my/caps")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if want := filepath.Join("/proj", "my/caps"); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestPluginResolveCapDir_ExplicitFlagAbsolute(t *testing.T) {
	got, err := pluginResolveCapDir("/proj", "/absolute/caps")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != "/absolute/caps" {
		t.Errorf("got %q, want /absolute/caps", got)
	}
}

func TestPluginResolveCapDir_EnvVar(t *testing.T) {
	t.Setenv("MIAODA_CAPABILITIES_DIR", "envdir/caps")
	got, err := pluginResolveCapDir("/proj", "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if want := filepath.Join("/proj", "envdir/caps"); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestPluginResolveCapDir_AppTypeEnv(t *testing.T) {
	t.Setenv("MIAODA_APP_TYPE", "2")
	got, err := pluginResolveCapDir("/proj", "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if want := filepath.Join("/proj", "server", "capabilities"); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestPluginResolveCapDir_AppTypeEnvShared(t *testing.T) {
	t.Setenv("MIAODA_APP_TYPE", "6")
	got, err := pluginResolveCapDir("/proj", "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if want := filepath.Join("/proj", "shared", "capabilities"); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestPluginResolveCapDir_EnvLocal(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, ".env.local"), []byte("MIAODA_APP_TYPE=2\n"), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	got, err := pluginResolveCapDir(dir, "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if want := filepath.Join(dir, "server", "capabilities"); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestPluginResolveCapDir_DetectServer(t *testing.T) {
	dir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir, "server", "capabilities"), 0o755); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	got, err := pluginResolveCapDir(dir, "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if want := filepath.Join(dir, "server", "capabilities"); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestPluginResolveCapDir_DetectShared(t *testing.T) {
	dir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir, "shared", "capabilities"), 0o755); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	got, err := pluginResolveCapDir(dir, "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if want := filepath.Join(dir, "shared", "capabilities"); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestPluginResolveCapDir_Ambiguous(t *testing.T) {
	dir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir, "server", "capabilities"), 0o755); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(dir, "shared", "capabilities"), 0o755); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
	_, err := pluginResolveCapDir(dir, "")
	if err == nil {
		t.Fatal("expected ambiguous error")
	}
	p, ok := errs.ProblemOf(err)
	if !ok {
		t.Fatalf("expected typed error, got %T: %v", err, err)
	}
	if p.Subtype != errs.SubtypeFailedPrecondition {
		t.Errorf("subtype = %q, want failed_precondition", p.Subtype)
	}
}

func TestPluginResolveCapDir_NeitherExists_DefaultsToServer(t *testing.T) {
	dir := t.TempDir()
	got, err := pluginResolveCapDir(dir, "")
	if err != nil {
		t.Fatalf("should default to server/capabilities, got error: %v", err)
	}
	if want := filepath.Join(dir, "server", "capabilities"); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestPluginResolveCapDir_AppType3_UsesServer(t *testing.T) {
	t.Setenv("MIAODA_APP_TYPE", "3")
	got, err := pluginResolveCapDir("/proj", "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if want := filepath.Join("/proj", "server", "capabilities"); got != want {
		t.Errorf("got %q, want %q (appType=3 should use server)", got, want)
	}
}

// --- pluginListCapabilities ---

func TestPluginListCapabilities_Empty(t *testing.T) {
	dir := t.TempDir()
	caps, err := pluginListCapabilities(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(caps) != 0 {
		t.Errorf("got %d caps, want 0", len(caps))
	}
}

func TestPluginListCapabilities_DirNotExist(t *testing.T) {
	caps, err := pluginListCapabilities("/nonexistent/path")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if caps != nil {
		t.Errorf("got %v, want nil", caps)
	}
}

func TestPluginListCapabilities_WithFiles(t *testing.T) {
	dir := t.TempDir()
	writeTestCapJSON(t, dir, "cap1.json", map[string]interface{}{"id": "cap1", "name": "Cap One"})
	writeTestCapJSON(t, dir, "cap2.json", map[string]interface{}{"id": "cap2", "name": "Cap Two"})
	// non-JSON file should be skipped
	if err := os.WriteFile(filepath.Join(dir, "readme.txt"), []byte("ignore"), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}

	caps, err := pluginListCapabilities(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(caps) != 2 {
		t.Fatalf("got %d caps, want 2", len(caps))
	}
}

func TestPluginListCapabilities_SkipsMalformed(t *testing.T) {
	dir := t.TempDir()
	writeTestCapJSON(t, dir, "good.json", map[string]interface{}{"id": "good"})
	if err := os.WriteFile(filepath.Join(dir, "bad.json"), []byte("not json"), 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}

	caps, err := pluginListCapabilities(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(caps) != 1 {
		t.Fatalf("got %d caps, want 1", len(caps))
	}
}

// --- pluginGetCapability ---

func TestPluginGetCapability_Found(t *testing.T) {
	dir := t.TempDir()
	writeTestCapJSON(t, dir, "my-instance.json", map[string]interface{}{"id": "my-instance", "name": "My Instance"})

	cap, err := pluginGetCapability(dir, "my-instance")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cap["id"] != "my-instance" {
		t.Errorf("id = %v, want my-instance", cap["id"])
	}
}

func TestPluginGetCapability_NotFound(t *testing.T) {
	dir := t.TempDir()
	_, err := pluginGetCapability(dir, "nonexistent")
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

// --- pluginValidateFormValue ---

func TestValidateFormValue_Valid(t *testing.T) {
	fv := map[string]interface{}{"prompt": "{{input.text}}"}
	ps := map[string]interface{}{
		"properties": map[string]interface{}{
			"text": map[string]interface{}{"type": "string", "description": "input text"},
		},
	}
	if errs := pluginValidateFormValue(fv, ps); len(errs) > 0 {
		t.Errorf("expected no errors, got %v", errs)
	}
}

func TestValidateFormValue_ForbiddenHandlebars(t *testing.T) {
	fv := map[string]interface{}{"body": "{{#if x}}yes{{/if}}"}
	errs := pluginValidateFormValue(fv, nil)
	if len(errs) == 0 {
		t.Fatal("expected forbidden Handlebars error")
	}
}

func TestValidateFormValue_UndefinedRef(t *testing.T) {
	fv := map[string]interface{}{"prompt": "{{input.typo}}"}
	ps := map[string]interface{}{
		"properties": map[string]interface{}{
			"text": map[string]interface{}{"type": "string", "description": "d"},
		},
	}
	errs := pluginValidateFormValue(fv, ps)
	found := false
	for _, e := range errs {
		if strings.Contains(e, "typo") && strings.Contains(e, "not defined") {
			found = true
		}
	}
	if !found {
		t.Errorf("expected undefined ref error for 'typo', got %v", errs)
	}
}

func TestValidateFormValue_UnconsumedParam(t *testing.T) {
	fv := map[string]interface{}{"prompt": "hello"}
	ps := map[string]interface{}{
		"properties": map[string]interface{}{
			"unused": map[string]interface{}{"type": "string", "description": "d"},
		},
	}
	errs := pluginValidateFormValue(fv, ps)
	found := false
	for _, e := range errs {
		if strings.Contains(e, "unused") && strings.Contains(e, "never referenced") {
			found = true
		}
	}
	if !found {
		t.Errorf("expected unconsumed param error, got %v", errs)
	}
}

func TestValidateFormValue_ParamsSchemaTypeValidation(t *testing.T) {
	fv := map[string]interface{}{"f": "{{input.x}}"}
	ps := map[string]interface{}{
		"properties": map[string]interface{}{
			"x": map[string]interface{}{"type": "number"},
		},
	}
	errs := pluginValidateFormValue(fv, ps)
	found := false
	for _, e := range errs {
		if strings.Contains(e, "number") && strings.Contains(e, "invalid") {
			found = true
		}
	}
	if !found {
		t.Errorf("expected type validation error, got %v", errs)
	}
}

func TestValidateFormValue_ArrayAutoFix(t *testing.T) {
	fv := map[string]interface{}{
		"files": []interface{}{"{{input.fileUrl}}"},
	}
	ps := map[string]interface{}{
		"properties": map[string]interface{}{
			"fileUrl": map[string]interface{}{
				"type": "array", "items": map[string]interface{}{"type": "string"},
				"description": "d",
			},
		},
	}
	errs := pluginValidateFormValue(fv, ps)
	if len(errs) != 0 {
		t.Errorf("expected no errors after auto-fix, got %v", errs)
	}
	// Verify auto-fix: array should be unwrapped to string
	if s, ok := fv["files"].(string); !ok || s != "{{input.fileUrl}}" {
		t.Errorf("expected auto-fix to unwrap array, got %v (%T)", fv["files"], fv["files"])
	}
}

func TestValidateFormValue_MissingDescription(t *testing.T) {
	fv := map[string]interface{}{"f": "{{input.x}}"}
	ps := map[string]interface{}{
		"properties": map[string]interface{}{
			"x": map[string]interface{}{"type": "string"},
		},
	}
	errs := pluginValidateFormValue(fv, ps)
	found := false
	for _, e := range errs {
		if strings.Contains(e, "missing description") {
			found = true
		}
	}
	if !found {
		t.Errorf("expected missing description error, got %v", errs)
	}
}

// --- helpers ---

func writeTestCapJSON(t *testing.T, dir, filename string, data map[string]interface{}) {
	t.Helper()
	b, err := json.Marshal(data)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, filename), b, 0o644); err != nil { //nolint:forbidigo
		t.Fatal(err)
	}
}
