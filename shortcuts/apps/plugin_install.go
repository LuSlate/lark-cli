// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	larkcore "github.com/larksuite/oapi-sdk-go/v3/core"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/shortcuts/common"
)

// AppsPluginInstall downloads a plugin package from the registry, extracts it
// to node_modules, and updates package.json actionPlugins.
//
// Without --name it batch-installs all plugins declared in actionPlugins that
// are not yet present in node_modules.
var AppsPluginInstall = common.Shortcut{
	Service:     appsService,
	Command:     "+plugin-install",
	Description: "Install a plugin package (download, extract, update package.json)",
	Risk:             "write",
	ConditionalScopes: []string{"spark:plugin:readonly"},
	AuthTypes:         []string{"user"},
	Flags: []common.Flag{
		{Name: "name", Desc: "plugin key[@version] (e.g. @official-plugins/ai-text-generate@1.0.0); omit to install all declared plugins"},
		{Name: "local", Desc: "install from a local .tgz file (dev/test only)", Hidden: true},
		{Name: "project-path", Desc: "project root path (defaults to current directory)"},
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		name := strings.TrimSpace(rctx.Str("name"))
		if name == "" {
			return common.NewDryRunAPI().
				POST(apiBasePath+"/plugins/-/versions/batch_get").
				Desc("Batch-install all declared plugins from package.json actionPlugins").
				Set("mode", "batch")
		}
		key, version := pluginParseInstallTarget(name)
		return common.NewDryRunAPI().
			POST(apiBasePath+"/plugins/-/versions/batch_get").
			Desc("Fetch plugin version metadata, then download .tgz package").
			Set("plugin_key", key).
			Set("version", version)
	},
	Validate: func(ctx context.Context, rctx *common.RuntimeContext) error {
		projectPath, err := pluginResolveProjectPath(rctx.Str("project-path"))
		if err != nil {
			return err
		}
		return pluginCheckProjectDir(projectPath)
	},
	Execute: func(ctx context.Context, rctx *common.RuntimeContext) error {
		projectPath, err := pluginResolveProjectPath(rctx.Str("project-path"))
		if err != nil {
			return err
		}

		if localTgz := strings.TrimSpace(rctx.Str("local")); localTgz != "" {
			return pluginInstallLocal(rctx, projectPath, localTgz)
		}

		name := strings.TrimSpace(rctx.Str("name"))
		if name == "" {
			return pluginInstallAll(ctx, rctx, projectPath)
		}
		return pluginInstallOne(ctx, rctx, projectPath, name)
	},
}

