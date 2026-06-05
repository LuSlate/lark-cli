// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"strings"
	"time"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
)

// ─── +table-put (cli-only, typed DataFrame-style import) ───────────
//
// Imports a typed, column-described table into Lark Sheets, type-faithfully:
// numbers stay numbers, dates land as real dates (serial + date number_format),
// not look-alike text. The wire protocol is deliberately a "table with column
// types" — pandas DataFrames are its most common producer, but the CLI never
// has to know about pandas.
//
// Writes into an existing spreadsheet (addressed by --url / --spreadsheet-token);
// to create a fresh workbook first, use +workbook-create, then point +table-put
// at the returned token. Multiple DataFrames → multiple sheets in one call: the
// top-level `sheets` array carries one entry per sub-sheet, each matched to an
// existing sub-sheet by name (created when absent).
//
// Date faithfulness was verified empirically (see isoDateToSerial): the only
// way to get a *real* date (ISNUMBER=TRUE, sortable / pivotable) is to write
// the Excel serial number AND set a date number_format. A date *string*, even
// with a date format, stays text — so date columns always go through the
// serial conversion below.

// TablePut is the typed table-put shortcut. It writes into an existing
// spreadsheet, composing get_workbook_structure / modify_workbook_structure /
// set_cell_range — no new backend tool, and no workbook creation (use
// +workbook-create for that, consistent with every other write shortcut).
var TablePut = common.Shortcut{
	Service:     "sheets",
	Command:     "+table-put",
	Description: "Write a typed table (columns with types + rows) into an existing spreadsheet; numbers and dates stay type-faithful.",
	Risk:        "write",
	Scopes:      []string{"sheets:spreadsheet:read", "sheets:spreadsheet:write_only"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+table-put"),
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if _, err := resolveSpreadsheetToken(runtime); err != nil {
			return err
		}
		_, err := parseTablePutPayload(runtime)
		return err
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		return tablePutDryRun(runtime)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		payload, err := parseTablePutPayload(runtime)
		if err != nil {
			return err
		}
		return tablePutWrite(ctx, runtime, token, payload, runtime.Bool("header-style"))
	},
	Tips: []string{
		"Writes into an existing spreadsheet — pass --url or --spreadsheet-token. To create a new workbook first, use +workbook-create, then point --spreadsheet-token here.",
		"Payload sheets are matched to existing sub-sheets by name (created when absent). Date columns take ISO yyyy-mm-dd strings — converted to real dates (serial + date format).",
	},
}

// ─── protocol ─────────────────────────────────────────────────────────

type tablePayload struct {
	Sheets []tableSheetSpec `json:"sheets"`
}

type tableSheetSpec struct {
	Name      string `json:"name"`
	StartCell string `json:"start_cell"`
	// Mode controls write placement: "overwrite" (default) writes a header+data
	// block from start_cell; "append" writes data below the sheet's existing
	// data (start_cell's row is ignored, its column is honored).
	Mode string `json:"mode"`
	// Header is whether to write a header row of column names. nil defaults by
	// mode: true for overwrite, false for append (so appended rows don't repeat
	// the header). Set explicitly to override.
	Header *bool `json:"header"`
	// AllowOverwrite, when explicitly false, makes the write fail if it would
	// land on a non-empty cell. nil defaults to true (overwrite).
	AllowOverwrite *bool             `json:"allow_overwrite"`
	Columns        []tableColumnSpec `json:"columns"`
	Rows           [][]interface{}   `json:"rows"`
}

type tableColumnSpec struct {
	Name   string `json:"name"`
	Type   string `json:"type"`
	Format string `json:"format"`
}

// parseTablePutPayload reads --sheets (JSON, supports @file / stdin) into a
// validated payload. UseNumber keeps numeric cells as json.Number so large
// integers (order IDs, etc.) survive without precision loss or scientific
// notation. Network-free: safe from Validate and DryRun.
func parseTablePutPayload(runtime flagView) (*tablePayload, error) {
	raw := strings.TrimSpace(runtime.Str("sheets"))
	if raw == "" {
		return nil, common.FlagErrorf("--sheets is required")
	}
	dec := json.NewDecoder(strings.NewReader(raw))
	dec.UseNumber()
	var p tablePayload
	if err := dec.Decode(&p); err != nil {
		return nil, common.FlagErrorf("--sheets: invalid JSON: %v", err)
	}
	if err := p.validate(); err != nil {
		return nil, err
	}
	return &p, nil
}

