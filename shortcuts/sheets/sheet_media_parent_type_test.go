// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package sheets

import "testing"

// TestSheetMediaParentType pins the token→parent_type mapping that every
// sheets image-upload entry point funnels through. Native spreadsheet tokens
// use "sheet_image"; imported "office" spreadsheets carry a "fake_office_"
// synthetic token and must upload with "office_sheet_file".
func TestSheetMediaParentType(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name  string
		token string
		want  string
	}{
		{"native spreadsheet token", "shtcnABC123", sheetImageParentType},
		{"wiki-resolved spreadsheet token", "Xyz0wABC123def", sheetImageParentType},
		{"empty token", "", sheetImageParentType},
		{"office imported token", "fake_office_abc123", officeSheetFileParentType},
		{"office token, only the prefix", fakeOfficeTokenPrefix, officeSheetFileParentType},
		{"prefix mid-string is not matched", "shtfake_office_abc", sheetImageParentType},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := sheetMediaParentType(tc.token); got != tc.want {
				t.Fatalf("sheetMediaParentType(%q) = %q, want %q", tc.token, got, tc.want)
			}
		})
	}
}
