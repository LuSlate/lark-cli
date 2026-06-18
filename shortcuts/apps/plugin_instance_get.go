// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"strings"

	"github.com/larksuite/cli/shortcuts/common"
)

// AppsPluginInstanceGet reads a single plugin instance (capability JSON) by id.
var AppsPluginInstanceGet = common.Shortcut{
	Service:     appsService,
	Command:     "+plugin-instance-get",
	Description: "Get a plugin instance by id",
	Risk: "read",
	Flags: []common.Flag{
		{Name: "id", Desc: "instance id (filename without .json in capabilities/)", Required: true},
		{Name: "project-path", Desc: "project root path (defaults to current directory)"},
		{Name: "capabilities-dir", Desc: "explicit capabilities directory (relative to project or absolute)"},
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		id := strings.TrimSpace(rctx.Str("id"))
		return common.NewDryRunAPI().
			Desc("Get plugin instance (read capability JSON)").
			Set("action", "get").
			Set("id", id).
			Set("source", fmt.Sprintf("<capabilities_dir>/%s.json", id))
	},
	Validate: func(ctx context.Context, rctx *common.RuntimeContext) error {
		id := strings.TrimSpace(rctx.Str("id"))
		if id == "" {
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

		rctx.OutFormat(cap, nil, func(w io.Writer) {
			pluginPrintInstance(w, cap)
		})
		return nil
	},
}

func pluginPrintInstance(w io.Writer, cap map[string]interface{}) {
	fmt.Fprintf(w, "ID:            %v\n", cap["id"])
	fmt.Fprintf(w, "Plugin:        %v\n", cap["pluginKey"])
	fmt.Fprintf(w, "Version:       %v\n", cap["pluginVersion"])
	fmt.Fprintf(w, "Name:          %v\n", cap["name"])

	if ts := common.FormatTime(cap["createdAt"]); ts != "" {
		fmt.Fprintf(w, "Created:       %s\n", ts)
	}
	if ts := common.FormatTime(cap["updatedAt"]); ts != "" {
		fmt.Fprintf(w, "Updated:       %s\n", ts)
	}

	if ps, ok := cap["paramsSchema"]; ok && ps != nil {
		b, _ := json.MarshalIndent(ps, "               ", "  ")
		fmt.Fprintf(w, "ParamsSchema:  %s\n", b)
	}
	if fv, ok := cap["formValue"]; ok && fv != nil {
		b, _ := json.MarshalIndent(fv, "               ", "  ")
		fmt.Fprintf(w, "FormValue:     %s\n", b)
	}
}