func (p *tablePayload) validate() error {
	if len(p.Sheets) == 0 {
		return common.FlagErrorf("--sheets: must contain at least one sheet")
	}
	seen := make(map[string]bool, len(p.Sheets))
	for i := range p.Sheets {
		s := &p.Sheets[i]
		if strings.TrimSpace(s.Name) == "" {
			return common.FlagErrorf("--sheets[%d]: name is required", i)
		}
		if seen[s.Name] {
			return common.FlagErrorf("--sheets[%d]: duplicate sheet name %q", i, s.Name)
		}
		seen[s.Name] = true
		if len(s.Columns) == 0 {
			return common.FlagErrorf("--sheets[%d] %q: columns must be non-empty", i, s.Name)
		}
		for j := range s.Columns {
			c := &s.Columns[j]
			if strings.TrimSpace(c.Name) == "" {
				return common.FlagErrorf("--sheets[%d] %q: columns[%d].name is required", i, s.Name, j)
			}
			if !validColumnType(c.Type) {
				return common.FlagErrorf("--sheets[%d] %q: columns[%d] %q has invalid type %q (want string/number/date/bool)",
					i, s.Name, j, c.Name, c.Type)
			}
		}
		for r := range s.Rows {
			if len(s.Rows[r]) != len(s.Columns) {
				return common.FlagErrorf("--sheets[%d] %q: row %d has %d cells, want %d (column count)",
					i, s.Name, r, len(s.Rows[r]), len(s.Columns))
			}
			// Validate each cell's value against its column type up front (pure,
			// network-free): a bad date/number/bool is caught here — before any
			// workbook is created — instead of failing mid-write and leaving a
			// stray empty spreadsheet behind.
			for c := range s.Columns {
				if _, err := buildTypedCell(&s.Columns[c], s.Rows[r][c]); err != nil {
					return common.FlagErrorf("--sheets[%d] %q: row %d column %q: %v", i, s.Name, r, s.Columns[c].Name, err)
				}
			}
		}
		if sc := strings.TrimSpace(s.StartCell); sc != "" {
			if _, _, ok := splitCellRef(sc); !ok {
				return common.FlagErrorf("--sheets[%d] %q: start_cell %q must be a single cell ref (e.g. A1)", i, s.Name, sc)
			}
		}
		switch s.Mode {
		case "", "overwrite", "append":
		default:
			return common.FlagErrorf("--sheets[%d] %q: mode %q is invalid (want \"overwrite\" or \"append\")", i, s.Name, s.Mode)
		}
	}
	return nil
}

func validColumnType(t string) bool {
	switch t {
	case "string", "number", "date", "bool":
		return true
	}
	return false
}

// ─── type mapping ─────────────────────────────────────────────────────

// headerOn reports whether a header row of column names should be written. A
// nil Header defaults by mode: overwrite writes it; append omits it so the
// appended rows don't repeat the header below an existing one.
func headerOn(s *tableSheetSpec) bool {
	if s.Header != nil {
		return *s.Header
	}
	return s.Mode != "append"
}

// buildSheetMatrix turns a sheet spec into the set_cell_range cells matrix:
// optionally a (bold-able) header row of column names, then one row per data
// record with each cell mapped by its column type. Per-column number_format is
// attached so numbers/dates render correctly (and dates become real dates).
func buildSheetMatrix(s *tableSheetSpec, headerStyle, writeHeader bool) ([][]interface{}, error) {
	ncols := len(s.Columns)
	matrix := make([][]interface{}, 0, len(s.Rows)+1)

	if writeHeader {
		header := make([]interface{}, ncols)
		for c := range s.Columns {
			cell := map[string]interface{}{"value": s.Columns[c].Name}
			if headerStyle {
				cell["cell_styles"] = map[string]interface{}{"font_weight": "bold"}
			}
			header[c] = cell
		}
		matrix = append(matrix, header)
	}

	for r := range s.Rows {
		row := make([]interface{}, ncols)
		for c := range s.Columns {
			cell, err := buildTypedCell(&s.Columns[c], s.Rows[r][c])
			if err != nil {
				return nil, common.FlagErrorf("sheet %q row %d column %q: %v", s.Name, r, s.Columns[c].Name, err)
			}
			row[c] = cell
		}
		matrix = append(matrix, row)
	}
	return matrix, nil
}

// buildTypedCell maps one raw JSON value to a set_cell_range cell per its
// declared column type. A nil (JSON null) becomes an empty cell that still
// carries the column's number_format. number values are kept as json.Number to
// preserve precision; dates are converted to Excel serials.
func buildTypedCell(col *tableColumnSpec, raw interface{}) (map[string]interface{}, error) {
	cell := map[string]interface{}{}
	nf := strings.TrimSpace(col.Format)
	if nf == "" {
		switch col.Type {
		case "date":
			nf = "yyyy-mm-dd"
		case "string":
			// Text format keeps digit-like strings (IDs / postcodes / phone numbers)
			// as text, and lets +table-get infer the column back as string instead
			// of guessing number from a numeric-looking value.
			nf = "@"
		}
	}
	if nf != "" {
		cell["cell_styles"] = map[string]interface{}{"number_format": nf}
	}
	if raw == nil {
		return cell, nil
	}
	switch col.Type {
	case "string":
		cell["value"] = stringifyCellValue(raw)
	case "number":
		n, ok := raw.(json.Number)
		if !ok {
			return nil, fmt.Errorf("number expects a numeric value, got %s", describeJSONType(raw))
		}
		cell["value"] = n
	case "bool":
		b, ok := raw.(bool)
		if !ok {
			return nil, fmt.Errorf("bool expects true/false, got %s", describeJSONType(raw))
		}
		cell["value"] = b
	case "date":
		str, ok := raw.(string)
		if !ok {
			return nil, fmt.Errorf("date expects an ISO yyyy-mm-dd string, got %s", describeJSONType(raw))
		}
		serial, err := isoDateToSerial(str)
		if err != nil {
			return nil, err
		}
		cell["value"] = serial
	default:
		return nil, fmt.Errorf("unsupported type %q", col.Type)
	}
	return cell, nil
}

