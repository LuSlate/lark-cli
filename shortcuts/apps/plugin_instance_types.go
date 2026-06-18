// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"context"
	"fmt"
	"io"
	"strings"

	"github.com/larksuite/cli/shortcuts/common"
)

// AppsPluginInstanceTypes generates TypeScript type definitions from a plugin
// instance's paramsSchema and the plugin manifest's actions, and writes them
// to shared/plugin-types.ts with per-id block replacement.
var AppsPluginInstanceTypes = common.Shortcut{
	Service:     appsService,
	Command:     "+plugin-instance-types",
	Description: "Generate TypeScript types for a plugin instance",
	Risk:        "write",
	Flags: []common.Flag{
		{Name: "id", Desc: "instance id", Required: true},
		{Name: "project-path", Desc: "project root path (defaults to current directory)"},
		{Name: "capabilities-dir", Desc: "explicit capabilities directory (relative to project or absolute)"},
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		id := strings.TrimSpace(rctx.Str("id"))
		return common.NewDryRunAPI().
			Desc("Generate TypeScript types for plugin instance").
			Set("action", "types").
			Set("id", id).
			Set("output", pluginTypesFile)
	},
	Validate: func(ctx context.Context, rctx *common.RuntimeContext) error {
		if strings.TrimSpace(rctx.Str("id")) == "" {
			return appsValidationParamError("--id", "--id is required")
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

		outputPath, typeNames, err := pluginGenerateAndPersistTypes(projectPath, cap)
		if err != nil {
			return appsFileIOError(err, "failed to generate types for %s", id)
		}

		result := map[string]interface{}{
			"instanceId": id,
			"outputPath": outputPath,
			"types":      typeNames,
		}
		rctx.OutFormat(result, nil, func(w io.Writer) {
			fmt.Fprintf(w, "✓ Types generated for %s → %s\n", id, outputPath)
			for _, t := range typeNames {
				fmt.Fprintf(w, "  %s\n", t)
			}
		})
		return nil
	},
}
