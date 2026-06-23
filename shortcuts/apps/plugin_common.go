// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"archive/tar"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/internal/validate"
)

// pluginIDPattern validates semantic instance ids: lowercase alphanumeric + hyphens,
// not starting or ending with a hyphen.
var pluginIDPattern = regexp.MustCompile(`^[a-z0-9]([a-z0-9-]*[a-z0-9])?$`)

// pluginResolveProjectPath resolves --project-path to an absolute path,
// defaulting to cwd when empty.
func pluginResolveProjectPath(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		cwd, err := os.Getwd() //nolint:forbidigo // shortcuts cannot import internal/vfs; cwd lookup is local-only and bounded.
		if err != nil {
			return "", errs.NewInternalError(errs.SubtypeUnknown, "cannot determine working directory: %v", err).WithCause(err)
		}
		return cwd, nil
	}
	if err := validate.RejectControlChars(raw, "--project-path"); err != nil {
		return "", err
	}
	return filepath.Clean(raw), nil
}

// pluginCheckProjectDir validates that projectPath contains a package.json.
func pluginCheckProjectDir(projectPath string) error {
	info, err := os.Stat(filepath.Join(projectPath, "package.json")) //nolint:forbidigo // shortcuts cannot import internal/vfs; local stat for project dir check.
	if err != nil {
		if os.IsNotExist(err) {
			return appsFailedPreconditionError("package.json not found in %s", projectPath).
				WithHint("run 'lark-cli apps +init' to initialize the project first")
		}
		return appsFileIOError(err, "cannot access package.json in %s", projectPath)
	}
	if !info.Mode().IsRegular() {
		return appsFailedPreconditionError("package.json in %s is not a regular file", projectPath)
	}
	return nil
}

// pluginResolveCapDir resolves the capabilities directory using a 4-level fallback:
//  1. capDirFlag (explicit --capabilities-dir)
//  2. MIAODA_CAPABILITIES_DIR env var
//  3. MIAODA_APP_TYPE env var (2→server/capabilities, 6→shared/capabilities)
//     3.5 Read .env.local for MIAODA_APP_TYPE
//  4. Detect by checking which directories exist under projectPath
func pluginResolveCapDir(projectPath, capDirFlag string) (string, error) {
	if dir := strings.TrimSpace(capDirFlag); dir != "" {
		if filepath.IsAbs(dir) {
			return dir, nil
		}
		return filepath.Join(projectPath, dir), nil
	}

	if dir := os.Getenv("MIAODA_CAPABILITIES_DIR"); dir != "" { //nolint:forbidigo // env-based config lookup is intentional.
		if filepath.IsAbs(dir) {
			return dir, nil
		}
		return filepath.Join(projectPath, dir), nil
	}

	// 3. MIAODA_APP_TYPE: only appType=6 (Modern) uses shared/; everything else uses server/
	appType := os.Getenv("MIAODA_APP_TYPE") //nolint:forbidigo // env-based config lookup is intentional.
	if appType == "" {
		appType = pluginReadEnvLocalValue(projectPath, "MIAODA_APP_TYPE")
	}
	if appType == "6" {
		return filepath.Join(projectPath, "shared", "capabilities"), nil
	}
	if appType != "" {
		return filepath.Join(projectPath, "server", "capabilities"), nil
	}

	// 4. Directory detection
	serverDir := filepath.Join(projectPath, "server", "capabilities")
	sharedDir := filepath.Join(projectPath, "shared", "capabilities")
	serverOK := pluginDirExists(serverDir)
	sharedOK := pluginDirExists(sharedDir)

	switch {
	case serverOK && sharedOK:
		return "", appsFailedPreconditionError(
			"ambiguous capabilities path: both server/capabilities/ and shared/capabilities/ exist",
		).WithHint("use --capabilities-dir to specify which capabilities directory to use")
	case serverOK:
		return serverDir, nil
	case sharedOK:
		return sharedDir, nil
	default:
		// Default to server/capabilities/ (most common app type)
		return filepath.Join(projectPath, "server", "capabilities"), nil
	}
}

// pluginReadEnvLocalValue reads a value from .env.local by key name.
func pluginReadEnvLocalValue(projectPath, key string) string {
	data, err := os.ReadFile(filepath.Join(projectPath, ".env.local")) //nolint:forbidigo // shortcuts cannot import internal/vfs; local env file read.
	if err != nil {
		return ""
	}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		k, v, ok := strings.Cut(line, "=")
		if !ok || strings.TrimSpace(k) != key {
			continue
		}
		v = strings.TrimSpace(v)
		v = strings.Trim(v, "\"'")
		return v
	}
	return ""
}