// stringifyCellValue renders any JSON scalar as the literal text a string
// column should hold. json.Number keeps its exact digits (no scientific
// notation), so IDs / postcodes survive as written.
func stringifyCellValue(raw interface{}) string {
	switch v := raw.(type) {
	case string:
		return v
	case json.Number:
		return v.String()
	case bool:
		if v {
			return "TRUE"
		}
		return "FALSE"
	default:
		return fmt.Sprintf("%v", v)
	}
}

func describeJSONType(raw interface{}) string {
	switch raw.(type) {
	case string:
		return "a string"
	case json.Number:
		return "a number"
	case bool:
		return "a boolean"
	case []interface{}:
		return "an array"
	case map[string]interface{}:
		return "an object"
	default:
		return fmt.Sprintf("%T", raw)
	}
}

// excelEpoch is the Excel / Lark Sheets serial-date origin (1899-12-30 = 0).
// Verified empirically: writing serial 45306 renders as 2024-01-15 in Lark
// Sheets, matching Excel's 1900 date system exactly.
var excelEpoch = time.Date(1899, 12, 30, 0, 0, 0, 0, time.UTC)

// isoDateToSerial converts an ISO yyyy-mm-dd string to its Excel serial day
// number. The result is written as a numeric cell value with a date
// number_format, which is the only combination that yields a real (sortable,
// pivotable, ISNUMBER=TRUE) date in Lark Sheets.
func isoDateToSerial(s string) (int, error) {
	t, err := time.Parse("2006-01-02", strings.TrimSpace(s))
	if err != nil {
		return 0, fmt.Errorf("date %q must be ISO yyyy-mm-dd: %v", s, err)
	}
	return int(math.Round(t.Sub(excelEpoch).Hours() / 24)), nil
}

// ─── range helpers ────────────────────────────────────────────────────

// tablePutMaxCellsPerWrite caps a single set_cell_range write. Larger
// sheets are split into row batches so one oversized request can't exceed the
// tool's cell ceiling. Matches +cells-set's default --max-cells.
const tablePutMaxCellsPerWrite = 50000

// sheetAnchor returns the resolved start cell (default A1) and its 0-based
// column/row. Caller has already validated start_cell, so the parse can't fail
// in practice; the ok guard is defensive.
func sheetAnchor(s *tableSheetSpec) (anchor string, col0, row0 int, err error) {
	anchor = strings.TrimSpace(s.StartCell)
	if anchor == "" {
		anchor = "A1"
	}
	c, r, ok := splitCellRef(anchor)
	if !ok {
		return "", 0, 0, common.FlagErrorf("start_cell %q must be a single cell ref (e.g. A1)", anchor)
	}
	return anchor, c, r, nil
}

// tablePutFullRange is the A1 rectangle the whole matrix (header + data)
// occupies, for reporting in the result / dry-run.
func tablePutFullRange(s *tableSheetSpec, totalRows int) string {
	_, col0, row0, err := sheetAnchor(s)
	if err != nil {
		return strings.TrimSpace(s.StartCell)
	}
	ncols := len(s.Columns)
	return fmt.Sprintf("%s%d:%s%d",
		columnIndexToLetter(col0), row0+1,
		columnIndexToLetter(col0+ncols-1), row0+totalRows)
}

// ─── write path ───────────────────────────────────────────────────────

// writeSheetData writes one sheet's matrix via set_cell_range, splitting into
// row batches when the cell count would exceed tablePutMaxCellsPerWrite.
// Returns a per-sheet summary for the result envelope.
func writeSheetData(ctx context.Context, runtime *common.RuntimeContext, token, sheetID string, s *tableSheetSpec, headerStyle bool) (map[string]interface{}, error) {
	_, col0, row0, err := sheetAnchor(s)
	if err != nil {
		return nil, err
	}
	ncols := len(s.Columns)

	// append mode starts below the sheet's existing data; start_cell's row is
	// ignored (its column is still honored). overwrite mode anchors at row0.
	baseRow := row0
	writeHeader := headerOn(s)
	if s.Mode == "append" {
		lastRow, err := lastDataRow(ctx, runtime, token, sheetID)
		if err != nil {
			return nil, fmt.Errorf("resolving last data row for append: %w", err)
		}
		if lastRow > 0 {
			baseRow = lastRow // 0-based index of the row just below the 1-based last data row
		} else if s.Header == nil {
			// appending to an empty sheet with no explicit header choice: write the
			// header so column names aren't lost (and a later +table-get doesn't
			// consume the first data row as the header).
			writeHeader = true
		}
	}

	matrix, err := buildSheetMatrix(s, headerStyle, writeHeader)
	if err != nil {
		return nil, err
	}

	if len(matrix) == 0 {
		// header:false with no data rows — nothing to write.
		return map[string]interface{}{
			"name": s.Name, "sheet_id": sheetID, "range": "",
			"data_rows": 0, "columns": ncols, "writes": 0, "mode": writeModeName(s),
		}, nil
	}

	startCol := columnIndexToLetter(col0)
	endCol := columnIndexToLetter(col0 + ncols - 1)
	allowOverwrite := s.AllowOverwrite == nil || *s.AllowOverwrite

	rowsPerBatch := tablePutMaxCellsPerWrite / ncols
	if rowsPerBatch < 1 {
		rowsPerBatch = 1
	}

	writes := 0
	for start := 0; start < len(matrix); start += rowsPerBatch {
		end := start + rowsPerBatch
		if end > len(matrix) {
			end = len(matrix)
		}
		batchRange := fmt.Sprintf("%s%d:%s%d", startCol, baseRow+start+1, endCol, baseRow+end)
		input := map[string]interface{}{
			"excel_id": token,
			"sheet_id": sheetID,
			"range":    batchRange,
			"cells":    matrix[start:end],
		}
		if !allowOverwrite {
			input["allow_overwrite"] = false
		}
		if _, err := callTool(ctx, runtime, token, ToolKindWrite, "set_cell_range", input); err != nil {
			return nil, fmt.Errorf("writing rows %d-%d: %w", start+1, end, err)
		}
		writes++
	}
	return map[string]interface{}{
		"name":      s.Name,
		"sheet_id":  sheetID,
		"range":     fmt.Sprintf("%s%d:%s%d", startCol, baseRow+1, endCol, baseRow+len(matrix)),
		"data_rows": len(s.Rows),
		"columns":   ncols,
		"writes":    writes,
		"mode":      writeModeName(s),
	}, nil
}

