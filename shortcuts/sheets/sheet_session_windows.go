// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

//go:build windows

package sheets

import (
	"os"
	"strconv"
)

// sessionSignal returns a per-session grouping token. Windows has no POSIX
// session id, so the parent process id is the best portable signal; ok=false
// when the process has no real parent (ppid <= 1).
func sessionSignal() (string, bool) {
	if ppid := os.Getppid(); ppid > 1 {
		return "ppid:" + strconv.Itoa(ppid), true
	}
	return "", false
}
