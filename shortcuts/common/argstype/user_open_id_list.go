// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package argstype

import (
	"strings"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/shortcuts/common"
)

// UserOpenIDList is a comma-separated list of UserOpenID values.
type UserOpenIDList []string

// ParseUserOpenIDList splits a CSV string and trims whitespace.
func ParseUserOpenIDList(raw string) UserOpenIDList {
	if strings.TrimSpace(raw) == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	out := make(UserOpenIDList, 0, len(parts))
	for _, p := range parts {
		if t := strings.TrimSpace(p); t != "" {
			out = append(out, t)
		}
	}
	return out
}

// ValidateValue verifies the list is non-empty and every entry has the ou_
// prefix. An explicitly-provided but empty list (e.g. from CSV input like
// ",," that parses to zero entries) is rejected rather than silently treated
// as "no recipients".
func (l UserOpenIDList) ValidateValue(_ *common.RuntimeContext, flagName string) error {
	if len(l) == 0 {
		return &errs.ValidationError{
			Problem: errs.Problem{
				Category: errs.CategoryValidation,
				Subtype:  errs.SubtypeInvalidArgument,
				Message:  "user open_id list is empty; provide at least one ou_xxx value",
			},
			Param: flagName,
		}
	}
	for i, v := range l {
		if !strings.HasPrefix(v, "ou_") {
			return &errs.ValidationError{
				Problem: errs.Problem{
					Category: errs.CategoryValidation,
					Subtype:  errs.SubtypeInvalidArgument,
					Message:  "invalid user open_id at index " + itoa(i) + ": expected ou_xxx",
				},
				Param: flagName,
			}
		}
	}
	return nil
}

// itoa is a tiny local helper to avoid pulling strconv in every file.
func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	var b []byte
	neg := n < 0
	if neg {
		n = -n
	}
	for n > 0 {
		b = append([]byte{byte('0' + n%10)}, b...)
		n /= 10
	}
	if neg {
		b = append([]byte{'-'}, b...)
	}
	return string(b)
}