// writeModeName normalizes the sheet's write mode to a non-empty label for
// result / dry-run reporting ("" defaults to "overwrite").
func writeModeName(s *tableSheetSpec) string {
	if s.Mode == "append" {
		return "append"
	}
	return "overwrite"
}

// lastDataRow returns the 1-based row number of the last row containing data in
// the sheet (0 when empty), so append mode can place new rows just below it. It
// reads current_region via get_range_as_csv — the backend's reported true data
// extent — anchored at A1.
func lastDataRow(ctx context.Context, runtime *common.RuntimeContext, token, sheetID string) (int, error) {
	out, err := callTool(ctx, runtime, token, ToolKindRead, "get_range_as_csv", map[string]interface{}{
		"excel_id": token,
		"sheet_id": sheetID,
		"range":    "A1",
		"max_rows": unboundedReadLimit,
	})
	if err != nil {
		return 0, err
	}
	m, ok := out.(map[string]interface{})
	if !ok {
		return 0, nil // empty sheet — no output
	}
	region, _ := m["current_region"].(string)
	if region == "" {
		region, _ = m["actual_range"].(string)
	}
	return a1EndRow(region), nil
}

// writeTypedSheets writes a typed payload's sheets into a workbook and returns
// the per-sheet summaries. It deliberately does not emit output — the caller
// composes the envelope, because +table-put and +workbook-create report
// different top-level shapes (a bare token vs. the full spreadsheet metadata).
// Existing sub-sheets are matched by name in a single structure read; missing
// ones are created on demand.
//
// adoptSheetID, when non-empty, is the id of a freshly created workbook's
// default sub-sheet: the first payload sheet adopts it (the default sheet is
// renamed to that sheet's name and reused) so the new workbook isn't left with
// a stray empty "Sheet1" beside the typed sheets. +table-put passes "" (it
// writes into an existing workbook, with no default sheet to adopt);
// +workbook-create passes the default sheet's id.
//
// On failure it returns the summaries written so far alongside the error, so
// the caller can surface a partial_success.
func writeTypedSheets(ctx context.Context, runtime *common.RuntimeContext, token string, payload *tablePayload, headerStyle bool, adoptSheetID string) ([]interface{}, error) {
	byName, err := listSheetIDsByName(ctx, runtime, token)
	if err != nil {
		return nil, err
	}

	// Adopt the default sheet as the first payload sheet (rename + reuse), so a
	// just-created workbook doesn't keep its empty default sheet around. Skip if
	// a sheet by that name already exists (it'll be matched normally below).
	if adoptSheetID != "" && len(payload.Sheets) > 0 {
		first := payload.Sheets[0].Name
		if _, exists := byName[first]; !exists {
			if err := renameSheet(ctx, runtime, token, adoptSheetID, first); err != nil {
				return nil, fmt.Errorf("adopting the default sheet as %q failed: %w", first, err)
			}
			byName[first] = adoptSheetID
		}
	}

	written := make([]interface{}, 0, len(payload.Sheets))
	for i := range payload.Sheets {
		s := &payload.Sheets[i]
		sheetID, ok := byName[s.Name]
		if !ok {
			rows, cols := sheetCreateDims(s)
			sheetID, err = createSheet(ctx, runtime, token, s.Name, rows, cols)
			if err != nil {
				return written, fmt.Errorf("creating sheet %q failed: %w", s.Name, err)
			}
			byName[s.Name] = sheetID
		}
		summary, err := writeSheetData(ctx, runtime, token, sheetID, s, headerStyle)
		if err != nil {
			return written, fmt.Errorf("writing sheet %q failed: %w", s.Name, err)
		}
		written = append(written, summary)
	}
	return written, nil
}

