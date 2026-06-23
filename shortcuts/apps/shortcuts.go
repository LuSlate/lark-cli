// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import "github.com/larksuite/cli/shortcuts/common"

// Shortcuts returns all apps domain shortcuts.
func Shortcuts() []common.Shortcut {
	return []common.Shortcut{
		AppsCreate,
		AppsUpdate,
		AppsList,
		AppsAccessScopeSet,
		AppsAccessScopeGet,
		AppsHTMLPublish,
		AppsInit,
		AppsReleaseCreate,
		AppsReleaseList,
		AppsReleaseGet,
		AppsEnvPull,
		withExtraTips(AppsLogList, "Tip: logs are online-only; keep --env omitted or set --env online."),
		withExtraTips(AppsLogGet, "Tip: logs are online-only; keep --env omitted or set --env online."),
		withExtraTips(AppsTraceList, "Tip: traces are online-only; keep --env omitted or set --env online."),
		withExtraTips(AppsTraceGet, "Tip: traces are online-only; keep --env omitted or set --env online."),
		withExtraTips(AppsMetricQuery, "Tip: metrics are online-only; keep --env omitted or set --env online."),
		withExtraTips(AppsAnalyticsQuery, "Tip: analytics are online-only; keep --env omitted or set --env online."),
		AppsEnvVarList,
		withExtraTips(AppsEnvVarSet, "Example: lark-cli apps +envvar-set --app-id <app_id> --env online --key FOO --value <value> --yes"),
		withExtraTips(AppsEnvVarDelete, "Tip: +envvar-delete is high-risk-write; only pass --yes after explicit confirmation."),
		AppsDBTableList,
		AppsDBTableGet,
		AppsDBExecute,
		AppsDBEnvCreate,
		AppsGitCredentialInit,
		AppsGitCredentialList,
		AppsGitCredentialRemove,
		AppsSessionCreate,
		AppsSessionList,
		AppsSessionGet,
		AppsSessionStop,
		AppsSessionMessagesList,
		AppsChat,
	}
}

func withExtraTips(sc common.Shortcut, tips ...string) common.Shortcut {
	sc.Tips = append(append([]string{}, sc.Tips...), tips...)
	return sc
}
