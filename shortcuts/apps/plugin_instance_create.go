// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/larksuite/cli/shortcuts/common"
)

// AppsPluginInstanceCreate creates a plugin instance by writing a capability
// JSON file into the resolved capabilities directory.
var AppsPluginInstanceCreate = common.Shortcut{
	Service:     appsService,
	Command:     "+plugin-instance-create",
	Description: "Create a plugin instance (write capability JSON)",
	Risk: "write",
	Flags: []common.Flag{
		{Name: "id", Desc: "semantic instance id (lowercase + hyphens); auto-derived from plugin key if omitted"},
		{Name: "plugin", Desc: "plugin key@version (e.g. @official-plugins/ai-text-generate@1.0.0)", Required: true},
		{Name: "name", Desc: "display name for the instance", Required: true},
		{Name: "description", Desc: "instance description"},
		{Name: "form-value", Desc: "formValue JSON object", Required: true, Input: []string{common.File, common.Stdin}},
		{Name: "params-schema", Desc: "paramsSchema JSON object (optional)", Input: []string{common.File, common.Stdin}},
		{Name: "project-path", Desc: "project root path (defaults to current directory)"},
		{Name: "capabilities-dir", Desc: "explicit capabilities directory (relative to project or absolute)"},
		{Name: "force", Type: "bool", Desc: "overwrite existing instance with same id"},
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		pluginKey, pluginVersion, _ := pluginParseKeyVersion(rctx.Str("plugin"))
		id := strings.TrimSpace(rctx.Str("id"))
		if id == "" {
			id = pluginDeriveID(pluginKey)
		}
		return common.NewDryRunAPI().
			Desc("Create plugin instance (write capability JSON)").
			Set("action", "create").
			Set("id", id).
			Set("plugin", pluginKey+"@"+pluginVersion).
			Set("target", fmt.Sprintf("<capabilities_dir>/%s.json", id))
	},
	Validate: func(ctx context.Context, rctx *common.RuntimeContext) error {
		if _, _, err := pluginParseKeyVersion(rctx.Str("plugin")); err != nil {
			return err
		}
		if id := strings.TrimSpace(rctx.Str("id")); id != "" {
			if err := pluginValidateID(id); err != nil {
				return err
			}
		}
		if err := pluginValidateJSONFlag("--form-value", rctx.Str("form-value")); err != nil {
			return err
		}
		if ps := strings.TrimSpace(rctx.Str("params-schema")); ps != "" {
			if err := pluginValidateJSONFlag("--params-schema", ps); err != nil {
				return err
			}
		}
		projectPath, err := pluginResolveProjectPath(rctx.Str("project-path"))
		if err != nil {
			return err
		}
		return pluginCheckProjectDir(projectPath)
	},
	Execute: func(ctx context.Context, rctx *common.RuntimeContext) error {
		pluginKey, pluginVersion, err := pluginParseKeyVersion(rctx.Str("plugin"))
		if err != nil {
			return err
		}

		projectPath, err := pluginResolveProjectPath(rctx.Str("project-path"))
		if err != nil {
			return err
		}

		warnings, err := pluginCheckInstalledVersion(projectPath, pluginKey, pluginVersion)
		if err != nil {
			return err
		}

		capDir, err := pluginResolveCapDir(projectPath, rctx.Str("capabilities-dir"))
		if err != nil {
			return err
		}
		if err := os.MkdirAll(capDir, 0o755); err != nil { //nolint:forbidigo // shortcuts cannot import internal/vfs; auto-create capabilities dir.
			return appsFileIOError(err, "cannot create capabilities directory %s", capDir)
		}

		id := strings.TrimSpace(rctx.Str("id"))
		if id == "" {
			id = pluginDeriveID(pluginKey)
		}

		capPath := filepath.Join(capDir, id+".json")
		if !rctx.Bool("force") {
			if _, err := os.Stat(capPath); err == nil { //nolint:forbidigo // shortcuts cannot import internal/vfs; existence check before create.
				return appsValidationError("instance %q already exists at %s", id, pluginCapRelPath(projectPath, capPath)).
					WithHint("use --force to overwrite, or choose a different --id")
			}
		}

		var formValue interface{}
		if err := json.Unmarshal([]byte(rctx.Str("form-value")), &formValue); err != nil {
			return appsValidationParamError("--form-value", "invalid JSON: %v", err).WithCause(err)
		}

		now := time.Now().UnixMilli()
		cap := map[string]interface{}{
			"id":            id,
			"pluginKey":     pluginKey,
			"pluginVersion": pluginVersion,
			"name":          strings.TrimSpace(rctx.Str("name")),
			"description":   strings.TrimSpace(rctx.Str("description")),
			"formValue":     formValue,
			"createdAt":     now,
			"updatedAt":     now,
			"createdBy":     0,
		}

		var paramsSchema interface{}
		if ps := strings.TrimSpace(rctx.Str("params-schema")); ps != "" {
			if err := json.Unmarshal([]byte(ps), &paramsSchema); err != nil {
				return appsValidationParamError("--params-schema", "invalid JSON: %v", err).WithCause(err)
			}
			cap["paramsSchema"] = paramsSchema
		}

		// Validate formValue against paramsSchema (feida-ai 5-rule check)
		if violations := pluginValidateFormValue(formValue, paramsSchema); len(violations) > 0 {
			hint := strings.Join(violations, "\n- ")
			return appsValidationError("formValue validation failed:\n- %s", hint).
				WithHint("fix the issues above and retry")
		}

		if err := pluginWriteCapJSON(capPath, cap); err != nil {
			return appsFileIOError(err, "cannot write %s", capPath)
		}

		// Auto-generate TypeScript types
		typesPath, typeNames, typesErr := pluginGenerateAndPersistTypes(projectPath, cap)

		relPath := pluginCapRelPath(projectPath, capPath)
		result := map[string]interface{}{
			"id":            id,
			"pluginKey":     pluginKey,
			"pluginVersion": pluginVersion,
			"name":          cap["name"],
			"path":          relPath,
		}
		if len(warnings) > 0 {
			result["warnings"] = warnings
		}
		if typesErr == nil {
			result["typesPath"] = typesPath
			result["types"] = typeNames
		}
		rctx.OutFormat(result, nil, func(w io.Writer) {
			for _, w2 := range warnings {
				fmt.Fprintf(w, "⚠ %s\n", w2)
			}
			fmt.Fprintf(w, "✓ Plugin instance created: %s\n", id)
			fmt.Fprintf(w, "  Plugin:  %s@%s\n", pluginKey, pluginVersion)
			fmt.Fprintf(w, "  Path:    %s\n", relPath)
			if typesErr == nil {
				fmt.Fprintf(w, "  Types:   %s → %s\n", strings.Join(typeNames, ", "), typesPath)
			}
		})
		return nil
	},
}
