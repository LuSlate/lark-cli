// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package minutes

import (
	"context"
	"strings"
	"testing"
	"time"

	clie2e "github.com/larksuite/cli/tests/cli_e2e"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestMinutesDetail_DryRunWaitReady(t *testing.T) {
	setDryRunConfigEnv(t)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	t.Cleanup(cancel)

	result, err := clie2e.RunCmd(ctx, clie2e.Request{
		Args: []string{
			"minutes", "+detail",
			"--minute-tokens", "tok",
			"--summary",
			"--todo",
			"--wait-ready",
			"--dry-run",
		},
		DefaultAs: "user",
	})
	require.NoError(t, err)
	result.AssertExitCode(t, 0)

	output := result.Stdout
	assert.True(t, strings.Contains(output, "/open-apis/minutes/v1/minutes/{minute_token}"), "dry-run should contain metadata API path, got: %s", output)
	assert.True(t, strings.Contains(output, "/open-apis/minutes/v1/minutes/{minute_token}/artifacts"), "dry-run should contain artifacts API path, got: %s", output)
}
