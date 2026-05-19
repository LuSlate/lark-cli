// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

// Package sec exposes the `lark-cli sec` command tree that bootstraps the
// lark-sec-cli sidecar daemon: install, run, stop, status, and `config init`.
// The internal/sec package owns the implementation; this package is a thin
// Cobra wrapper that mirrors the conventions in cmd/auth.
//
// After bootstrap install, lark-sec-cli handles its own upgrade lifecycle —
// lark-cli is not in the update path, which is why there's no `sec update`
// subcommand here.
package sec

import (
	"github.com/spf13/cobra"

	"github.com/larksuite/cli/internal/cmdutil"
)

// NewCmdSec builds the parent `sec` command and registers all subcommands.
func NewCmdSec(f *cmdutil.Factory) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "sec",
		Short: "Manage the lark-sec-cli security sidecar (install, run, status)",
		Long: `Manage the lark-sec-cli security sidecar.

lark-sec-cli is a local HTTPS proxy daemon that intercepts lark-cli's traffic,
injects BDMS risk-control signatures, and manages credentials via the OS
keychain. These subcommands handle the install and runtime lifecycle from
lark-cli's side: bootstrap-install the daemon, run it in the background, and
wire the captured environment back into lark-cli. Updates after the first
install are managed by lark-sec-cli itself.`,
	}
	cmd.AddCommand(NewCmdSecInstall(f, nil))
	cmd.AddCommand(NewCmdSecRun(f, nil))
	cmd.AddCommand(NewCmdSecStop(f, nil))
	cmd.AddCommand(NewCmdSecStatus(f, nil))
	cmd.AddCommand(NewCmdSecConfig(f))
	return cmd
}
