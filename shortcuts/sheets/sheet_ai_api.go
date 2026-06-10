// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/internal/util"
	"github.com/larksuite/cli/internal/validate"
	"github.com/larksuite/cli/shortcuts/common"
)

// sheetTxnIDEnv is the env var carrying a caller-provided, session-stable
// transaction id for sheet tool calls.
const sheetTxnIDEnv = "LARK_CLI_SHEET_TRANSACTION_ID"

// sheetTransactionID returns the session-stable transaction id threaded into a
// write tool call's extra.transaction_id.
//
// Sheet write tools persist their reverse ("undo") changeset keyed by the
// request's transaction id; the server mints a fresh uuid per request when the
// caller supplies none, which would isolate every CLI invocation into its own
// single-call undo stack. Sharing one stable id across a group of edits (and a
// later +undo) is what lets +undo find and reverse those edits.
//
// Resolution order:
//  1. $LARK_CLI_SHEET_TRANSACTION_ID — explicit caller override (highest).
//  2. else a value derived from this shell session (see
//     deriveSessionTransactionID) so a group of edits and a later +undo group
//     by default, with no env var to set.
//  3. else "" — the server mints a per-request id as before.
func sheetTransactionID() string {
	if v := strings.TrimSpace(os.Getenv(sheetTxnIDEnv)); v != "" {
		return v
	}
	return deriveSessionTransactionID()
}

// deriveSessionTransactionID builds a transaction id that is stable across the
// lark-cli invocations of one shell session and distinct across sessions, so a
// group of edits and a later +undo share an undo stack without the caller
// exporting LARK_CLI_SHEET_TRANSACTION_ID.
//
// Each lark-cli run is a fresh process and cannot mutate its parent's
// environment, so a *generated* id can't survive to the next command. Instead
// every run independently *recomputes* the same id from its own OS session —
// nothing is persisted between invocations.
//
// Returns "" when no trustworthy session signal exists (e.g. the process was
// reparented to init); the server then mints a per-request id and a
// missing-grouping +undo surfaces undone:0 rather than silently grouping
// unrelated callers. The grouping signal is a per-shell-session token
// (sessionSignal, platform-specific) salted with the uid and boot/host so a
// session id recycled after a reboot, or reused by a different user, can't
// collide with a stale undo stack.
func deriveSessionTransactionID() string {
	sig, ok := sessionSignal()
	if !ok {
		return ""
	}
	seed := strings.Join([]string{sig, strconv.Itoa(os.Getuid()), sessionSalt()}, "|")
	sum := sha256.Sum256([]byte(seed))
	return "larkcli-" + hex.EncodeToString(sum[:16])
}

// sessionSalt pins the derived id to this boot (Linux boot_id) or, failing
// that, this host, so a session id recycled after a reboot can't address a
// pre-reboot undo stack. Best-effort: an empty salt only weakens collision
// resistance across reboots, never correctness within a session.
func sessionSalt() string {
	if b, err := os.ReadFile("/proc/sys/kernel/random/boot_id"); err == nil {
		return strings.TrimSpace(string(b))
	}
	h, _ := os.Hostname()
	return h
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
func buildToolBody(kind ToolKind, toolName string, input map[string]interface{}) (map[string]interface{}, error) {
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
	// the server to mint a per-request id as before. Only write tools join the
	// undo transaction; reads must never carry it — a read scoped to a
	// transaction id resolves against that transaction's (often empty) snapshot
	// instead of the live document, so it would read back blank.
	if kind == ToolKindWrite {
		if txID := sheetTransactionID(); txID != "" {
			body["extra"] = map[string]interface{}{"transaction_id": txID}
		}
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
	body, err := buildToolBody(kind, toolName, input)
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
	wireBody, _ := buildToolBody(kind, toolName, input)
	return common.NewDryRunAPI().
		POST(toolInvokePath(token, kind)).
		Body(wireBody).
		Set("spreadsheet_token", token).
		Set("tool_name", toolName).
		Set("tool_input", input)
}