func pluginDirExists(path string) bool {
	info, err := os.Stat(path) //nolint:forbidigo // shortcuts cannot import internal/vfs; local dir existence check.
	return err == nil && info.IsDir()
}

// pluginReadCapJSON reads and parses a single capability JSON file.
func pluginReadCapJSON(path string) (map[string]interface{}, error) {
	data, err := os.ReadFile(path) //nolint:forbidigo // shortcuts cannot import internal/vfs; local capability file read.
	if err != nil {
		return nil, err
	}
	var cap map[string]interface{}
	if err := json.Unmarshal(data, &cap); err != nil {
		return nil, fmt.Errorf("invalid JSON in %s: %w", filepath.Base(path), err)
	}
	return cap, nil
}

// pluginListCapabilities reads all *.json files from capDir.
// Returns nil (not error) if the directory does not exist.
func pluginListCapabilities(capDir string) ([]map[string]interface{}, error) {
	entries, err := os.ReadDir(capDir) //nolint:forbidigo // shortcuts cannot import internal/vfs; local dir listing.
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, appsFileIOError(err, "cannot read capabilities directory %s", capDir)
	}

	var caps []map[string]interface{}
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		cap, err := pluginReadCapJSON(filepath.Join(capDir, entry.Name()))
		if err != nil {
			continue
		}
		caps = append(caps, cap)
	}
	return caps, nil
}

// pluginGetCapability reads a single capability by id from capDir.
// The file is expected at capDir/{id}.json.
func pluginGetCapability(capDir, id string) (map[string]interface{}, error) {
	path := filepath.Join(capDir, id+".json")
	cap, err := pluginReadCapJSON(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, appsValidationError("instance %q not found", id).
				WithHint("list instances with 'lark-cli apps +plugin-instance-list'")
		}
		return nil, appsFileIOError(err, "cannot read capability %s", path)
	}
	return cap, nil
}

// pluginReadManifest reads manifest.json from node_modules for the given pluginKey.
func pluginReadManifest(projectPath, pluginKey string) (map[string]interface{}, error) {
	path := filepath.Join(projectPath, "node_modules", pluginKey, "manifest.json")
	data, err := os.ReadFile(path) //nolint:forbidigo // shortcuts cannot import internal/vfs; local manifest read.
	if err != nil {
		return nil, err
	}
	var manifest map[string]interface{}
	if err := json.Unmarshal(data, &manifest); err != nil {
		return nil, fmt.Errorf("invalid manifest.json for %s: %w", pluginKey, err)
	}
	return manifest, nil
}

// pluginParseKeyVersion splits "key@version" into (key, version).
// The key may start with "@" (scoped npm package), so the split is at the last "@".
func pluginParseKeyVersion(s string) (string, string, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return "", "", appsValidationParamError("--plugin", "--plugin is required")
	}
	idx := strings.LastIndex(s, "@")
	if idx <= 0 {
		return "", "", appsValidationParamError("--plugin",
			"invalid format %q; expected key@version (e.g. @official-plugins/ai-text-generate@1.0.0)", s)
	}
	key, version := s[:idx], s[idx+1:]
	if key == "" || version == "" {
		return "", "", appsValidationParamError("--plugin",
			"invalid format %q; expected key@version", s)
	}
	return key, version, nil
}

// pluginDeriveID derives an instance id from a plugin key.
// "@official-plugins/ai-text-generate" → "official-plugins-ai-text-generate"
func pluginDeriveID(pluginKey string) string {
	id := strings.TrimPrefix(pluginKey, "@")
	id = strings.ReplaceAll(id, "/", "-")
	return id
}

// pluginValidateID checks that id is a valid semantic instance id.
func pluginValidateID(id string) error {
	if !pluginIDPattern.MatchString(id) {
		return appsValidationParamError("--id",
			"invalid id %q; must be lowercase alphanumeric with hyphens, not starting/ending with hyphen", id)
	}
	return nil
}

// pluginValidateJSONFlag checks that value is non-empty valid JSON.
func pluginValidateJSONFlag(flagName, value string) error {
	value = strings.TrimSpace(value)
	if value == "" {
		return appsValidationParamError(flagName, "%s value is required", flagName)
	}
	if !json.Valid([]byte(value)) {
		return appsValidationParamError(flagName, "%s must be valid JSON", flagName)
	}
	return nil
}

