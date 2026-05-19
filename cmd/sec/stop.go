// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sec

import (
	"bytes"
	"fmt"
	"os/exec"

	"github.com/spf13/cobra"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/output"
	intsec "github.com/larksuite/cli/internal/sec"
)

// StopOptions holds inputs for `lark-cli sec stop`.
type StopOptions struct {
	Factory *cmdutil.Factory
}

// NewCmdSecStop disables and removes the lark-sec-cli user system service.
// Counterpart to `sec run` — internally invokes `lark-sec-cli service disable`,
// which uninstalls the launchd / systemd / VBS-watchdog registration.
//
// The daemon itself wipes ~/.lark-cli/sec_config.json on shutdown (see its
// --disable-on-exit flag, default true), so subsequent lark-cli runs route
// directly to the upstream API instead of dangling through a dead local proxy.
func NewCmdSecStop(f *cmdutil.Factory, runF func(*StopOptions) error) *cobra.Command {
	opts := &StopOptions{Factory: f}
	cmd := &cobra.Command{
		Use:   "stop",
		Short: "Disable and remove the lark-sec-cli user system service",
		RunE: func(cmd *cobra.Command, args []string) error {
			if runF != nil {
				return runF(opts)
			}
			return runStop(cmd, opts)
		},
	}
	return cmd
}

func runStop(cmd *cobra.Command, opts *StopOptions) error {
	_, paths, err := installer(opts.Factory)
	if err != nil {
		return output.Errorf(output.ExitInternal, "internal", "%v", err)
	}
	state, err := intsec.LoadState(paths.StateFile())
	if err != nil {
		return output.Errorf(output.ExitInternal, "internal", "load sec state: %v", err)
	}
	if state == nil {
		// Nothing on disk to stop — no-op.
		output.PrintSuccess(opts.Factory.IOStreams.ErrOut, "lark-sec-cli not installed; nothing to stop")
		return nil
	}

	out := opts.Factory.IOStreams.ErrOut
	args := []string{"service", "disable"}
	fmt.Fprintf(out, "Running: %s %v\n", state.BinaryPath, args)

	c := exec.CommandContext(cmd.Context(), state.BinaryPath, args...)
	var stdout, stderr bytes.Buffer
	c.Stdout = &stdout
	c.Stderr = &stderr
	if err := c.Run(); err != nil {
		return output.Errorf(output.ExitInternal, "sec_service_disable",
			"`lark-sec-cli service disable` failed: %v\nstderr: %s", err, stderr.String())
	}
	fmt.Fprint(out, stdout.String())
	output.PrintSuccess(out, "lark-sec-cli service disabled")
	return nil
}