// pluginInstallOne installs a single plugin by key[@version].
func pluginInstallOne(ctx context.Context, rctx *common.RuntimeContext, projectPath, name string) error {
	key, version := pluginParseInstallTarget(name)
	if key == "" {
		return appsValidationParamError("--name", "invalid plugin name %q", name)
	}

	// Check if already installed with same version (pre-API fast path)
	if version != "" && version != "latest" {
		if installed := pluginInstalledVersion(projectPath, key); installed == version {
			pluginSyncActionPlugins(projectPath, key, version)
			result := map[string]interface{}{
				"key": key, "version": version, "status": "already_installed",
			}
			rctx.OutFormat(result, nil, func(w io.Writer) {
				fmt.Fprintf(w, "✓ %s@%s is already installed\n", key, version)
			})
			return nil
		}
	}

	// Resolve version via API
	resolvedVersion, downloadURL, approach, err := pluginResolveVersion(ctx, rctx, key, version)
	if err != nil {
		return err
	}

	// Post-API check: latest may resolve to the already-installed version
	if installed := pluginInstalledVersion(projectPath, key); installed == resolvedVersion {
		pluginSyncActionPlugins(projectPath, key, resolvedVersion)
		result := map[string]interface{}{
			"key": key, "version": resolvedVersion, "status": "already_installed",
		}
		rctx.OutFormat(result, nil, func(w io.Writer) {
			fmt.Fprintf(w, "✓ %s@%s is already up to date\n", key, resolvedVersion)
		})
		return nil
	}

	// Download tgz
	tgzData, err := pluginDownloadPackage(ctx, rctx, key, resolvedVersion, downloadURL, approach)
	if err != nil {
		return err
	}

	// Extract to node_modules
	destDir := filepath.Join(projectPath, "node_modules", key)
	if err := os.RemoveAll(destDir); err != nil { //nolint:forbidigo // shortcuts cannot import internal/vfs; clean before extract.
		return appsFileIOError(err, "cannot clean %s", destDir)
	}
	if err := os.MkdirAll(destDir, 0o755); err != nil { //nolint:forbidigo
		return appsFileIOError(err, "cannot create %s", destDir)
	}
	if err := pluginExtractTGZ(bytes.NewReader(tgzData), destDir); err != nil {
		return appsFileIOError(err, "cannot extract plugin package for %s", key)
	}

	// Check peer dependencies
	missingPeers := pluginCheckPeerDeps(projectPath, key)

	// Update package.json
	pkg, err := pluginReadPackageJSON(projectPath)
	if err != nil {
		return err
	}
	pluginSetActionPlugin(pkg, key, resolvedVersion)
	if err := pluginWritePackageJSON(projectPath, pkg); err != nil {
		return appsFileIOError(err, "cannot update package.json")
	}

	result := map[string]interface{}{
		"key": key, "version": resolvedVersion, "status": "installed",
	}
	if len(missingPeers) > 0 {
		result["missing_peer_dependencies"] = missingPeers
	}
	rctx.OutFormat(result, nil, func(w io.Writer) {
		fmt.Fprintf(w, "✓ Installed %s@%s\n", key, resolvedVersion)
		if len(missingPeers) > 0 {
			fmt.Fprintf(w, "⚠ Missing peer dependencies: %s\n", strings.Join(missingPeers, ", "))
			fmt.Fprintln(w, "  Run 'npm install' in the project directory to install them.")
		}
	})
	return nil
}

// pluginInstallAll installs all plugins declared in actionPlugins that are
// missing from node_modules.
func pluginInstallAll(ctx context.Context, rctx *common.RuntimeContext, projectPath string) error {
	pkg, err := pluginReadPackageJSON(projectPath)
	if err != nil {
		return err
	}
	declared := pluginGetActionPlugins(pkg)
	if len(declared) == 0 {
		rctx.OutFormat(map[string]interface{}{"installed": 0}, nil, func(w io.Writer) {
			fmt.Fprintln(w, "No plugins declared in package.json actionPlugins.")
		})
		return nil
	}

	var installed int
	for key, version := range declared {
		existing := pluginInstalledVersion(projectPath, key)
		if existing != "" && existing == version {
			continue
		}
		target := key + "@" + version
		if err := pluginInstallOne(ctx, rctx, projectPath, target); err != nil {
			return fmt.Errorf("install %s: %w", key, err)
		}
		installed++
	}

	if installed == 0 {
		rctx.OutFormat(map[string]interface{}{"installed": 0, "status": "all_up_to_date"}, nil, func(w io.Writer) {
			fmt.Fprintln(w, "All declared plugins are already installed.")
		})
	}
	return nil
}

