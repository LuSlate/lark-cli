// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"context"
	"fmt"
	"io"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
)

// AppsPluginInstanceList lists all plugin instances (capability JSON files)
// in the resolved capabilities directory.
var AppsPluginInstanceList = common.Shortcut{
	Service:     appsService,
	Command:     "+plugin-instance-list",
	Description: "List all plugin instances in the project",
	Risk: "read",
	Flags: []common.Flag{
		{Name: "summary", Type: "bool", Desc: "show only id and name"},
		{Name: "project-path", Desc: "project root path (defaults to current directory)"},
		{Name: "capabilities-dir", Desc: "explicit capabilities directory (relative to project or absolute)"},
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		projectPath, _ := pluginResolveProjectPath(rctx.Str("project-path"))
		capDir, _ := pluginResolveCapDir(projectPath, rctx.Str("capabilities-dir"))
		return common.NewDryRunAPI().
			Desc("List plugin instances (scan capabilities directory)").
			Set("action", "list").
			Set("scan_dir", capDir).
			Set("summary", fmt.Sprintf("%v", rctx.Bool("summary")))
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

		capDir, err := pluginResolveCapDir(projectPath, rctx.Str("capabilities-dir"))
		if err != nil {
			// Cannot determine capabilities dir → no instances exist yet.
			rctx.OutFormat(
				map[string]interface{}{"instances": []interface{}{}},
				&output.Meta{Count: 0},
				func(w io.Writer) { fmt.Fprintln(w, "No plugin instances found.") },
			)
			return nil
		}

		caps, err := pluginListCapabilities(capDir)
		if err != nil {
			return err
		}

		summary := rctx.Bool("summary")
		instances := make([]interface{}, 0, len(caps))
		for _, cap := range caps {
			if summary {
				instances = append(instances, map[string]interface{}{
					"id":   cap["id"],
					"name": cap["name"],
				})
			} else {
				instances = append(instances, cap)
			}
		}

		data := map[string]interface{}{"instances": instances}
		rctx.OutFormat(data, &output.Meta{Count: len(instances)}, func(w io.Writer) {
			if len(instances) == 0 {
				fmt.Fprintln(w, "No plugin instances found.")
				return
			}
			rows := make([]map[string]interface{}, 0, len(caps))
			for _, cap := range caps {
				rows = append(rows, map[string]interface{}{
					"id":            cap["id"],
					"pluginKey":     cap["pluginKey"],
					"pluginVersion": cap["pluginVersion"],
					"name":          cap["name"],
				})
			}
			output.PrintTable(w, rows)
		})
		return nil
	},
}
