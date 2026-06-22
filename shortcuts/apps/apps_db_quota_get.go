// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"context"
	"fmt"
	"io"

	"github.com/larksuite/cli/shortcuts/common"
)

// AppsDBQuotaGet reports an app's database storage usage and object counts.
//
// GET /apps/{app_id}/db/quota。storage_quota_bytes / usage_percent 在配额未对接（=0）时
// 不输出（与 +file-quota-get 一致）；tables / views 始终输出。
var AppsDBQuotaGet = common.Shortcut{
	Service:     appsService,
	Command:     "+db-quota-get",
	Description: "Get an app's database storage usage",
	Risk:        "read",
	Tips: []string{
		"Example: lark-cli apps +db-quota-get --app-id <app_id>",
	},
	Scopes:    []string{"spark:app:read"},
	AuthTypes: []string{"user"},
	HasFormat: true,
	Flags: []common.Flag{
		{Name: "app-id", Desc: "Miaoda app id", Required: true},
		{Name: "env", Default: "online", Enum: []string{"dev", "online"}, Desc: "target db environment"},
	},
	Validate: func(ctx context.Context, rctx *common.RuntimeContext) error {
		_, err := requireAppID(rctx.Str("app-id"))
		return err
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		appID, _ := requireAppID(rctx.Str("app-id"))
		return common.NewDryRunAPI().
			GET(appDbQuotaPath(appID)).
			Desc("Get Miaoda app database storage usage").
			Params(map[string]interface{}{"env": rctx.Str("env")})
	},
	Execute: func(ctx context.Context, rctx *common.RuntimeContext) error {
		appID, err := requireAppID(rctx.Str("app-id"))
		if err != nil {
			return err
		}
		data, err := rctx.CallAPITyped("GET", appDbQuotaPath(appID), map[string]interface{}{"env": rctx.Str("env")}, nil)
		if err != nil {
			return withAppsHint(err, dbEnvMigrateHint)
		}
		// 配额未对接（storage_quota_bytes=0/缺失）时删掉 quota / usage_percent。
		if q, ok := numericAsFloat(data["storage_quota_bytes"]); !ok || q == 0 {
			delete(data, "storage_quota_bytes")
			delete(data, "usage_percent")
		}
		rctx.OutFormat(data, nil, func(w io.Writer) {
			renderDbQuotaPretty(w, data)
		})
		return nil
	},
}

// renderDbQuotaPretty 打 usage（已用 / 配额 (百分比)）与 tables / views 行。
func renderDbQuotaPretty(w io.Writer, data map[string]interface{}) {
	used := humanBytes(data["storage_used_bytes"])
	usage := used
	if q, ok := numericAsFloat(data["storage_quota_bytes"]); ok && q > 0 {
		pct := ""
		if p, ok := numericAsFloat(data["usage_percent"]); ok {
			pct = fmt.Sprintf(" (%.1f%%)", p)
		}
		usage = fmt.Sprintf("%s / %s%s", used, humanBytes(data["storage_quota_bytes"]), pct)
	}
	pairs := [][2]string{{"usage", usage}}
	if f, ok := numericAsFloat(data["tables"]); ok {
		pairs = append(pairs, [2]string{"tables", fmt.Sprintf("%d", int64(f))})
	}
	if f, ok := numericAsFloat(data["views"]); ok {
		pairs = append(pairs, [2]string{"views", fmt.Sprintf("%d", int64(f))})
	}
	renderKeyValuePairs(w, pairs)
}