// pluginCheckInstalled verifies that the plugin package is installed in node_modules
// with a valid manifest.json. Distinguishes three failure cases:
//   - plugin directory does not exist → "not installed"
//   - plugin directory exists but manifest.json missing → "not built"
//   - other I/O error
func pluginCheckInstalled(projectPath, pluginKey string) error {
	pluginDir := filepath.Join(projectPath, "node_modules", pluginKey)
	manifestPath := filepath.Join(pluginDir, "manifest.json")
	if _, err := os.Stat(manifestPath); err != nil { //nolint:forbidigo // shortcuts cannot import internal/vfs; local stat for plugin check.
		if os.IsNotExist(err) {
			if pluginDirExists(pluginDir) {
				return appsFailedPreconditionError(
					"plugin %q exists in node_modules but manifest.json is missing; the package may not have been built correctly", pluginKey,
				).WithHint("run 'lark-cli apps +plugin-install --name %s' to reinstall from registry", pluginKey)
			}
			return appsFailedPreconditionError("plugin %q is not installed", pluginKey).
				WithHint("run 'lark-cli apps +plugin-install --name %s' to install", pluginKey)
		}
		return appsFileIOError(err, "cannot check plugin installation for %s", pluginKey)
	}
	return nil
}

// pluginCheckDependentInstances scans the capabilities directory for instances
// that reference the given pluginKey. Returns nil if none found, an error with
// the list of dependent instance ids if any exist, or the underlying I/O error.
func pluginCheckDependentInstances(projectPath, pluginKey, capDirFlag string) error {
	capDir, err := pluginResolveCapDir(projectPath, capDirFlag)
	if err != nil {
		// No capabilities directory → no instances can exist → no conflict.
		return nil
	}
	caps, err := pluginListCapabilities(capDir)
	if err != nil {
		// Cannot scan → best-effort, don't block.
		return nil
	}
	var deps []string
	for _, cap := range caps {
		if pk, _ := cap["pluginKey"].(string); pk == pluginKey {
			if id, _ := cap["id"].(string); id != "" {
				deps = append(deps, id)
			}
		}
	}
	if len(deps) == 0 {
		return nil
	}
	return appsFailedPreconditionError(
		"plugin %q is still referenced by %d instance(s): %s", pluginKey, len(deps), strings.Join(deps, ", "),
	).WithHint("delete these instances first (lark-cli apps +plugin-instance-delete --id <id> for each), clean up calling code and types, then retry uninstall")
}

// pluginCheckInstalledVersion checks that the plugin is installed and warns if
// the installed version differs from the declared version. Returns (warnings, error).
func pluginCheckInstalledVersion(projectPath, pluginKey, declaredVersion string) ([]string, error) {
	if err := pluginCheckInstalled(projectPath, pluginKey); err != nil {
		return nil, err
	}
	var warnings []string
	if installed := pluginInstalledVersion(projectPath, pluginKey); installed != "" && installed != declaredVersion {
		warnings = append(warnings, fmt.Sprintf(
			"installed version %s differs from declared %s; run 'lark-cli apps +plugin-install --name %s@%s' to update, or continue with the installed version",
			installed, declaredVersion, pluginKey, declaredVersion))
	}
	return warnings, nil
}

// ── formValue validation (aligned with feida-ai validatePluginInstance) ──

// Forbidden Handlebars block-level helpers.
var pluginForbiddenTemplatePatterns = []*regexp.Regexp{
	regexp.MustCompile(`\{\{#if\b`),
	regexp.MustCompile(`\{\{#each\b`),
	regexp.MustCompile(`\{\{#unless\b`),
	regexp.MustCompile(`\{\{/if\}\}`),
	regexp.MustCompile(`\{\{/each\}\}`),
	regexp.MustCompile(`\{\{/unless\}\}`),
	regexp.MustCompile(`\{\{else\}\}`),
}

// pluginInputRefPattern matches {{input.xxx}} template references.
var pluginInputRefPattern = regexp.MustCompile(`\{\{input\.(\w+)\}\}`)

// pluginTemplateRefExact matches a string that is exactly one {{input.xxx}} with no surrounding text.
var pluginTemplateRefExact = regexp.MustCompile(`^\{\{input\.(\w+)\}\}$`)