// renameSheet renames a sub-sheet in place via modify_workbook_structure. Used
// to adopt a freshly created workbook's default sheet as the first typed sheet
// (see writeTypedSheets); mirrors +sheet-rename's tool input.
func renameSheet(ctx context.Context, runtime *common.RuntimeContext, token, sheetID, newName string) error {
	_, err := callTool(ctx, runtime, token, ToolKindWrite, "modify_workbook_structure", map[string]interface{}{
		"excel_id":  token,
		"operation": "rename",
		"sheet_id":  sheetID,
		"new_name":  newName,
	})
	return err
}

// tablePutWrite writes the payload into an existing workbook and emits the
// +table-put envelope. The shared write loop lives in writeTypedSheets; this
// wrapper adds +table-put's output shape and partial-success reporting.
func tablePutWrite(ctx context.Context, runtime *common.RuntimeContext, token string, payload *tablePayload, headerStyle bool) error {
	written, err := writeTypedSheets(ctx, runtime, token, payload, headerStyle, "")
	if err != nil {
		return tablePutPartial(token, nil, written, err.Error())
	}
	runtime.Out(map[string]interface{}{
		"spreadsheet_token": token,
		"sheets":            written,
	}, nil)
	return nil
}

// createSheet appends a new sub-sheet sized to hold the spec, then resolves its
// id. The backend's default sheet (20 cols × 200 rows) is too small for wide or
// long tables (e.g. a 37-column quarter matrix), so the create request sizes the
// sheet to the write range up front — otherwise the follow-up set_cell_range
// fails with "range … exceeds sheet bounds". modify_workbook_structure's create
// output shape isn't relied upon — the id is read back by name, which is robust
// across tool-response variations.
func createSheet(ctx context.Context, runtime *common.RuntimeContext, token, name string, rows, cols int) (string, error) {
	input := map[string]interface{}{
		"excel_id":   token,
		"operation":  "create",
		"sheet_name": name,
	}
	if rows > 0 {
		input["rows"] = rows
	}
	if cols > 0 {
		input["columns"] = cols
	}
	if _, err := callTool(ctx, runtime, token, ToolKindWrite, "modify_workbook_structure", input); err != nil {
		return "", err
	}
	id, _, err := lookupSheetIndex(ctx, runtime, token, "", name)
	if err != nil {
		return "", fmt.Errorf("sheet %q created but resolving its id failed: %w", name, err)
	}
	return id, nil
}

// sheetCreateDims sizes a to-be-created sheet to the spec's write range so the
// follow-up set_cell_range can't exceed sheet bounds. It accounts for the
// start_cell offset and the optional header row. The backend's 20×200 defaults
// are kept as floors (ordinary small tables are created exactly as before) and
// its hard limits (200 cols, 50000 rows) as ceilings.
func sheetCreateDims(s *tableSheetSpec) (rows, cols int) {
	_, col0, row0, _ := sheetAnchor(s)
	cols = col0 + len(s.Columns)
	rows = row0 + len(s.Rows)
	if headerOn(s) {
		rows++
	}
	if cols < 20 {
		cols = 20
	}
	if cols > 200 {
		cols = 200
	}
	if rows < 200 {
		rows = 200
	}
	if rows > 50000 {
		rows = 50000
	}
	return rows, cols
}

// listSheetIDsByName maps every existing sub-sheet's display name to its id via
// a single get_workbook_structure read. Used by write mode to decide which
// payload sheets already exist.
func listSheetIDsByName(ctx context.Context, runtime *common.RuntimeContext, token string) (map[string]string, error) {
	out, err := callTool(ctx, runtime, token, ToolKindRead, "get_workbook_structure", map[string]interface{}{
		"excel_id": token,
	})
	if err != nil {
		return nil, err
	}
	m, ok := out.(map[string]interface{})
	if !ok {
		return nil, output.Errorf(output.ExitAPI, "tool_output", "get_workbook_structure returned non-object output")
	}
	sheets, _ := m["sheets"].([]interface{})
	byName := make(map[string]string, len(sheets))
	for _, raw := range sheets {
		sm, ok := raw.(map[string]interface{})
		if !ok {
			continue
		}
		id, _ := sm["sheet_id"].(string)
		name, _ := sm["sheet_name"].(string)
		if name == "" {
			name, _ = sm["title"].(string)
		}
		if id != "" && name != "" {
			byName[name] = id
		}
	}
	return byName, nil
}

// tablePutPartial builds a structured error for a multi-sheet write that failed
// partway. When some sheets already landed it's a partial_success (their
// summaries are surfaced so callers can retry the rest or delete the workbook);
// when nothing landed — the first or only sheet failed — it's a plain failure,
// so we don't misleadingly claim "some sheets were written".
func tablePutPartial(token string, spreadsheet interface{}, written []interface{}, reason string) error {
	detail := map[string]interface{}{
		"spreadsheet_token": token,
		"written_sheets":    written,
	}
	if spreadsheet != nil {
		detail["spreadsheet"] = spreadsheet
	}
	if len(written) == 0 {
		return &output.ExitError{
			Code: output.ExitAPI,
			Detail: &output.ErrDetail{
				Type:    "api_error",
				Message: fmt.Sprintf("table-put failed on %s: %s", token, reason),
				Hint:    "no sheets were written; fix the cause and retry",
				Detail:  detail,
			},
		}
	}
	return &output.ExitError{
		Code: output.ExitAPI,
		Detail: &output.ErrDetail{
			Type:    "partial_success",
			Message: fmt.Sprintf("table-put partially applied to %s: %s", token, reason),
			Hint:    "some sheets were written; inspect written_sheets, then retry the remaining sheets or delete the spreadsheet",
			Detail:  detail,
		},
	}
}

