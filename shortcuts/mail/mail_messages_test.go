// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package mail

import (
	"strings"
	"testing"
)

func TestValidateMessageIDs(t *testing.T) {
	tests := []struct {
		name       string
		ids        []string
		wantErr    bool
		wantSubstr string
	}{
		{
			name:    "empty list passes",
			ids:     []string{},
			wantErr: false,
		},
		{
			name:    "valid single ID passes",
			ids:     []string{"msg_abc123"},
			wantErr: false,
		},
		{
			name:    "valid multiple IDs pass",
			ids:     []string{"msg_abc123", "msg_def456", "msg_ghi789"},
			wantErr: false,
		},
		{
			name:    "valid hex ID passes",
			ids:     []string{"a1b2c3d4e5f6"},
			wantErr: false,
		},
		{
			name:    "valid ID with underscores and dashes passes",
			ids:     []string{"msg_abc-123_def"},
			wantErr: false,
		},
		{
			name:       "empty string rejected",
			ids:        []string{""},
			wantErr:    true,
			wantSubstr: "empty or whitespace-only",
		},
		{
			name:       "whitespace-only rejected",
			ids:        []string{"   "},
			wantErr:    true,
			wantSubstr: "empty or whitespace-only",
		},
		{
			name:       "natural language word rejected",
			ids:        []string{"message"},
			wantErr:    true,
			wantSubstr: "natural language",
		},
		{
			name:       "natural language phrase rejected",
			ids:        []string{"please read this email"},
			wantErr:    true,
			wantSubstr: "contains spaces",
		},
		{
			name:       "JSON array string rejected",
			ids:        []string{`["id1","id2"]`},
			wantErr:    true,
			wantSubstr: "JSON array",
		},
		{
			name:       "JSON array string with spaces rejected",
			ids:        []string{`[ "id1", "id2" ]`},
			wantErr:    true,
			wantSubstr: "JSON array",
		},
		{
			name:    "double-quoted valid ID passes after quote stripping",
			ids:     []string{`"msg_abc123"`},
			wantErr: false,
		},
		{
			name:    "single-quoted valid ID passes after quote stripping",
			ids:     []string{`'msg_abc123'`},
			wantErr: false,
		},
		{
			name:       "double-quoted natural language rejected after stripping",
			ids:        []string{`"message"`},
			wantErr:    true,
			wantSubstr: "natural language",
		},
		{
			name:       "single-quoted natural language rejected after stripping",
			ids:        []string{`'email'`},
			wantErr:    true,
			wantSubstr: "natural language",
		},
		{
			name:    "ID that just looks like quotes but isn't still valid",
			ids:     []string{"msg_abc'123"},
			wantErr: false,
		},
		{
			name:       "colon-separated IDs rejected",
			ids:        []string{"id1:id2:id3"},
			wantErr:    true,
			wantSubstr: "colon separators",
		},
		{
			name:       "mixed valid and invalid reports invalid ones",
			ids:        []string{"msg_valid123", "the", "msg_another456"},
			wantErr:    true,
			wantSubstr: "natural language",
		},
		{
			name:       "double-quoted empty rejected",
			ids:        []string{`""`},
			wantErr:    true,
			wantSubstr: "empty or whitespace-only",
		},
		{
			name:       "single-quoted empty rejected",
			ids:        []string{`''`},
			wantErr:    true,
			wantSubstr: "empty or whitespace-only",
		},
		{
			name:       "natural language word 'email' rejected",
			ids:        []string{"email"},
			wantErr:    true,
			wantSubstr: "natural language",
		},
		{
			name:       "natural language word 'subject' rejected",
			ids:        []string{"subject"},
			wantErr:    true,
			wantSubstr: "natural language",
		},
		{
			name:       "natural language word 'fetch' rejected",
			ids:        []string{"fetch"},
			wantErr:    true,
			wantSubstr: "natural language",
		},
		{
			name:    "numeric ID passes",
			ids:     []string{"1234567890"},
			wantErr: false,
		},
		{
			name:    "ID with uppercase passes",
			ids:     []string{"MSG_ABC123DEF"},
			wantErr: false,
		},
		{
			name:    "realistic Lark message ID passes",
			ids:     []string{"gmxxxxxxxxxxxxxx"},
			wantErr: false,
		},
		{
			name:       "multiple invalid IDs all reported",
			ids:        []string{"the", "email", "id1:id2"},
			wantErr:    true,
			wantSubstr: "natural language",
		},
		{
			name:       "double-quoted whitespace-only rejected",
			ids:        []string{`"   "`},
			wantErr:    true,
			wantSubstr: "empty or whitespace-only",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateMessageIDs(tt.ids)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateMessageIDs(%v) error = %v, wantErr %v", tt.ids, err, tt.wantErr)
				return
			}
			if err != nil && tt.wantSubstr != "" {
				if !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("validateMessageIDs(%v) error = %v, want substr %q", tt.ids, err, tt.wantSubstr)
				}
			}
		})
	}
}

func TestValidateSingleMessageID(t *testing.T) {
	tests := []struct {
		name   string
		raw    string
		wantOK bool
	}{
		{name: "valid hex ID", raw: "a1b2c3d4", wantOK: true},
		{name: "valid prefixed ID", raw: "msg_abc123", wantOK: true},
		{name: "empty string", raw: "", wantOK: false},
		{name: "whitespace only", raw: "   ", wantOK: false},
		{name: "tab only", raw: "\t", wantOK: false},
		{name: "natural language phrase", raw: "please read my email", wantOK: false},
		{name: "JSON array", raw: `["id1","id2"]`, wantOK: false},
		{name: "colon separated", raw: "id1:id2:id3", wantOK: false},
		{name: "double quoted valid ID passes after strip", raw: `"msg_abc"`, wantOK: true},
		{name: "single quoted valid ID passes after strip", raw: `'msg_abc'`, wantOK: true},
		{name: "double quoted natural language rejected after strip", raw: `"message"`, wantOK: false},
		{name: "single quoted natural language rejected after strip", raw: `'email'`, wantOK: false},
		{name: "word: message", raw: "message", wantOK: false},
		{name: "word: email", raw: "email", wantOK: false},
		{name: "word: subject", raw: "subject", wantOK: false},
		{name: "word: please", raw: "please", wantOK: false},
		{name: "word: THE", raw: "THE", wantOK: false},
		{name: "numeric ID", raw: "1234567890", wantOK: true},
		{name: "ID with dash", raw: "msg-abc-123", wantOK: true},
		{name: "ID with dot", raw: "msg.abc.123", wantOK: true},
		{name: "ID with underscore", raw: "msg_abc_123", wantOK: true},
		{name: "double quoted empty", raw: `""`, wantOK: false},
		{name: "single quoted empty", raw: `''`, wantOK: false},
		{name: "double quoted whitespace", raw: `"   "`, wantOK: false},
		{name: "double quoted colon-separated rejected after strip", raw: `"a:b:c"`, wantOK: false},
		{name: "double quoted JSON array rejected", raw: `"[]"`, wantOK: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			reason := validateSingleMessageID(tt.raw)
			if tt.wantOK && reason != "" {
				t.Errorf("validateSingleMessageID(%q) = %q, want empty (valid)", tt.raw, reason)
			}
			if !tt.wantOK && reason == "" {
				t.Errorf("validateSingleMessageID(%q) = empty, want rejection reason", tt.raw)
			}
		})
	}
}