// pluginValidateFormValue validates formValue and paramsSchema following feida-ai's
// validatePluginInstance rules. Returns all violations; empty means valid.
// Also auto-fixes array double-wrapping in formValue (mutates fvMap in place).
func pluginValidateFormValue(formValue, paramsSchema interface{}) []string {
	var errors []string

	fvMap, _ := formValue.(map[string]interface{})

	// Rule 1: Forbidden Handlebars control syntax (recursive)
	pluginTraverseValues(formValue, "formValue", func(s, path string) {
		for _, pat := range pluginForbiddenTemplatePatterns {
			if pat.MatchString(s) {
				errors = append(errors, fmt.Sprintf("forbidden Handlebars syntax at %s: %s", path, pat.FindString(s)))
			}
		}
	})

	// If no paramsSchema provided, skip schema-dependent rules
	psMap, _ := paramsSchema.(map[string]interface{})
	properties, _ := psMap["properties"].(map[string]interface{})
	definedParams := make(map[string]bool, len(properties))
	for k := range properties {
		definedParams[k] = true
	}

	// Rule 2: paramsSchema property type validation
	allowedTypes := map[string]bool{"string": true, "array": true}
	allowedFormats := map[string]bool{"plugin-image-url": true, "plugin-file-url": true}
	for paramName, paramDef := range properties {
		def, ok := paramDef.(map[string]interface{})
		if !ok {
			continue
		}
		paramType, _ := def["type"].(string)
		if !allowedTypes[paramType] {
			errors = append(errors, fmt.Sprintf("paramsSchema property %q type %q is invalid; only string or array allowed", paramName, paramType))
		}
		if paramType == "array" {
			if _, hasItems := def["items"]; !hasItems {
				errors = append(errors, fmt.Sprintf("paramsSchema property %q is array but missing items", paramName))
			}
		}
		if f, ok := def["format"].(string); ok && !allowedFormats[f] {
			errors = append(errors, fmt.Sprintf("paramsSchema property %q format %q is invalid; only plugin-image-url or plugin-file-url allowed", paramName, f))
		}
		if _, hasDesc := def["description"]; !hasDesc {
			errors = append(errors, fmt.Sprintf("paramsSchema property %q missing description", paramName))
		}
	}

	// Rule 3: {{input.xxx}} references must exist in paramsSchema
	pluginTraverseValues(formValue, "formValue", func(s, path string) {
		for _, match := range pluginInputRefPattern.FindAllStringSubmatch(s, -1) {
			if !definedParams[match[1]] {
				errors = append(errors, fmt.Sprintf("{{input.%s}} at %s is not defined in paramsSchema", match[1], path))
			}
		}
	})

	// Rule 4: every paramsSchema property must be consumed by {{input.xxx}} in formValue
	if len(definedParams) > 0 && fvMap != nil {
		fvStr, _ := json.Marshal(fvMap)
		fvJSON := string(fvStr)
		for paramName := range definedParams {
			ref := "{{input." + paramName + "}}"
			if !strings.Contains(fvJSON, ref) {
				errors = append(errors, fmt.Sprintf("paramsSchema property %q is never referenced as %s in formValue", paramName, ref))
			}
		}
	}

	// Rule 5: array double-wrapping auto-fix
	// If paramsSchema declares a field as type:array, and formValue wraps it in
	// ["{{input.xxx}}"], auto-fix to "{{input.xxx}}" to prevent runtime [[val]] nesting.
	if fvMap != nil {
		arrayParams := make(map[string]bool)
		for paramName, paramDef := range properties {
			if def, ok := paramDef.(map[string]interface{}); ok {
				if t, _ := def["type"].(string); t == "array" {
					arrayParams[paramName] = true
				}
			}
		}
		if len(arrayParams) > 0 {
			pluginAutoFixArrayWrapping(fvMap, arrayParams)
		}
	}

	return errors
}

// pluginTraverseValues recursively visits all string leaf values in a nested
// structure (object / array / string), calling visitor for each.
func pluginTraverseValues(value interface{}, path string, visitor func(s, path string)) {
	switch v := value.(type) {
	case string:
		visitor(v, path)
	case []interface{}:
		for i, item := range v {
			pluginTraverseValues(item, fmt.Sprintf("%s[%d]", path, i), visitor)
		}
	case map[string]interface{}:
		for key, val := range v {
			pluginTraverseValues(val, path+"."+key, visitor)
		}
	}
}

