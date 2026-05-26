// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package im

import "github.com/larksuite/cli/shortcuts/common"

// Shortcuts returns all legacy im shortcuts. ImMessagesSend has been migrated
// to the typed framework — see TypedShortcuts below.
func Shortcuts() []common.Shortcut {
	return []common.Shortcut{
		ImChatCreate,
		ImChatList,
		ImChatMessageList,
		ImChatSearch,
		ImChatUpdate,
		ImMessagesMGet,
		ImMessagesReply,
		ImMessagesResourcesDownload,
		ImMessagesSearch,
		ImThreadsMessagesList,
		ImFlagCreate,
		ImFlagCancel,
		ImFlagList,
	}
}

// TypedShortcuts returns the im shortcuts that have migrated to the new
// common.TypedShortcut[T] framework. Returned as []common.Mountable so the
// top-level shortcuts/register.go can mount them through the same pipeline
// it uses for legacy shortcuts.
//
// IMPORTANT: a shortcut MUST appear in exactly one of Shortcuts() /
// TypedShortcuts() — duplicating it across both slices would double-mount
// the cobra subcommand.
func TypedShortcuts() []common.Mountable {
	return []common.Mountable{
		ImMessagesSend,
	}
}
