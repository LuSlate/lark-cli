// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package common

import (
	"bytes"
	"reflect"
	"strings"
	"testing"

	"github.com/spf13/cobra"

	"github.com/larksuite/cli/internal/cmdutil"
)

type helpDemoTarget struct {
	Chat *string `flag:"chat-id"`
	User *string `flag:"user-id"`
}

func (helpDemoTarget) OneOf() {}

type helpDemoArgs struct {
	Target helpDemoTarget
	Idemp  string `flag:"idempotency-key"`
}

func TestTypedHelp_RendersSections(t *testing.T) {
	t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())
	cmd := &cobra.Command{Use: "+demo", Short: "demo command"}
	cmdutil.SetRisk(cmd, "high-risk-write")
	cmdutil.SetTips(cmd, []string{"call carefully"})
	specs, err := walkArgs(reflect.TypeOf(&helpDemoArgs{}))
	if err != nil {
		t.Fatalf("walkArgs: %v", err)
	}
	cmd.SetHelpFunc(buildTypedHelp(specs, []HelpExample{{Title: "demo", Cmd: "--chat-id oc_x"}}))
	var buf bytes.Buffer
	cmd.SetOut(&buf)
	cmd.SetErr(&buf)
	cmd.HelpFunc()(cmd, nil)
	out := buf.String()
	for _, section := range []string{"CHOOSE ONE", "OPTIONAL", "EXAMPLES", "Risk:", "Tips:"} {
		if !strings.Contains(out, section) {
			t.Errorf("help missing %q section; got:\n%s", section, out)
		}
	}
}