// pluginAutoFixArrayWrapping fixes ["{{input.xxx}}"] → "{{input.xxx}}" for
// array-typed params to prevent runtime double-wrapping.
func pluginAutoFixArrayWrapping(obj map[string]interface{}, arrayParams map[string]bool) {
	for key, value := range obj {
		arr, ok := value.([]interface{})
		if ok && len(arr) == 1 {
			if s, ok := arr[0].(string); ok {
				if m := pluginTemplateRefExact.FindStringSubmatch(s); m != nil && arrayParams[m[1]] {
					obj[key] = s
				}
			}
		}
		if nested, ok := value.(map[string]interface{}); ok {
			pluginAutoFixArrayWrapping(nested, arrayParams)
		}
	}
}

// pluginWriteCapJSON writes a capability map to capDir/{id}.json atomically.
func pluginWriteCapJSON(capPath string, cap map[string]interface{}) error {
	data, err := json.MarshalIndent(cap, "", "  ")
	if err != nil {
		return appsFileIOError(err, "cannot marshal capability JSON")
	}
	data = append(data, '\n')
	return validate.AtomicWrite(capPath, data, 0o644)
}

// pluginCapRelPath returns the capability file path relative to projectPath.
func pluginCapRelPath(projectPath, capPath string) string {
	rel, err := filepath.Rel(projectPath, capPath)
	if err != nil {
		return capPath
	}
	return rel
}

// ── package.json helpers ──

// pluginReadPackageJSON reads and parses the project's package.json.
func pluginReadPackageJSON(projectPath string) (map[string]interface{}, error) {
	path := filepath.Join(projectPath, "package.json")
	data, err := os.ReadFile(path) //nolint:forbidigo // shortcuts cannot import internal/vfs; local package.json read.
	if err != nil {
		return nil, appsFileIOError(err, "cannot read package.json")
	}
	var pkg map[string]interface{}
	if err := json.Unmarshal(data, &pkg); err != nil {
		return nil, appsValidationError("invalid package.json: %v", err).WithCause(err)
	}
	return pkg, nil
}

// pluginWritePackageJSON writes package.json atomically, preserving formatting.
func pluginWritePackageJSON(projectPath string, pkg map[string]interface{}) error {
	data, err := json.MarshalIndent(pkg, "", "  ")
	if err != nil {
		return appsFileIOError(err, "cannot marshal package.json")
	}
	data = append(data, '\n')
	return validate.AtomicWrite(filepath.Join(projectPath, "package.json"), data, 0o644)
}

// pluginGetActionPlugins extracts actionPlugins from package.json as key→version.
func pluginGetActionPlugins(pkg map[string]interface{}) map[string]string {
	raw, ok := pkg["actionPlugins"]
	if !ok {
		return nil
	}
	m, ok := raw.(map[string]interface{})
	if !ok {
		return nil
	}
	out := make(map[string]string, len(m))
	for k, v := range m {
		if s, ok := v.(string); ok {
			out[k] = s
		}
	}
	return out
}

// pluginSetActionPlugin adds or updates a plugin entry in actionPlugins.
func pluginSetActionPlugin(pkg map[string]interface{}, key, version string) {
	m, ok := pkg["actionPlugins"].(map[string]interface{})
	if !ok {
		m = make(map[string]interface{})
		pkg["actionPlugins"] = m
	}
	m[key] = version
}

// pluginRemoveActionPlugin removes a plugin entry from actionPlugins.
func pluginRemoveActionPlugin(pkg map[string]interface{}, key string) {
	m, ok := pkg["actionPlugins"].(map[string]interface{})
	if !ok {
		return
	}
	delete(m, key)
}

// pluginSyncActionPlugins ensures the actionPlugins record in package.json
// matches the actually installed version, even when install is skipped.
func pluginSyncActionPlugins(projectPath, key, version string) {
	pkg, err := pluginReadPackageJSON(projectPath)
	if err != nil {
		return
	}
	ap := pluginGetActionPlugins(pkg)
	if ap[key] == version {
		return
	}
	pluginSetActionPlugin(pkg, key, version)
	_ = pluginWritePackageJSON(projectPath, pkg)
}