// pluginInstallLocal installs a plugin from a local .tgz file, skipping API calls.
// Reads plugin key and version from the extracted package.json inside the tgz.
func pluginInstallLocal(rctx *common.RuntimeContext, projectPath, tgzPath string) error {
	tgzData, err := os.ReadFile(tgzPath) //nolint:forbidigo // shortcuts cannot import internal/vfs; local tgz read.
	if err != nil {
		return appsValidationParamError("--local", "cannot read tgz file %s: %v", tgzPath, err).WithCause(err)
	}

	// Extract to a temp dir first to read package.json
	tmpDir, err := os.MkdirTemp("", "plugin-local-*") //nolint:forbidigo
	if err != nil {
		return appsFileIOError(err, "cannot create temp dir")
	}
	defer os.RemoveAll(tmpDir) //nolint:forbidigo

	if err := pluginExtractTGZ(bytes.NewReader(tgzData), tmpDir); err != nil {
		return appsFileIOError(err, "cannot extract tgz")
	}

	// Read key and version from extracted package.json
	pkgData, err := os.ReadFile(filepath.Join(tmpDir, "package.json")) //nolint:forbidigo
	if err != nil {
		return appsFileIOError(err, "tgz does not contain package.json")
	}
	var pkgMeta map[string]interface{}
	if err := json.Unmarshal(pkgData, &pkgMeta); err != nil {
		return appsFileIOError(err, "invalid package.json in tgz")
	}
	key, _ := pkgMeta["name"].(string)
	version, _ := pkgMeta["version"].(string)
	if key == "" {
		return appsValidationParamError("--local", "package.json in tgz missing 'name' field")
	}
	if version == "" {
		version = "0.0.0"
	}

	// Move to node_modules
	destDir := filepath.Join(projectPath, "node_modules", key)
	if err := os.RemoveAll(destDir); err != nil { //nolint:forbidigo
		return appsFileIOError(err, "cannot clean %s", destDir)
	}
	if err := os.MkdirAll(filepath.Dir(destDir), 0o755); err != nil { //nolint:forbidigo
		return appsFileIOError(err, "cannot create parent dir for %s", destDir)
	}
	if err := os.Rename(tmpDir, destDir); err != nil { //nolint:forbidigo
		// rename may fail across filesystems; fall back to re-extract
		if err2 := os.MkdirAll(destDir, 0o755); err2 != nil { //nolint:forbidigo
			return appsFileIOError(err2, "cannot create %s", destDir)
		}
		if err2 := pluginExtractTGZ(bytes.NewReader(tgzData), destDir); err2 != nil {
			return appsFileIOError(err2, "cannot extract plugin to %s", destDir)
		}
	}

	// Update package.json actionPlugins
	pkg, err := pluginReadPackageJSON(projectPath)
	if err != nil {
		return err
	}
	pluginSetActionPlugin(pkg, key, version)
	if err := pluginWritePackageJSON(projectPath, pkg); err != nil {
		return appsFileIOError(err, "cannot update package.json")
	}

	result := map[string]interface{}{
		"key": key, "version": version, "status": "installed", "source": "local",
	}
	rctx.OutFormat(result, nil, func(w io.Writer) {
		fmt.Fprintf(w, "✓ Installed %s@%s (from local %s)\n", key, version, tgzPath)
	})
	return nil
}

// pluginResolveVersion calls the batch_get API to resolve download info.
// Returns resolved version, download URL, download approach ("inner"|"public").
func pluginResolveVersion(ctx context.Context, rctx *common.RuntimeContext, key, version string) (resolvedVersion, downloadURL, downloadApproach string, err error) {
	item := map[string]interface{}{"plugin_key": key}
	if version != "" {
		item["version"] = version
	}
	body := map[string]interface{}{
		"items": []interface{}{item},
	}

	data, err := rctx.CallAPITyped("POST", apiBasePath+"/plugins/-/versions/batch_get", nil, body)
	if err != nil {
		p, ok := errs.ProblemOf(err)
		if ok && p.Subtype == errs.SubtypeInvalidResponse {
			p.Message = fmt.Sprintf("plugin registry API is not available (returned non-JSON for %s)", key)
			p.Hint = "the plugin registry endpoint may not be registered yet; check with the backend team"
			return "", "", "", err
		}
		return "", "", "", withAppsHint(err, fmt.Sprintf("failed to fetch plugin version for %s; check plugin key spelling and network", key))
	}

	versions := pluginExtractVersionInfo(data, key)
	if len(versions) == 0 {
		return "", "", "", appsValidationError("no version found for plugin %q", key).
			WithHint("check plugin key and version")
	}

	first := versions[0]
	rv, _ := first["version"].(string)
	dl, _ := first["downloadURL"].(string)
	approach, _ := first["downloadApproach"].(string)
	if rv == "" {
		return "", "", "", appsValidationError("incomplete version info for plugin %q", key).
			WithHint("API returned version info without version; contact plugin maintainer")
	}
	return rv, dl, approach, nil
}

