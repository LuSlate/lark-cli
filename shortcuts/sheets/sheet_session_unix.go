// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

//go:build !windows

package sheets

import (
	"os"
	"strconv"
	"syscall"
)

// sessionSignal returns a token that is stable across every process of one
// shell/login session and distinct across sessions, plus ok=false when no such
// signal is trustworthy.
//
// The POSIX session id (getsid) is preferred: every process in the same
// terminal/login session shares it, and unlike the parent pid it survives
// subshell wrapping (e.g. `sh -c "lark-cli ..."` spawned afresh per command),
// which is the common way an agent drives the CLI. It falls back to the parent
// pid, then gives up when the process was reparented to init (sid/ppid <= 1) —
// init is shared by unrelated processes and would over-group distinct callers.
func sessionSignal() (string, bool) {
	if sid, err := syscall.Getsid(0); err == nil && sid > 1 {
		return "sid:" + strconv.Itoa(sid), true
	}
	if ppid := os.Getppid(); ppid > 1 {
		return "ppid:" + strconv.Itoa(ppid), true
	}
	return "", false
}