// pluginCheckPeerDeps reads peerDependencies from the installed plugin's
// package.json and returns the names of any that are missing from node_modules.
func pluginCheckPeerDeps(projectPath, pluginKey string) []string {
	pkgPath := filepath.Join(projectPath, "node_modules", pluginKey, "package.json")
	data, err := os.ReadFile(pkgPath) //nolint:forbidigo // shortcuts cannot import internal/vfs; local package read.
	if err != nil {
		return nil
	}
	var pkg map[string]interface{}
	if err := json.Unmarshal(data, &pkg); err != nil {
		return nil
	}
	peerDeps, ok := pkg["peerDependencies"].(map[string]interface{})
	if !ok || len(peerDeps) == 0 {
		return nil
	}
	var missing []string
	for dep := range peerDeps {
		depDir := filepath.Join(projectPath, "node_modules", dep)
		if !pluginDirExists(depDir) {
			missing = append(missing, dep)
		}
	}
	return missing
}

// pluginParseInstallTarget parses "key[@version]" where version is optional.
// For scoped packages like "@scope/name@1.0.0", the split is at the last "@".
func pluginParseInstallTarget(s string) (key string, version string) {
	s = strings.TrimSpace(s)
	if s == "" {
		return "", ""
	}
	idx := strings.LastIndex(s, "@")
	if idx <= 0 {
		return s, ""
	}
	return s[:idx], s[idx+1:]
}

// pluginInstalledVersion reads the version of an installed plugin from its
// package.json in node_modules. Returns "" if not found or unreadable.
func pluginInstalledVersion(projectPath, pluginKey string) string {
	path := filepath.Join(projectPath, "node_modules", pluginKey, "package.json")
	data, err := os.ReadFile(path) //nolint:forbidigo // shortcuts cannot import internal/vfs; local package read.
	if err != nil {
		return ""
	}
	var pkg map[string]interface{}
	if err := json.Unmarshal(data, &pkg); err != nil {
		return ""
	}
	v, _ := pkg["version"].(string)
	return v
}

// ── tgz extraction ──

// pluginExtractTGZ extracts a gzipped tar archive into destDir, stripping the
// first path component (npm convention: tarballs contain a "package/" prefix).
// Path traversal entries are silently skipped.
func pluginExtractTGZ(r io.Reader, destDir string) error {
	gz, err := gzip.NewReader(r)
	if err != nil {
		return fmt.Errorf("gzip: %w", err)
	}
	defer gz.Close()

	cleanDest := filepath.Clean(destDir) + string(filepath.Separator)
	tr := tar.NewReader(gz)
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return fmt.Errorf("tar: %w", err)
		}

		name := pluginStripFirstComponent(hdr.Name)
		if name == "" {
			continue
		}
		if strings.Contains(name, "..") {
			continue
		}

		target := filepath.Join(destDir, name)
		if !strings.HasPrefix(filepath.Clean(target)+string(filepath.Separator), cleanDest) &&
			filepath.Clean(target) != filepath.Clean(destDir) {
			continue
		}

		switch hdr.Typeflag {
		case tar.TypeDir:
			if err := os.MkdirAll(target, 0o755); err != nil { //nolint:forbidigo // shortcuts cannot import internal/vfs; tgz extraction.
				return err
			}
		case tar.TypeReg:
			if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil { //nolint:forbidigo
				return err
			}
			f, err := os.OpenFile(target, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, os.FileMode(hdr.Mode)&0o755) //nolint:forbidigo
			if err != nil {
				return err
			}
			if _, err := io.Copy(f, tr); err != nil { //nolint:gosec // bounded by tar entry size
				f.Close()
				return err
			}
			f.Close()
		}
	}
	return nil
}

// pluginStripFirstComponent removes the first path component ("package/foo" → "foo").
func pluginStripFirstComponent(name string) string {
	name = filepath.ToSlash(name)
	if i := strings.Index(name, "/"); i >= 0 {
		return name[i+1:]
	}
	return ""
}

// ── TypeScript type generation ──

const pluginTypesFile = "shared/plugin-types.ts"
const pluginBlockStartPrefix = "// ---- plugin:"
const pluginBlockEndPrefix = "// ---- end:"

