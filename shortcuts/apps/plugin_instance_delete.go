// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/larksuite/cli/shortcuts/common"
)

// AppsPluginInstanceDelete deletes a plugin instance (capability JSON file).
// The operation is idempotent: deleting a non-existent instance is not an error.
var AppsPluginInstanceDelete = common.Shortcut{
	Service:     appsService,
	Command:     "+plugin-instance-delete",
	Description: "Delete a plugin instance",
	Risk: "write",
	Flags: []common.Flag{
		{Name: "id", Desc: "instance id", Required: true},
		{Name: "project-path", Desc: "project root path (defaults to current directory)"},
		{Name: "capabilities-dir", Desc: "explicit capabilities directory (relative to project or absolute)"},
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		id := strings.TrimSpace(rctx.Str("id"))
		projectPath, _ := pluginResolveProjectPath(rctx.Str("project-path"))
		capDir, _ := pluginResolveCapDir(projectPath, rctx.Str("capabilities-dir"))
		return common.NewDryRunAPI().
			Desc("Delete plugin instance (remove capability JSON, idempotent)").
			Set("action", "delete").
			Set("id", id).
			Set("target", filepath.Join(capDir, id+".json"))
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

		capPath := filepath.Join(capDir, id+".json")
		if err := os.Remove(capPath); err != nil && !os.IsNotExist(err) { //nolint:forbidigo // shortcuts cannot import internal/vfs; local file delete.
			return appsFileIOError(err, "cannot delete %s", capPath)
		}

		result := map[string]interface{}{
			"id":      id,
			"deleted": true,
		}
		rctx.OutFormat(result, nil, func(w io.Writer) {
			fmt.Fprintf(w, "✓ Plugin instance deleted: %s\n", id)
		})
		return nil
	},
}
