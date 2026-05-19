// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sec

import (
	"github.com/spf13/cobra"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/output"
	intsec "github.com/larksuite/cli/internal/sec"
)

// InstallOptions holds inputs for `lark-cli sec install`.
type InstallOptions struct {
	Factory *cmdutil.Factory
	Force   bool
}

// NewCmdSecInstall performs first-time bootstrap install of lark-sec-cli from
// the embedded release manifest. After install, lark-sec-cli is in charge of
// finding and applying its own updates — this command only handles the initial
// version-on-disk step.
func NewCmdSecInstall(f *cmdutil.Factory, runF func(*InstallOptions) error) *cobra.Command {
	opts := &InstallOptions{Factory: f}
	cmd := &cobra.Command{
		Use:   "install",
		Short: "Install lark-sec-cli (first-time bootstrap)",
		Long: `Install the lark-sec-cli release pinned by this lark-cli build.

The bootstrap manifest is embedded; no external release server is consulted.
Once installed, lark-sec-cli is responsible for its own upgrade lifecycle.

Re-running is a no-op when an install already exists. Use --force to re-pin
the install back to the version this lark-cli build ships (e.g. for repair).`,
		RunE: func(cmd *cobra.Command, args []string) error {
			if runF != nil {
				return runF(opts)
			}
			return runInstall(cmd, opts)
		},
	}
	cmd.Flags().BoolVar(&opts.Force, "force", false, "reinstall even when an install already exists")
	return cmd
}

func runInstall(cmd *cobra.Command, opts *InstallOptions) error {
	inst, paths, err := installer(opts.Factory)
	if err != nil {
		return output.Errorf(output.ExitInternal, "internal", "%v", err)
	}
	state, err := inst.Install(cmd.Context(), intsec.InstallOptions{
		Force: opts.Force,
	})
	if err != nil {
		return output.Errorf(output.ExitNetwork, "sec_install", "install lark-sec-cli: %v", err)
	}
	out := opts.Factory.IOStreams.ErrOut
	output.PrintSuccess(out,
		"lark-sec-cli "+state.Version+" installed (buildId="+state.BuildID+") at "+paths.BinaryPath())
	return nil
}
