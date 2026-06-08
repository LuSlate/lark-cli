// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/internal/util"
	"github.com/larksuite/cli/internal/validate"
	"github.com/larksuite/cli/shortcuts/common"
)

// sheetTxnIDEnv is the env var carrying a caller-provided, session-stable
// transaction id for sheet tool calls.
const sheetTxnIDEnv = "LARK_CLI_SHEET_TRANSACTION_ID"

// sheetTransactionID returns the session-stable transaction id from the
// environment, or "" when unset.
//
// Sheet write tools persist their reverse ("undo") changeset keyed by the
// request's transaction id; the server mints a fresh uuid per request when the
// caller supplies none, which isolates every CLI invocation into its own
// single-call undo stack. Threading one stable id across a group of edits (and
// a later +undo) is what lets +undo find and reverse those edits. An agent
// driving lark-cli sets this once per session; empty preserves today's
// per-request behavior.
func sheetTransactionID() string {
	return strings.TrimSpace(os.Getenv(sheetTxnIDEnv))
}

// ToolKind selects the One-OpenAPI endpoint and its rate-limit bucket.
//
//   - ToolKindRead  → POST .../tools/invoke_read   (scope sheets:spreadsheet:read,       10 qps)
//   - ToolKindWrite → POST .../tools/invoke_write  (scope sheets:spreadsheet:write_only,  5 qps)
type ToolKind string

const (
	ToolKindRead  ToolKind = "read"
	ToolKindWrite ToolKind = "write"
)

// toolInvokePath returns the full One-OpenAPI invoke path for the given
// spreadsheet token + tool kind. Network-free, safe in DryRun.
func toolInvokePath(token string, kind ToolKind) string {
	suffix := "invoke_read"
	if kind == ToolKindWrite {
		suffix = "invoke_write"
	}
	return fmt.Sprintf("/open-apis/sheet_ai/v2/spreadsheets/%s/tools/%s",
		validate.EncodePathSegment(token), suffix)
}

// buildToolBody constructs the One-OpenAPI request body for a tool invocation.
// `input` is serialized to a JSON string per the API contract; callers pass
// a typed Go map and never need to handle JSON encoding themselves.
func buildToolBody(toolName string, input map[string]interface{}) (map[string]interface{}, error) {
	inputJSON, err := json.Marshal(input)
	if err != nil {
		return nil, fmt.Errorf("encode tool input: %w", err)
	}
	body := map[string]interface{}{
		"tool_name": toolName,
		"input":     string(inputJSON),
	}
	// Thread a session-stable transaction id (when provided) so a group of
	// edits and a later +undo share one undo stack. Omitted when unset, leaving
	// the server to mint a per-request id as before.
	if txID := sheetTransactionID(); txID != "" {
		body["extra"] = map[string]interface{}{"transaction_id": txID}
	}
	return body, nil
}

// callTool invokes a sheet-ai tool via the One-OpenAPI endpoint and decodes
// the JSON-string `output` field into a generic Go value (typically
// map[string]interface{}). When the tool returns an empty `output`, callTool
// returns nil with no error.
//
// kind must match the tool's read/write classification — passing a read tool
// to invoke_write (or vice versa) results in a 403 from the gateway.
func callTool(
	ctx context.Context,
	runtime *common.RuntimeContext,
	token string,
	kind ToolKind,
	toolName string,
	input map[string]interface{},
) (interface{}, error) {
	body, err := buildToolBody(toolName, input)
	if err != nil {
		return nil, err
	}

	raw, err := runtime.RawAPI("POST", toolInvokePath(token, kind), nil, body)
	if err != nil {
		return nil, err
	}

	envelope, ok := raw.(map[string]interface{})
	if !ok {
		return nil, output.Errorf(output.ExitAPI, "tool_response",
			"tool %q: unexpected non-JSON-object response: %v", toolName, raw)
	}
	code, _ := util.ToFloat64(envelope["code"])
	if code != 0 {
		msg, _ := envelope["msg"].(string)
		return nil, output.ErrAPI(int(code), fmt.Sprintf("tool %q failed: [%d] %s", toolName, int(code), msg), envelope["error"])
	}
	data, _ := envelope["data"].(map[string]interface{})
	rawOutput, _ := data["output"].(string)
	if rawOutput == "" {
		return nil, nil
	}

	var out interface{}
	if err := json.Unmarshal([]byte(rawOutput), &out); err != nil {
		return nil, output.Errorf(output.ExitAPI, "tool_output",
			"tool %q returned invalid JSON output: %v", toolName, err)
	}
	return out, nil
}

// invokeToolDryRun renders the One-OpenAPI request the shortcut would send.
// The wire-format body (with input serialized to a JSON string) is preserved
// for fidelity, and a decoded tool_input map is surfaced alongside so humans
// don't have to mentally unmarshal the string field.
func invokeToolDryRun(
	token string,
	kind ToolKind,
	toolName string,
	input map[string]interface{},
) *common.DryRunAPI {
	wireBody, _ := buildToolBody(toolName, input)
	return common.NewDryRunAPI().
		POST(toolInvokePath(token, kind)).
		Body(wireBody).
		Set("spreadsheet_token", token).
		Set("tool_name", toolName).
		Set("tool_input", input)
}
