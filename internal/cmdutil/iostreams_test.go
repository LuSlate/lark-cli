// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package cmdutil

import (
	"bytes"
	"os"
	"testing"
)

func TestStdoutIsTerminal(t *testing.T) {
	// Buffer-backed output (tests, captured output) is never a terminal.
	if (&IOStreams{Out: &bytes.Buffer{}}).StdoutIsTerminal() {
		t.Error("bytes.Buffer Out should not be a terminal")
	}
	// An os.Pipe write end is an *os.File but not a terminal — mirrors `cmd | jq`,
	// the case the stdin-based IsTerminal would get wrong.
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	defer r.Close()
	defer w.Close()
	if (&IOStreams{Out: w}).StdoutIsTerminal() {
		t.Error("os.Pipe Out should not be a terminal")
	}
}
