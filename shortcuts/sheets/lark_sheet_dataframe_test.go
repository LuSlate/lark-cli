// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/apache/arrow/go/v17/arrow"
	"github.com/apache/arrow/go/v17/arrow/array"
	"github.com/apache/arrow/go/v17/arrow/ipc"
	"github.com/apache/arrow/go/v17/arrow/memory"
	"github.com/larksuite/cli/shortcuts/common"
)

// buildArrowIPC writes one record into a Feather v2 (Arrow IPC file) blob.
// Used by the round-trip tests below to stand in for what
// `pandas.DataFrame.to_feather(path)` would produce; saves the tests from
// depending on a pandas-shaped fixture file.
//
// ipc.NewFileWriter wants an io.WriteSeeker (it back-patches a footer
// offset), so we write to a temp file and read the bytes back — simpler than
// re-implementing a seekable in-memory buffer.
func buildArrowIPC(t *testing.T, schema *arrow.Schema, build func(b *array.RecordBuilder)) []byte {
	t.Helper()
	mem := memory.NewGoAllocator()
	rb := array.NewRecordBuilder(mem, schema)
	defer rb.Release()
	build(rb)
	rec := rb.NewRecord()
	defer rec.Release()

	path := filepath.Join(t.TempDir(), "df.arrow")
	f, err := os.Create(path)
	if err != nil {
		t.Fatalf("create temp arrow file: %v", err)
	}
	w, err := ipc.NewFileWriter(f, ipc.WithSchema(schema), ipc.WithAllocator(mem))
	if err != nil {
		f.Close()
		t.Fatalf("ipc.NewFileWriter: %v", err)
	}
	if err := w.Write(rec); err != nil {
		t.Fatalf("write record: %v", err)
	}
	if err := w.Close(); err != nil {
		t.Fatalf("close writer: %v", err)
	}
	if err := f.Close(); err != nil {
		t.Fatalf("close file: %v", err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read temp arrow file: %v", err)
	}
	return data
}

// TestDataframe_RoundTripCoreTypes pins down the Arrow-schema → internal
// (type, format) mapping and the per-cell value shape that buildTypedCell
// expects: number cells are json.Number (precision-preserving), date cells
// are `yyyy-mm-dd` strings, bool/string come through verbatim. Numbers, dates,
// strings, bools, and nulls all in one record so a future Arrow-Go bump can't
// quietly regress any one family.
func TestDataframe_RoundTripCoreTypes(t *testing.T) {
	t.Parallel()

	schema := arrow.NewSchema([]arrow.Field{
		{Name: "name", Type: arrow.BinaryTypes.String},
		{Name: "qty", Type: arrow.PrimitiveTypes.Int64},
		{Name: "price", Type: arrow.PrimitiveTypes.Float64, Metadata: arrow.NewMetadata(
			[]string{"number_format"}, []string{"$#,##0.00"},
		)},
		{Name: "active", Type: arrow.FixedWidthTypes.Boolean},
		{Name: "shipped_on", Type: arrow.FixedWidthTypes.Date32},
	}, nil)

	jan15 := arrow.Date32FromTime(time.Date(2024, 1, 15, 0, 0, 0, 0, time.UTC))
	feb02 := arrow.Date32FromTime(time.Date(2024, 2, 2, 0, 0, 0, 0, time.UTC))

	buf := buildArrowIPC(t, schema, func(b *array.RecordBuilder) {
		b.Field(0).(*array.StringBuilder).AppendValues([]string{"alice", ""}, []bool{true, false})
		b.Field(1).(*array.Int64Builder).AppendValues([]int64{42, 0}, []bool{true, false})
		b.Field(2).(*array.Float64Builder).AppendValues([]float64{19.95, 0}, []bool{true, false})
		b.Field(3).(*array.BooleanBuilder).AppendValues([]bool{true, false}, []bool{true, true})
		b.Field(4).(*array.Date32Builder).AppendValues([]arrow.Date32{jan15, feb02}, []bool{true, true})
	})

	spec, err := decodeArrowToSheet(buf, "S1")
	if err != nil {
		t.Fatalf("decodeArrowToSheet: %v", err)
	}
	if spec.Name != "S1" {
		t.Errorf("sheet name = %q, want S1", spec.Name)
	}
	if len(spec.Columns) != 5 {
		t.Fatalf("got %d columns, want 5", len(spec.Columns))
	}
	want := []struct{ typ, format string }{
		{"string", "@"},
		{"number", ""},
		{"number", "$#,##0.00"},
		{"bool", ""},
		{"date", "yyyy-mm-dd"},
	}
	for i, w := range want {
		if spec.Columns[i].Type != w.typ {
			t.Errorf("columns[%d].Type = %q, want %q", i, spec.Columns[i].Type, w.typ)
		}
		if spec.Columns[i].Format != w.format {
			t.Errorf("columns[%d].Format = %q, want %q", i, spec.Columns[i].Format, w.format)
		}
	}

	if len(spec.Rows) != 2 {
		t.Fatalf("got %d rows, want 2", len(spec.Rows))
	}
	// Row 0: every field present, types match what buildTypedCell will accept.
	row0 := spec.Rows[0]
	if row0[0] != "alice" {
		t.Errorf("row0[name] = %#v, want \"alice\"", row0[0])
	}
	if n, ok := row0[1].(json.Number); !ok || n.String() != "42" {
		t.Errorf("row0[qty] = %#v, want json.Number(\"42\")", row0[1])
	}
	if n, ok := row0[2].(json.Number); !ok || n.String() != "19.95" {
		t.Errorf("row0[price] = %#v, want json.Number(\"19.95\")", row0[2])
	}
	if row0[3] != true {
		t.Errorf("row0[active] = %#v, want true", row0[3])
	}
	if row0[4] != "2024-01-15" {
		t.Errorf("row0[shipped_on] = %#v, want \"2024-01-15\"", row0[4])
	}

	// Row 1: nulls on name/qty/price (despite the buffer values) must become nil
	// so buildTypedCell paints an empty cell that still carries number_format.
	row1 := spec.Rows[1]
	for _, c := range []int{0, 1, 2} {
		if row1[c] != nil {
			t.Errorf("row1[%d] = %#v, want nil (null in arrow)", c, row1[c])
		}
	}
	if row1[3] != false {
		t.Errorf("row1[active] = %#v, want false", row1[3])
	}
	if row1[4] != "2024-02-02" {
		t.Errorf("row1[shipped_on] = %#v, want \"2024-02-02\"", row1[4])
	}
}

// TestDataframe_Timestamp pins the timestamp → date conversion for the
// timestamp[us] case (pandas default for `pd.Timestamp` columns once written
// via `to_feather`). Only the calendar date matters for our `yyyy-mm-dd`
// landing — guard against TZ drift from the wrong unit pick.
func TestDataframe_Timestamp(t *testing.T) {
	t.Parallel()
	schema := arrow.NewSchema([]arrow.Field{
		{Name: "ts", Type: &arrow.TimestampType{Unit: arrow.Microsecond}},
	}, nil)
	ts := arrow.Timestamp(time.Date(2024, 6, 12, 14, 30, 0, 0, time.UTC).UnixMicro())
	buf := buildArrowIPC(t, schema, func(b *array.RecordBuilder) {
		b.Field(0).(*array.TimestampBuilder).AppendValues([]arrow.Timestamp{ts}, []bool{true})
	})
	spec, err := decodeArrowToSheet(buf, "S")
	if err != nil {
		t.Fatal(err)
	}
	if spec.Columns[0].Type != "date" {
		t.Errorf("type = %q, want date", spec.Columns[0].Type)
	}
	if got := spec.Rows[0][0]; got != "2024-06-12" {
		t.Errorf("ts = %#v, want \"2024-06-12\"", got)
	}
}

// TestDataframe_EmptySchema rejects an Arrow file whose schema has no fields:
// a 0-column "DataFrame" would write a header-less, data-less block that
// validates as "writer ran successfully" but produces nothing — the test ties
// that off as an explicit error rather than letting it slip through.
func TestDataframe_EmptySchema(t *testing.T) {
	t.Parallel()
	schema := arrow.NewSchema(nil, nil)
	buf := buildArrowIPC(t, schema, func(b *array.RecordBuilder) {})
	_, err := decodeArrowToSheet(buf, "S")
	if err == nil || !strings.Contains(err.Error(), "no fields") {
		t.Errorf("err = %v, want 'no fields' error", err)
	}
}

// TestDataframe_DuplicateColumn catches duplicate-name columns at decode
// time. Validate already rejects duplicate column names for the JSON path;
// the Arrow path mirrors that so the error surfaces with the same shape.
func TestDataframe_DuplicateColumn(t *testing.T) {
	t.Parallel()
	schema := arrow.NewSchema([]arrow.Field{
		{Name: "x", Type: arrow.BinaryTypes.String},
		{Name: "x", Type: arrow.PrimitiveTypes.Int64},
	}, nil)
	buf := buildArrowIPC(t, schema, func(b *array.RecordBuilder) {
		b.Field(0).(*array.StringBuilder).Append("")
		b.Field(1).(*array.Int64Builder).Append(0)
	})
	_, err := decodeArrowToSheet(buf, "S")
	if err == nil || !strings.Contains(err.Error(), "duplicate") {
		t.Errorf("err = %v, want duplicate-column error", err)
	}
}

// TestDataframe_BadBytes rejects a non-Arrow blob with a hint pointing at
// pandas df.to_feather so users see what producer is expected without having
// to grep the docs.
func TestDataframe_BadBytes(t *testing.T) {
	t.Parallel()
	_, err := decodeArrowToSheet([]byte("not arrow"), "S")
	if err == nil || !strings.Contains(err.Error(), "Arrow") {
		t.Errorf("err = %v, want Arrow-decode error", err)
	}
}

// TestReadDataframeBytes_RejectsSecondStdinConsumer covers the case where another
// flag (e.g. --styles) has already consumed stdin via the common Input resolver:
// since --dataframe bypasses that resolver, the only thing keeping the two from
// racing for an empty stream is the explicit StdinConsumed() check in
// readDataframeBytes. Without that check, fangshuyu's report holds — both flags
// silently accept '-' and one of them sees empty bytes downstream.
func TestReadDataframeBytes_RejectsSecondStdinConsumer(t *testing.T) {
	// process-wide cache must be reset so the test isn't served from a prior run.
	saved := dataframeStdinCache
	dataframeStdinCache = nil
	t.Cleanup(func() { dataframeStdinCache = saved })

	rctx := &common.RuntimeContext{}
	rctx.MarkStdinConsumed()

	_, err := readDataframeBytes(rctx, "-")
	requireValidation(t, err, "stdin (-) can only be used by one flag")
}

// TestDataframe_EncodeRoundTrip checks --dataframe-out's encoder against its
// own decoder: build a +table-get-shaped sheet map (the same one
// readSheetAsSpec emits), encode to Arrow IPC, decode back via the put-side
// decoder, and require the column types / formats / row values to match. If
// any encoder choice drifts from what the decoder expects, the round-trip
// breaks here long before a real put → get round-trip in production would.
func TestDataframe_EncodeRoundTrip(t *testing.T) {
	t.Parallel()
	sheet := map[string]interface{}{
		"name":    "S1",
		"columns": []interface{}{"name", "qty", "price", "active", "ts"},
		"dtypes": map[string]interface{}{
			"name":   "object",
			"qty":    "float64",
			"price":  "float64",
			"active": "bool",
			"ts":     "datetime64[ns]",
		},
		"formats": map[string]interface{}{
			// `@` is the writer convention for string columns; readSheetAsSpec
			// strips it via isTextNumberFormat, so an Arrow file built from a
			// real read won't carry @ either. Keep it absent here to mirror
			// the production wire shape.
			"price": "$#,##0.00",
		},
		"data": []interface{}{
			[]interface{}{"alice", json.Number("42"), json.Number("19.95"), true, "2024-01-15"},
			[]interface{}{"bob", nil, json.Number("8.5"), false, "2024-02-02"},
		},
	}
	blob, err := encodeSheetMapToArrowIPC(sheet)
	if err != nil {
		t.Fatalf("encodeSheetMapToArrowIPC: %v", err)
	}
	spec, err := decodeArrowToSheet(blob, "S1")
	if err != nil {
		t.Fatalf("decodeArrowToSheet: %v", err)
	}
	wantTypes := []string{"string", "number", "number", "bool", "date"}
	wantFormats := []string{"@", "", "$#,##0.00", "", "yyyy-mm-dd"}
	if len(spec.Columns) != len(wantTypes) {
		t.Fatalf("got %d columns, want %d", len(spec.Columns), len(wantTypes))
	}
	for i, w := range wantTypes {
		if spec.Columns[i].Type != w {
			t.Errorf("columns[%d].Type = %q, want %q", i, spec.Columns[i].Type, w)
		}
		if spec.Columns[i].Format != wantFormats[i] {
			t.Errorf("columns[%d].Format = %q, want %q", i, spec.Columns[i].Format, wantFormats[i])
		}
	}
	if len(spec.Rows) != 2 {
		t.Fatalf("got %d rows, want 2", len(spec.Rows))
	}
	if spec.Rows[0][0] != "alice" {
		t.Errorf("row0[name] = %#v, want alice", spec.Rows[0][0])
	}
	if n, ok := spec.Rows[0][1].(json.Number); !ok || n.String() != "42" {
		t.Errorf("row0[qty] = %#v, want json.Number(\"42\")", spec.Rows[0][1])
	}
	if spec.Rows[0][3] != true {
		t.Errorf("row0[active] = %#v, want true", spec.Rows[0][3])
	}
	if spec.Rows[0][4] != "2024-01-15" {
		t.Errorf("row0[ts] = %#v, want 2024-01-15", spec.Rows[0][4])
	}
	// qty is null on row1, must come back as nil (not a zero-valued
	// json.Number that would later round-trip as 0).
	if spec.Rows[1][1] != nil {
		t.Errorf("row1[qty] = %#v, want nil (null arrow cell)", spec.Rows[1][1])
	}
}

// TestDataframe_EncodeAcceptsBothRowShapes pins the encoder against the two
// shapes `sheet["data"]` actually arrives in: `[][]interface{}` from a live
// readSheetAsSpec call (production), and `[]interface{}` from a JSON
// unmarshal (round-trip / fixtures). Either must produce non-empty Arrow
// output — early on the production shape silently fell through the
// `[]interface{}` type assertion and we shipped a 0-row Arrow blob.
func TestDataframe_EncodeAcceptsBothRowShapes(t *testing.T) {
	t.Parallel()
	base := func(data interface{}) map[string]interface{} {
		return map[string]interface{}{
			"name":    "S",
			"columns": []interface{}{"city"},
			"dtypes":  map[string]interface{}{"city": "object"},
			"data":    data,
		}
	}
	for label, data := range map[string]interface{}{
		"production [][]interface{}": [][]interface{}{{"BJ"}, {"SH"}},
		"unmarshal []interface{}":    []interface{}{[]interface{}{"BJ"}, []interface{}{"SH"}},
	} {
		blob, err := encodeSheetMapToArrowIPC(base(data))
		if err != nil {
			t.Errorf("%s: encode: %v", label, err)
			continue
		}
		spec, err := decodeArrowToSheet(blob, "S")
		if err != nil {
			t.Errorf("%s: decode: %v", label, err)
			continue
		}
		if len(spec.Rows) != 2 {
			t.Errorf("%s: got %d rows, want 2", label, len(spec.Rows))
		}
	}
}

// TestDataframe_DtypeToInternalType pins the inverse of typeToDtype so
// readSheetAsSpec's dtype labels recover the right internal type. Covers the
// dtype families +table-get emits today plus the safe fallback for unknown
// labels (string, lossless).
func TestDataframe_DtypeToInternalType(t *testing.T) {
	t.Parallel()
	cases := map[string]string{
		"float64":         "number",
		"int64":           "number",
		"Int64":           "number",
		"bool":            "bool",
		"boolean":         "bool",
		"datetime64[ns]":  "date",
		"datetime64[ms]":  "date",
		"object":          "string",
		"":                "string",
		"weird-new-dtype": "string",
	}
	for in, want := range cases {
		if got := dtypeToInternalType(in); got != want {
			t.Errorf("dtypeToInternalType(%q) = %q, want %q", in, got, want)
		}
	}
}

// TestDataframe_BytesWriterSeeker confirms the in-memory WriteSeeker handles
// the Seek-and-overwrite pattern ipc.NewFileWriter uses to patch the footer
// offset: write some bytes, seek back to the middle, overwrite, end up with
// the buffer reflecting the overwritten bytes (not a tail-extended duplicate).
func TestDataframe_BytesWriterSeeker(t *testing.T) {
	t.Parallel()
	var w bytesWriterSeeker
	if _, err := w.Write([]byte("hello world")); err != nil {
		t.Fatal(err)
	}
	if _, err := w.Seek(6, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := w.Write([]byte("WORLD")); err != nil {
		t.Fatal(err)
	}
	if got := string(w.buf); got != "hello WORLD" {
		t.Errorf("buf = %q, want \"hello WORLD\"", got)
	}
}
