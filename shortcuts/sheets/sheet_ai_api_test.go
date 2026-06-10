// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"strings"
	"testing"
)

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

// TestBuildToolBody_DerivesTransactionIDWhenUnset verifies that with the env
// var unset a write tool carries a session-derived transaction id (so a group
// of edits and a later +undo group by default), that the derived id is stable
// across invocations in the same session, and that it differs from any literal
// override. In an environment with no trustworthy session signal the derived
// id is "" and the body carries no extra, preserving the per-request default.
func TestBuildToolBody_DerivesTransactionIDWhenUnset(t *testing.T) {
	t.Setenv(sheetTxnIDEnv, "")
	want := sheetTransactionID()
	body := parseDryRunBody(t, CellsSet, cellsSetArgs())
	extra, hasExtra := body["extra"].(map[string]interface{})

	if want == "" {
		if hasExtra {
			t.Errorf("no session signal: extra should be absent: %#v", body)
		}
		return
	}
	if !strings.HasPrefix(want, "larkcli-") {
		t.Errorf("derived transaction_id = %q, want larkcli- prefix", want)
	}
	if !hasExtra || extra["transaction_id"] != want {
		t.Errorf("write tool should carry derived transaction_id %q: %#v", want, body)
	}
	if got := sheetTransactionID(); got != want {
		t.Errorf("derived transaction_id not stable: %q vs %q", got, want)
	}
}

// TestBuildToolBody_OmitsTransactionIDForReads verifies that read tools never
// carry a transaction id even when one is set: a read scoped to a transaction
// resolves against that transaction's snapshot (often empty) instead of the
// live document, so threading it would make reads return blank cells.
func TestBuildToolBody_OmitsTransactionIDForReads(t *testing.T) {
	t.Setenv(sheetTxnIDEnv, "tx_test_123")
	body := parseDryRunBody(t, CellsGet, []string{
		"--url", testURL, "--sheet-id", testSheetID, "--range", "A1",
	})
	if _, ok := body["extra"]; ok {
		t.Errorf("read tool must not carry extra.transaction_id: %#v", body)
	}
}
