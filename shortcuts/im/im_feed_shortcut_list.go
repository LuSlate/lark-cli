// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package im

import (
	"context"

	"github.com/larksuite/cli/shortcuts/common"
)

// ImFeedShortcutList provides the +feed-shortcut-list shortcut for listing
// the current user's feed shortcuts. The latest OAPI contract returns the
// full list directly, so the shortcut intentionally exposes no pagination or
// detail-enrichment behavior.
var ImFeedShortcutList = common.Shortcut{
	Service:     "im",
	Command:     "+feed-shortcut-list",
	Description: "List the current user's feed shortcuts; user-only; returns the full CHAT shortcut list directly with no pagination or detail lookup",
	Risk:        "read",
	UserScopes:  []string{feedShortcutReadScope},
	AuthTypes:   []string{"user"},
	HasFormat:   true,
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		return common.NewDryRunAPI().GET("/open-apis/im/v2/feed_shortcuts")
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		data, err := runtime.DoAPIJSONTyped("GET", "/open-apis/im/v2/feed_shortcuts", nil, nil)
		if err != nil {
			return err
		}
		runtime.Out(data, nil)
		return nil
	},
}
