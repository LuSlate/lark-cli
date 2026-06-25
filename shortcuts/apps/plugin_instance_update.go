// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"path/filepath"
	"strings"
	"time"

	"github.com/larksuite/cli/shortcuts/common"
)

// AppsPluginInstanceUpdate updates an existing plugin instance's mutable fields
// (name, formValue, paramsSchema) while preserving immutable fields.
var AppsPluginInstanceUpdate = common.Shortcut{
	Service:     appsService,
	Command:     "+plugin-instance-update",
	Description: "Update a plugin instance (modify capability JSON)",
	Risk: "write",
	Flags: []common.Flag{
		{Name: "id", Desc: "instance id", Required: true},
		{Name: "name", Desc: "new display name"},
		{Name: "form-value", Desc: "new formValue JSON object", Input: []string{common.File, common.Stdin}},
		{Name: "params-schema", Desc: "new paramsSchema JSON object", Input: []string{common.File, common.Stdin}},
		{Name: "project-path", Desc: "project root path (defaults to current directory)"},
		{Name: "capabilities-dir", Desc: "explicit capabilities directory (relative to project or absolute)"},
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		id := strings.TrimSpace(rctx.Str("id"))
		projectPath, _ := pluginResolveProjectPath(rctx.Str("project-path"))
		capDir, _ := pluginResolveCapDir(projectPath, rctx.Str("capabilities-dir"))
		return common.NewDryRunAPI().
			Desc("Update plugin instance: merge partial updates to existing capability, validate formValue, write back, auto-regenerate TypeScript types").
			Set("action", "update").
			Set("id", id).
			Set("target", fmt.Sprintf("<capabilities_dir>/%s.json", id)).
			Set("output", filepath.Join(capDir, id+".json")).
			Set("types_output", filepath.Join(projectPath, "shared", "plugin-types.ts"))
	},
	Validate: func(ctx context.Context, rctx *common.RuntimeContext) error {
		id := strings.TrimSpace(rctx.Str("id"))
		if id == "" {
			return appsValidationParamError("--id", "--id is required")
		}
		hasUpdate := false
		if rctx.Changed("name") {
			hasUpdate = true
		}
		if fv := strings.TrimSpace(rctx.Str("form-value")); fv != "" {
			if err := pluginValidateJSONFlag("--form-value", fv); err != nil {
				return err
			}
			hasUpdate = true
		}
		if ps := strings.TrimSpace(rctx.Str("params-schema")); ps != "" {
			if err := pluginValidateJSONFlag("--params-schema", ps); err != nil {
				return err
			}
			hasUpdate = true
		}
		if !hasUpdate {
			return appsValidationError("at least one of --name, --form-value, or --params-schema must be provided")
		}
		projectPath, err := pluginResolveProjectPath(rctx.Str("project-path"))
		if err != nil {
			return err
		}
		return pluginCheckProjectDir(projectPath)
	},
	Execute: func(ctx context.Context, rctx *common.RuntimeContext) error {
		id := strings.TrimSpace(rctx.Str("id"))
		projectPath, err := pluginResolveProjectPath(rctx.Str("project-path"))
		if err != nil {
			return err
		}

		capDir, err := pluginResolveCapDir(projectPath, rctx.Str("capabilities-dir"))
		if err != nil {
			return err
		}

		cap, err := pluginGetCapability(capDir, id)
		if err != nil {
			return err
		}

		if rctx.Changed("name") {
			cap["name"] = strings.TrimSpace(rctx.Str("name"))
		}
		if fv := strings.TrimSpace(rctx.Str("form-value")); fv != "" {
			var formValue interface{}
			if err := json.Unmarshal([]byte(fv), &formValue); err != nil {
				return appsValidationParamError("--form-value", "invalid JSON: %v", err).WithCause(err)
			}
			cap["formValue"] = formValue
		}
		if ps := strings.TrimSpace(rctx.Str("params-schema")); ps != "" {
			var paramsSchema interface{}
			if err := json.Unmarshal([]byte(ps), &paramsSchema); err != nil {
				return appsValidationParamError("--params-schema", "invalid JSON: %v", err).WithCause(err)
			}
			cap["paramsSchema"] = paramsSchema
		}

		// Validate formValue against paramsSchema after merge
		if violations := pluginValidateFormValue(cap["formValue"], cap["paramsSchema"]); len(violations) > 0 {
			hint := strings.Join(violations, "\n- ")
			return appsValidationError("formValue validation failed:\n- %s", hint).
				WithHint("fix the issues above and retry")
		}

		cap["updatedAt"] = time.Now().UnixMilli()

		capPath := filepath.Join(capDir, id+".json")
		if err := pluginWriteCapJSON(capPath, cap); err != nil {
			return appsFileIOError(err, "cannot write %s", capPath)
		}

		// Auto-regenerate TypeScript types
		typesPath, typeNames, typesErr := pluginGenerateAndPersistTypes(projectPath, cap)

		result := map[string]interface{}{
			"id":        id,
			"pluginKey": cap["pluginKey"],
			"name":      cap["name"],
			"updatedAt": cap["updatedAt"],
		}
		if typesErr == nil {
			result["typesPath"] = typesPath
			result["types"] = typeNames
		}
		rctx.OutFormat(result, nil, func(w io.Writer) {
			fmt.Fprintf(w, "✓ Plugin instance updated: %s\n", id)
			if typesErr == nil {
				fmt.Fprintf(w, "  Types:   %s → %s\n", strings.Join(typeNames, ", "), typesPath)
			}
		})
		return nil
	},
}