// ─── dry-run ──────────────────────────────────────────────────────────

// tablePutDryRun renders the set_cell_range write the shortcut would send for
// each sheet. Network-free; the payload and locator have already been validated
// by Validate, so errors here degrade to an empty preview rather than twice.
func tablePutDryRun(runtime *common.RuntimeContext) *common.DryRunAPI {
	dry := common.NewDryRunAPI()
	payload, err := parseTablePutPayload(runtime)
	if err != nil {
		return dry
	}
	token, err := resolveSpreadsheetToken(runtime)
	if err != nil {
		return dry
	}
	headerStyle := runtime.Bool("header-style")
	for i := range payload.Sheets {
		s := &payload.Sheets[i]
		matrix, _ := buildSheetMatrix(s, headerStyle, headerOn(s))
		desc := fmt.Sprintf("write sheet %q (%d data rows × %d cols, mode=%s) via set_cell_range",
			s.Name, len(s.Rows), len(s.Columns), writeModeName(s))
		rng := tablePutFullRange(s, len(matrix))
		if s.Mode == "append" {
			rng = "<append below existing data>"
		}
		input := map[string]interface{}{
			"excel_id":   token,
			"sheet_name": s.Name,
			"range":      rng,
			"cells":      matrix,
		}
		if s.AllowOverwrite != nil && !*s.AllowOverwrite {
			input["allow_overwrite"] = false
		}
		wireBody, _ := buildToolBody("set_cell_range", input)
		dry.POST(toolInvokePath(token, ToolKindWrite)).Desc(desc).Body(wireBody)
	}
	return dry
}

// ─── +table-get (typed read-back, mirror of +table-put) ───────────────
//
// Reads a spreadsheet's sheets back into the same typed protocol +table-put
// consumes, so the output round-trips: pipe it straight back to +table-put, or
// load it into a DataFrame. Column types are inferred from each column's
// number_format (a date format → date, numeric/percent → number) and date
// serials are converted back to ISO strings — the exact inverse of the put path.

// TableGet reads sheets back into the typed table protocol.
var TableGet = common.Shortcut{
	Service:     "sheets",
	Command:     "+table-get",
	Description: "Read sheets back into the typed table protocol (mirror of +table-put); column types are inferred from number_format so the output feeds straight to +table-put or a DataFrame.",
	Risk:        "read",
	Scopes:      []string{"sheets:spreadsheet:read"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags:       flagsFor("+table-get"),
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if _, err := resolveSpreadsheetToken(runtime); err != nil {
			return err
		}
		if strings.TrimSpace(runtime.Str("sheet-id")) != "" && strings.TrimSpace(runtime.Str("sheet-name")) != "" {
			return common.FlagErrorf("--sheet-id and --sheet-name are mutually exclusive")
		}
		return nil
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		token, _ := resolveSpreadsheetToken(runtime)
		dry := common.NewDryRunAPI()
		if strings.TrimSpace(runtime.Str("sheet-id")) == "" && strings.TrimSpace(runtime.Str("sheet-name")) == "" {
			body, _ := buildToolBody("get_workbook_structure", map[string]interface{}{"excel_id": token})
			dry.POST(toolInvokePath(token, ToolKindRead)).Desc("list sub-sheets via get_workbook_structure").Body(body)
		}
		rng := strings.TrimSpace(runtime.Str("range"))
		if rng == "" {
			rng = "<each sheet's current region>"
		}
		body, _ := buildToolBody("get_cell_ranges", map[string]interface{}{
			"excel_id": token, "ranges": []string{rng},
			"include_styles": true, "value_render_option": "raw_value",
		})
		dry.POST(toolInvokePath(token, ToolKindRead)).
			Desc(fmt.Sprintf("read cells (%s) + styles via get_cell_ranges, then infer column types", rng)).
			Body(body)
		return dry
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		token, err := resolveSpreadsheetToken(runtime)
		if err != nil {
			return err
		}
		targets, err := tableGetTargets(ctx, runtime, token)
		if err != nil {
			return err
		}
		noHeader := runtime.Bool("no-header")
		userRange := strings.TrimSpace(runtime.Str("range"))
		sheets := make([]interface{}, 0, len(targets))
		for _, t := range targets {
			spec, err := readSheetAsSpec(ctx, runtime, token, t, userRange, noHeader)
			if err != nil {
				return err
			}
			sheets = append(sheets, spec)
		}
		runtime.Out(map[string]interface{}{"sheets": sheets}, nil)
		return nil
	},
	Tips: []string{
		"Output is the same shape +table-put consumes — pipe it back in, or load sheets[].rows into a DataFrame keyed by columns[].name.",
		"Column types are inferred per column, but only when every non-empty cell agrees; a column mixing types (e.g. numbers + \"暂无\") degrades to string — lossless and round-trips cleanly. Numeric coercion of dirty cells is the caller's job (pandas to_numeric(errors=\"coerce\") on the string column).",
	},
}

// tableGetSheet identifies a sheet to read back.
type tableGetSheet struct {
	id   string
	name string
}