// pluginGenerateAndPersistTypes reads manifest + capability, generates TypeScript
// interfaces, and writes them to shared/plugin-types.ts with per-id block replacement.
// Returns (outputPath, typeNames, error).
func pluginGenerateAndPersistTypes(projectPath string, cap map[string]interface{}) (string, []string, error) {
	pluginKey, _ := cap["pluginKey"].(string)
	id, _ := cap["id"].(string)
	name, _ := cap["name"].(string)
	if pluginKey == "" || id == "" {
		return "", nil, fmt.Errorf("capability missing pluginKey or id")
	}

	manifest, err := pluginReadManifest(projectPath, pluginKey)
	if err != nil {
		return "", nil, fmt.Errorf("cannot read manifest for %s: %w", pluginKey, err)
	}

	actions, _ := manifest["actions"].([]interface{})
	if len(actions) == 0 {
		return "", nil, fmt.Errorf("plugin %s has no actions defined", pluginKey)
	}

	prefix := pluginToPascalCase(id)
	var typeNames []string
	var parts []string
	parts = append(parts,
		"// ============================================================",
		fmt.Sprintf("// 插件 %s (%s) 的类型定义", id, name),
		"// 由 lark-cli +plugin-instance-types 自动生成",
		"// ============================================================",
	)

	paramsSchema, _ := cap["paramsSchema"].(map[string]interface{})

	for i, rawAction := range actions {
		action, ok := rawAction.(map[string]interface{})
		if !ok {
			continue
		}
		actionKey, _ := action["key"].(string)
		actionSuffix := ""
		if len(actions) > 1 {
			actionSuffix = pluginToPascalCase(actionKey)
		}
		inputName := prefix + actionSuffix + "Input"
		outputName := prefix + actionSuffix + "Output"

		// inputSchema: first action uses paramsSchema if available
		var inputSchema map[string]interface{}
		if i == 0 && paramsSchema != nil && len(paramsSchema) > 0 {
			inputSchema = paramsSchema
		} else {
			inputSchema, _ = action["inputSchema"].(map[string]interface{})
		}

		if inputSchema != nil {
			if iface := pluginGenerateInterface(inputName, inputSchema); iface != "" {
				parts = append(parts, "", iface)
				typeNames = append(typeNames, inputName)
			}
		}

		outputSchema, _ := action["outputSchema"].(map[string]interface{})
		if outputSchema != nil {
			if props, ok := outputSchema["properties"].(map[string]interface{}); ok && len(props) > 0 {
				keys := make([]string, 0, 3)
				for k := range props {
					if len(keys) < 3 {
						keys = append(keys, k)
					}
				}
				parts = append(parts, "",
					"/**",
					fmt.Sprintf(" * capabilityClient.load('%s').call<%s>('%s', input)", id, outputName, actionKey),
					fmt.Sprintf(" * const { %s } = result;", strings.Join(keys, ", ")),
					" */",
				)
			}
			if iface := pluginGenerateInterface(outputName, outputSchema); iface != "" {
				parts = append(parts, iface)
				typeNames = append(typeNames, outputName)
			}
		}
	}

	typesCode := strings.Join(parts, "\n")
	outputPath := filepath.Join(projectPath, pluginTypesFile)

	if err := pluginPersistTypesBlock(outputPath, id, typesCode); err != nil {
		return "", nil, err
	}

	return pluginTypesFile, typeNames, nil
}

// pluginToPascalCase converts "task-text-summary" → "TaskTextSummary".
// Handles digit-prefixed segments: "4s-store" → "FourSStore".
func pluginToPascalCase(id string) string {
	digitWords := map[byte]string{
		'0': "Zero", '1': "One", '2': "Two", '3': "Three", '4': "Four",
		'5': "Five", '6': "Six", '7': "Seven", '8': "Eight", '9': "Nine",
	}
	parts := strings.FieldsFunc(id, func(r rune) bool { return r == '-' || r == '_' })
	var result strings.Builder
	for _, part := range parts {
		if part == "" {
			continue
		}
		if part[0] >= '0' && part[0] <= '9' {
			i := 0
			for i < len(part) && part[i] >= '0' && part[i] <= '9' {
				if w, ok := digitWords[part[i]]; ok {
					result.WriteString(w)
				}
				i++
			}
			if i < len(part) {
				result.WriteByte(part[i] - 32) // uppercase
				result.WriteString(strings.ToLower(part[i+1:]))
			}
		} else {
			result.WriteByte(part[0] &^ 0x20) // uppercase first char
			result.WriteString(strings.ToLower(part[1:]))
		}
	}
	return result.String()
}

