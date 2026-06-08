// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import "testing"

// cellsSetArgs is a minimal valid +cells-set invocation used to inspect the
// tool-call request body.
func cellsSetArgs() []string {
	return []string{
		"--spreadsheet-token", testToken,
		"--sheet-id", testSheetID,
		"--range", "A1",
		"--cells", `[[{"value":"x"}]]`,
	}
}

// TestBuildToolBody_ThreadsTransactionID verifies that a session-stable
// transaction id from the environment is threaded into the request body's
// extra.transaction_id, so a group of edits and a later +undo share one undo
// stack.
func TestBuildToolBody_ThreadsTransactionID(t *testing.T) {
	t.Setenv(sheetTxnIDEnv, "tx_test_123")
	body := parseDryRunBody(t, CellsSet, cellsSetArgs())
	extra, ok := body["extra"].(map[string]interface{})
	if !ok {
		t.Fatalf("extra missing from body: %#v", body)
	}
	if extra["transaction_id"] != "tx_test_123" {
		t.Errorf("transaction_id = %#v, want tx_test_123", extra["transaction_id"])
	}
}

// TestBuildToolBody_OmitsTransactionIDWhenUnset verifies the body carries no
// extra when the env var is empty, preserving the per-request default.
func TestBuildToolBody_OmitsTransactionIDWhenUnset(t *testing.T) {
	t.Setenv(sheetTxnIDEnv, "")
	body := parseDryRunBody(t, CellsSet, cellsSetArgs())
	if _, ok := body["extra"]; ok {
		t.Errorf("extra should be absent when %s is unset: %#v", sheetTxnIDEnv, body)
	}
}