// tableGetTargets resolves which sheets +table-get reads: the one named by
// --sheet-id / --sheet-name, or every sheet (in workbook order) when neither is
// given.
func tableGetTargets(ctx context.Context, runtime *common.RuntimeContext, token string) ([]tableGetSheet, error) {
	id := strings.TrimSpace(runtime.Str("sheet-id"))
	name := strings.TrimSpace(runtime.Str("sheet-name"))
	if id != "" {
		return []tableGetSheet{{id: id}}, nil
	}
	if name != "" {
		return []tableGetSheet{{name: name}}, nil
	}
	out, err := callTool(ctx, runtime, token, ToolKindRead, "get_workbook_structure", map[string]interface{}{"excel_id": token})
	if err != nil {
		return nil, err
	}
	m, _ := out.(map[string]interface{})
	raw, _ := m["sheets"].([]interface{})
	targets := make([]tableGetSheet, 0, len(raw))
	for _, r := range raw {
		sm, ok := r.(map[string]interface{})
		if !ok {
			continue
		}
		sid, _ := sm["sheet_id"].(string)
		sname, _ := sm["sheet_name"].(string)
		if sname == "" {
			sname, _ = sm["title"].(string)
		}
		if sid != "" {
			targets = append(targets, tableGetSheet{id: sid, name: sname})
		}
	}
	if len(targets) == 0 {
		return nil, output.Errorf(output.ExitAPI, "tool_output", "no sheets found in workbook")
	}
	return targets, nil
}

// readSheetAsSpec reads one sheet's region and rebuilds it as a typed-protocol
// sheet (name + typed columns + JSON-safe rows), the inverse of the put path.
func readSheetAsSpec(ctx context.Context, runtime *common.RuntimeContext, token string, t tableGetSheet, userRange string, noHeader bool) (map[string]interface{}, error) {
	spec := map[string]interface{}{"name": t.name, "columns": []interface{}{}, "rows": []interface{}{}}
	region := userRange
	if region == "" {
		r, err := sheetCurrentRegion(ctx, runtime, token, t.id, t.name)
		if err != nil {
			return nil, err
		}
		region = r
	}
	if region == "" {
		return spec, nil // empty sheet
	}
	input := map[string]interface{}{
		"excel_id":            token,
		"ranges":              []string{region},
		"include_styles":      true,
		"value_render_option": "raw_value",
		"cell_limit":          unboundedReadLimit,
	}
	sheetSelectorForToolInput(input, t.id, t.name)
	out, err := callTool(ctx, runtime, token, ToolKindRead, "get_cell_ranges", input)
	if err != nil {
		return nil, err
	}
	grid := extractCellGrid(out)
	if len(grid) == 0 {
		return spec, nil
	}

	var headerRow []map[string]interface{}
	dataRows := grid
	if !noHeader {
		headerRow = grid[0]
		dataRows = grid[1:]
	}
	ncols := 0
	for _, r := range grid {
		if len(r) > ncols {
			ncols = len(r)
		}
	}

	columns := make([]interface{}, ncols)
	colTypes := make([]string, ncols)
	for c := 0; c < ncols; c++ {
		typ, format := inferColumnType(dataRows, c)
		colTypes[c] = typ
		col := map[string]interface{}{"name": tableGetColumnName(headerRow, c, noHeader), "type": typ}
		if format != "" {
			col["format"] = format
		}
		columns[c] = col
	}

	rows := make([]interface{}, 0, len(dataRows))
	for _, r := range dataRows {
		row := make([]interface{}, ncols)
		for c := 0; c < ncols; c++ {
			row[c] = cellToTyped(cellAt(r, c), colTypes[c])
		}
		rows = append(rows, row)
	}
	spec["columns"] = columns
	spec["rows"] = rows
	return spec, nil
}

// sheetCurrentRegion returns the A1 range covering the sheet's existing data
// (current_region), or "" for an empty sheet.
func sheetCurrentRegion(ctx context.Context, runtime *common.RuntimeContext, token, sheetID, sheetName string) (string, error) {
	input := map[string]interface{}{"excel_id": token, "range": "A1", "max_rows": unboundedReadLimit}
	sheetSelectorForToolInput(input, sheetID, sheetName)
	out, err := callTool(ctx, runtime, token, ToolKindRead, "get_range_as_csv", input)
	if err != nil {
		return "", err
	}
	m, ok := out.(map[string]interface{})
	if !ok {
		return "", nil
	}
	region, _ := m["current_region"].(string)
	if region == "" {
		region, _ = m["actual_range"].(string)
	}
	return region, nil
}

// extractCellGrid pulls ranges[0].cells out of a get_cell_ranges response into a
// 2D grid of cell objects (each carrying value + cell_styles).
func extractCellGrid(out interface{}) [][]map[string]interface{} {
	m, ok := out.(map[string]interface{})
	if !ok {
		return nil
	}
	ranges, _ := m["ranges"].([]interface{})
	if len(ranges) == 0 {
		return nil
	}
	r0, _ := ranges[0].(map[string]interface{})
	rawCells, _ := r0["cells"].([]interface{})
	grid := make([][]map[string]interface{}, 0, len(rawCells))
	for _, rr := range rawCells {
		rowArr, _ := rr.([]interface{})
		row := make([]map[string]interface{}, 0, len(rowArr))
		for _, cc := range rowArr {
			cm, _ := cc.(map[string]interface{})
			row = append(row, cm)
		}
		grid = append(grid, row)
	}
	return grid
}