// pluginGenerateInterface generates "export interface Name { ... }" from a JSON Schema.
func pluginGenerateInterface(name string, schema map[string]interface{}) string {
	props, ok := schema["properties"].(map[string]interface{})
	if !ok || len(props) == 0 {
		return ""
	}
	requiredSet := make(map[string]bool)
	if req, ok := schema["required"].([]interface{}); ok {
		for _, r := range req {
			if s, ok := r.(string); ok {
				requiredSet[s] = true
			}
		}
	}
	var lines []string
	for key, val := range props {
		propMap, _ := val.(map[string]interface{})
		optional := ""
		if !requiredSet[key] {
			optional = "?"
		}
		tsType := pluginSchemaToTS(propMap, "  ")
		desc, _ := propMap["description"].(string)
		if desc != "" {
			lines = append(lines, fmt.Sprintf("  /** %s */", desc))
		}
		safeKey := pluginQuoteKey(key)
		lines = append(lines, fmt.Sprintf("  %s%s: %s;", safeKey, optional, tsType))
	}
	return fmt.Sprintf("export interface %s {\n%s\n}", name, strings.Join(lines, "\n"))
}

// pluginSchemaToTS converts a JSON Schema property to a TypeScript type string.
func pluginSchemaToTS(prop map[string]interface{}, indent string) string {
	if prop == nil {
		return "unknown"
	}
	t, _ := prop["type"].(string)
	switch t {
	case "string":
		return "string"
	case "number", "integer":
		return "number"
	case "boolean":
		return "boolean"
	case "array":
		if items, ok := prop["items"].(map[string]interface{}); ok {
			return pluginSchemaToTS(items, indent) + "[]"
		}
		return "unknown[]"
	case "object":
		if innerProps, ok := prop["properties"].(map[string]interface{}); ok && len(innerProps) > 0 {
			inner := indent + "  "
			var fields []string
			for k, v := range innerProps {
				vm, _ := v.(map[string]interface{})
				fields = append(fields, fmt.Sprintf("%s%s: %s;", inner, pluginQuoteKey(k), pluginSchemaToTS(vm, inner)))
			}
			return fmt.Sprintf("{\n%s\n%s}", strings.Join(fields, "\n"), indent)
		}
		return "Record<string, unknown>"
	}
	// No explicit type: infer from structure
	if _, ok := prop["properties"]; ok {
		return pluginSchemaToTS(map[string]interface{}{"type": "object", "properties": prop["properties"]}, indent)
	}
	if _, ok := prop["items"]; ok {
		return pluginSchemaToTS(map[string]interface{}{"type": "array", "items": prop["items"]}, indent)
	}
	return "unknown"
}

// pluginQuoteKey returns the key as-is if it's a valid JS identifier, else quoted.
func pluginQuoteKey(key string) string {
	clean := strings.Map(func(r rune) rune {
		if r == '\n' || r == '\r' || r == '\t' {
			return ' '
		}
		return r
	}, strings.TrimSpace(key))
	if regexp.MustCompile(`^[a-zA-Z_$][a-zA-Z0-9_$]*$`).MatchString(clean) {
		return clean
	}
	return "'" + strings.ReplaceAll(clean, "'", "\\'") + "'"
}

// pluginPersistTypesBlock writes a type block to the types file, replacing existing
// blocks for the same id or appending if new.
func pluginPersistTypesBlock(outputPath, id, typesCode string) error {
	blockStart := pluginBlockStartPrefix + id + " ----"
	blockEnd := pluginBlockEndPrefix + id + " ----"
	newBlock := blockStart + "\n" + typesCode + "\n" + blockEnd

	existing, err := os.ReadFile(outputPath) //nolint:forbidigo // shortcuts cannot import internal/vfs; local types file read.
	if err != nil && !os.IsNotExist(err) {
		return appsFileIOError(err, "cannot read %s", outputPath)
	}
	content := string(existing)

	var updated string
	if startIdx := strings.Index(content, blockStart); startIdx >= 0 {
		endIdx := strings.Index(content, blockEnd)
		if endIdx >= 0 {
			updated = content[:startIdx] + newBlock + content[endIdx+len(blockEnd):]
		} else {
			updated = content + "\n\n" + newBlock
		}
	} else if content != "" {
		updated = content + "\n\n" + newBlock
	} else {
		updated = newBlock + "\n"
	}

	if err := os.MkdirAll(filepath.Dir(outputPath), 0o755); err != nil { //nolint:forbidigo
		return appsFileIOError(err, "cannot create directory for %s", outputPath)
	}
	return validate.AtomicWrite(outputPath, []byte(updated), 0o644)
}
