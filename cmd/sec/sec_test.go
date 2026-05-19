// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sec

import (
	"sort"
	"testing"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/core"
)

// TestNewCmdSec_HasAllSubcommands locks in the public command surface so a
// future refactor doesn't silently drop install/run/etc. The `update` verb
// was intentionally removed when lark-sec-cli took over its own upgrade
// lifecycle; if it ever needs to come back, add it here too.
func TestNewCmdSec_HasAllSubcommands(t *testing.T) {
	f, _, _, _ := cmdutil.TestFactory(t, &core.CliConfig{AppID: "a", AppSecret: "s"})
	cmd := NewCmdSec(f)

	var got []string
	for _, c := range cmd.Commands() {
		got = append(got, c.Name())
	}
	sort.Strings(got)
	want := []string{"config", "install", "run", "status", "stop"}
	if len(got) != len(want) {
		t.Fatalf("subcommands = %v, want %v", got, want)
	}
	for i, name := range want {
		if got[i] != name {
			t.Errorf("subcommands[%d] = %q, want %q", i, got[i], name)
		}
	}
}

// TestNewCmdSecInstall_FlagParsing follows the cmd/auth/auth_test pattern:
// inject runF, parse flags, assert opts captured them.
func TestNewCmdSecInstall_FlagParsing(t *testing.T) {
	f, _, _, _ := cmdutil.TestFactory(t, &core.CliConfig{AppID: "a", AppSecret: "s"})
	var got *InstallOptions
	cmd := NewCmdSecInstall(f, func(opts *InstallOptions) error {
		got = opts
		return nil
	})
	cmd.SetArgs([]string{"--force"})
	if err := cmd.Execute(); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if got == nil {
		t.Fatal("runF not invoked")
	}
	if !got.Force {
		t.Errorf("Force = false, want true")
	}
}
