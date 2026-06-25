// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"bytes"
	"io"
	"runtime"
	"strings"
	"testing"
)

// These benchmarks back the memory review of the sheets fan-out / download
// paths. They measure two hot spots:
//
//   1. fillCellsMatrix — fan-out shortcuts (+cells-set-style, +dropdown-set,
//      +cells-batch-set-style, +dropdown-update) expand one A1 range into a
//      rows×cols matrix of per-cell maps. A tiny input string ("A1:Z100000")
//      explodes into millions of heap maps with no upper bound.
//
//   2. the export-download reader — strings.NewReader(string(rawBody)) copies
//      the whole downloaded file once more before saving it.
//
// Run: go test ./shortcuts/sheets -run XXX -bench 'FillCellsMatrix|DownloadReader' -benchmem

var styleProto = map[string]interface{}{
	"cell_styles":   map[string]interface{}{"bold": true, "fg_color": "#FF0000"},
	"border_styles": map[string]interface{}{"top": map[string]interface{}{"style": "solid"}},
}

func benchFillCellsMatrix(b *testing.B, rows, cols int) {
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		m := fillCellsMatrix(rows, cols, styleProto)
		if len(m) != rows {
			b.Fatalf("bad matrix")
		}
	}
}

func BenchmarkFillCellsMatrix_100(b *testing.B)   { benchFillCellsMatrix(b, 10, 10) }     // A1:J10
func BenchmarkFillCellsMatrix_10K(b *testing.B)   { benchFillCellsMatrix(b, 1000, 10) }   // A1:J1000
func BenchmarkFillCellsMatrix_100K(b *testing.B)  { benchFillCellsMatrix(b, 10000, 10) }  // A1:J10000
func BenchmarkFillCellsMatrix_2600K(b *testing.B) { benchFillCellsMatrix(b, 100000, 26) } // A1:Z100000

// TestFanoutMatrixPeakMemory reports the concrete resident-heap delta of
// materializing a large fan-out matrix, so the review doc can quote real MB.
// Not an assertion — it prints numbers under `go test -v -run PeakMemory`.
func TestFanoutMatrixPeakMemory(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping memory probe in -short")
	}
	cases := []struct {
		name       string
		rows, cols int
	}{
		{"A1:Z10000 (260K cells)", 10000, 26},
		{"A1:Z100000 (2.6M cells)", 100000, 26},
	}
	for _, c := range cases {
		var before, after runtime.MemStats
		runtime.GC()
		runtime.ReadMemStats(&before)
		m := fillCellsMatrix(c.rows, c.cols, styleProto)
		runtime.ReadMemStats(&after)
		runtime.KeepAlive(m)
		t.Logf("%-26s heap +%6.1f MB  (%d total allocs)",
			c.name,
			float64(after.HeapAlloc-before.HeapAlloc)/(1024*1024),
			after.Mallocs-before.Mallocs)
	}
}

// --- export-download reader copy ---

func benchDownloadReader(b *testing.B, size int, useStringCopy bool) {
	raw := bytes.Repeat([]byte("x"), size)
	sink := make([]byte, 32*1024)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		var r io.Reader
		if useStringCopy {
			r = strings.NewReader(string(raw)) // current code: extra full-size copy
		} else {
			r = bytes.NewReader(raw) // fix: no copy
		}
		for {
			if _, err := r.Read(sink); err != nil {
				break
			}
		}
	}
}

// --- fan-out cell-budget cap (fix for the unbounded matrix blow-up) ---

func TestStampMatrixBudgetCap(t *testing.T) {
	// 49998 cells (1923×26) sits just under the 50000 cap → allowed.
	if err := checkStampMatrixBudget("range", "A1:Z1923", 1923, 26); err != nil {
		t.Fatalf("49998 cells should pass, got: %v", err)
	}
	// Exactly at the cap → allowed.
	if err := checkStampMatrixBudget("range", "A1:A50000", 50000, 1); err != nil {
		t.Fatalf("50000 cells (== cap) should pass, got: %v", err)
	}
	// Just over the cap → rejected.
	if err := checkStampMatrixBudget("range", "A1:A50001", 50001, 1); err == nil {
		t.Fatal("50001 cells should be rejected")
	}
	// The pathological case from the review (2.6M cells) → rejected.
	if err := checkStampMatrixBudget("ranges", "Sheet1!A1:Z100000", 100000, 26); err == nil {
		t.Fatal("2.6M-cell fan-out should be rejected")
	}
}

// BenchmarkStampBudget_RejectsOversized is the "after" side of the fix: the same
// A1:Z100000 input that BenchmarkFillCellsMatrix_2600K shows costing ~917MB /
// 5.3M allocs is now rejected up front, allocating only the error string.
func BenchmarkStampBudget_RejectsOversized(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		if err := checkStampMatrixBudget("range", "A1:Z100000", 100000, 26); err == nil {
			b.Fatal("expected rejection")
		}
	}
}

func BenchmarkDownloadReader_StringCopy_1MB(b *testing.B)  { benchDownloadReader(b, 1<<20, true) }
func BenchmarkDownloadReader_BytesNoCopy_1MB(b *testing.B) { benchDownloadReader(b, 1<<20, false) }
func BenchmarkDownloadReader_StringCopy_16MB(b *testing.B) { benchDownloadReader(b, 16<<20, true) }
func BenchmarkDownloadReader_BytesNoCopy_16MB(b *testing.B) {
	benchDownloadReader(b, 16<<20, false)
}