func cellAt(row []map[string]interface{}, c int) map[string]interface{} {
	if c >= 0 && c < len(row) {
		return row[c]
	}
	return nil
}

func readCellValue(cell map[string]interface{}) interface{} {
	if cell == nil {
		return nil
	}
	return cell["value"]
}

func readCellFormat(cell map[string]interface{}) string {
	if cell == nil {
		return ""
	}
	st, _ := cell["cell_styles"].(map[string]interface{})
	nf, _ := st["number_format"].(string)
	return nf
}

// inferColumnType decides a column's type from its data cells: a date
// number_format guides each cell's type, but a column is given a non-string type
// only when EVERY non-empty cell agrees. Real sheet columns often mix types (a
// number column with a stray "暂无", a date column with a bare count); declaring
// number/date while a string value rides along makes the output inconsistent —
// it breaks round-trip back into +table-put (which rejects a string in a number
// column) and crashes pandas astype. So a mixed column degrades to string
// (lossless, self-consistent), keeping columns[].type faithful to every value in
// rows. Coercing dirty cells onto a numeric column is deliberately left to the
// caller (pandas to_numeric(errors="coerce") on the string column): lossless
// there — the original values stay in the frame — whereas doing it here would
// drop them silently and irrecoverably.
func inferColumnType(dataRows [][]map[string]interface{}, c int) (string, string) {
	seen := map[string]bool{}
	numberFormat, dateFormat := "", ""
	for _, r := range dataRows {
		cell := cellAt(r, c)
		v := readCellValue(cell)
		if v == nil {
			continue
		}
		if s, ok := v.(string); ok && s == "" {
			continue // empty string is empty, not a string value
		}
		nf := readCellFormat(cell)
		switch {
		case isDateNumberFormat(nf):
			// A date format yields date only when the cell is actually a serial
			// number; a date format painted on text is just text.
			if _, ok := tableGetToFloat(v); ok {
				seen["date"] = true
				if dateFormat == "" {
					dateFormat = nf
				}
			} else {
				seen["string"] = true
			}
		case isTextNumberFormat(nf):
			seen["string"] = true
		default:
			switch v.(type) {
			case float64, json.Number:
				seen["number"] = true
				if numberFormat == "" {
					numberFormat = nf
				}
			case bool:
				seen["bool"] = true
			default:
				seen["string"] = true
			}
		}
	}
	switch {
	case len(seen) == 0:
		return "string", "" // all empty
	case len(seen) == 1:
		switch {
		case seen["date"]:
			return "date", dateFormat
		case seen["number"]:
			return "number", numberFormat
		case seen["bool"]:
			return "bool", ""
		default:
			return "string", ""
		}
	default:
		return "string", "" // mixed types → string (self-consistent, lossless)
	}
}

// isDateNumberFormat reports whether a number_format denotes a date/time. Date
// formats carry a year token ('y'); pure numeric formats (#,##0, 0.00, 0.00%,
// @) do not.
func isDateNumberFormat(nf string) bool {
	return strings.ContainsRune(strings.ToLower(nf), 'y')
}

// isTextNumberFormat reports whether a number_format is Excel/Lark text format
// ("@"), which +table-put writes on string columns so digit-like strings survive
// and read back as string instead of being inferred as number.
func isTextNumberFormat(nf string) bool {
	return strings.TrimSpace(nf) == "@"
}

// cellToTyped converts a read-back cell to the JSON-safe value its column type
// implies: date serials become ISO strings, numbers/bools pass through, empty
// cells become null, everything else is stringified. inferColumnType guarantees
// a non-string column is homogeneous, so the date/number branches never meet a
// stray off-type value.
func cellToTyped(cell map[string]interface{}, typ string) interface{} {
	v := readCellValue(cell)
	if v == nil {
		return nil
	}
	if s, ok := v.(string); ok && s == "" {
		return nil
	}
	switch typ {
	case "date":
		if f, ok := tableGetToFloat(v); ok {
			return serialToISO(f)
		}
		return v
	case "number", "bool":
		return v
	default:
		return stringifyCellValue(v)
	}
}

// tableGetColumnName returns the column's name: the header cell's text, or a
// positional col<N> when there is no header row.
func tableGetColumnName(headerRow []map[string]interface{}, c int, noHeader bool) string {
	if !noHeader {
		if v := readCellValue(cellAt(headerRow, c)); v != nil {
			if s := stringifyCellValue(v); s != "" {
				return s
			}
		}
	}
	return fmt.Sprintf("col%d", c+1)
}

func tableGetToFloat(v interface{}) (float64, bool) {
	switch n := v.(type) {
	case float64:
		return n, true
	case json.Number:
		f, err := n.Float64()
		return f, err == nil
	}
	return 0, false
}

// serialToISO converts an Excel serial day number back to an ISO yyyy-mm-dd
// string — the inverse of isoDateToSerial.
func serialToISO(serial float64) string {
	return excelEpoch.AddDate(0, 0, int(serial)).Format("2006-01-02")
}