// pluginExtractVersionInfo extracts the version list for a key from the
// batch_get response. Handles both field names: "pluginVersions" (fullstack-cli
// inner API) and "pluginKeyToVersions" (OpenAPI design).
func pluginExtractVersionInfo(data map[string]interface{}, key string) []map[string]interface{} {
	var raw interface{}
	for _, field := range []string{"pluginVersions", "pluginKeyToVersions", "plugin_key_to_versions"} {
		if v, ok := data[field]; ok {
			raw = v
			break
		}
	}
	m, ok := raw.(map[string]interface{})
	if !ok {
		return nil
	}
	arr, ok := m[key].([]interface{})
	if !ok {
		return nil
	}
	out := make([]map[string]interface{}, 0, len(arr))
	for _, v := range arr {
		if vm, ok := v.(map[string]interface{}); ok {
			out = append(out, vm)
		}
	}
	return out
}

// pluginDownloadPackage downloads a plugin .tgz using the approach indicated by
// the batch_get API: "inner" uses an authenticated API call to the plugin
// package endpoint; "public" does a plain HTTP GET to the download URL.
// When approach is empty, it infers from the URL shape.
func pluginDownloadPackage(ctx context.Context, rctx *common.RuntimeContext, key, version, downloadURL, approach string) ([]byte, error) {
	switch approach {
	case "inner":
		apiPath := pluginBuildInnerDownloadPath(key, version)
		return pluginDownloadViaAPI(ctx, rctx, apiPath)
	case "public":
		if downloadURL == "" {
			return nil, appsValidationError("public download requires a downloadURL for %s@%s", key, version)
		}
		return pluginDownloadDirect(downloadURL)
	default:
		if downloadURL != "" && strings.HasPrefix(downloadURL, "http") {
			return pluginDownloadDirect(downloadURL)
		}
		apiPath := pluginBuildInnerDownloadPath(key, version)
		return pluginDownloadViaAPI(ctx, rctx, apiPath)
	}
}

// pluginBuildInnerDownloadPath constructs the API path for downloading a plugin
// package. For key "@scope/name", the path segments are scope and name.
func pluginBuildInnerDownloadPath(key, version string) string {
	scope, name := pluginSplitKey(key)
	return fmt.Sprintf("%s/plugins/%s/%s/versions/%s/package", apiBasePath, scope, name, version)
}

// pluginSplitKey splits "@scope/name" into ("@scope", "name").
func pluginSplitKey(key string) (string, string) {
	if idx := strings.Index(key, "/"); idx > 0 {
		return key[:idx], key[idx+1:]
	}
	return key, ""
}

func pluginDownloadViaAPI(ctx context.Context, rctx *common.RuntimeContext, apiPath string) ([]byte, error) {
	resp, err := rctx.DoAPIStream(ctx, &larkcore.ApiReq{
		HttpMethod: http.MethodGet,
		ApiPath:    apiPath,
	})
	if err != nil {
		return nil, appsFileIOError(err, "download failed: %s", apiPath)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, appsFileIOError(fmt.Errorf("HTTP %d", resp.StatusCode), "download failed: %s", apiPath)
	}
	return io.ReadAll(resp.Body)
}

func pluginDownloadDirect(url string) ([]byte, error) {
	resp, err := http.Get(url) //nolint:gosec,noctx // download URL from trusted API response
	if err != nil {
		return nil, appsFileIOError(err, "download failed: %s", common.TruncateStr(url, 120))
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, appsFileIOError(fmt.Errorf("HTTP %d", resp.StatusCode), "download failed")
	}
	return io.ReadAll(resp.Body)
}
