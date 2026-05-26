// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package argstype

import (
	"errors"
	"reflect"
	"testing"

	"github.com/larksuite/cli/errs"
)

func TestUserOpenIDList_Parse(t *testing.T) {
	list := UserOpenIDList{"ou_a", "ou_b"}
	if err := list.ValidateValue(nil, "user-ids"); err != nil {
		t.Errorf("valid list should pass: %v", err)
	}
}

func TestUserOpenIDList_RejectEmpty(t *testing.T) {
	// CSV input like ",," parses to an empty list; an explicitly-empty list
	// must be rejected rather than silently accepted as "no recipients".
	if err := ParseUserOpenIDList(",,").ValidateValue(nil, "user-ids"); err == nil {
		t.Error("empty list must be rejected")
	}
	if err := UserOpenIDList(nil).ValidateValue(nil, "user-ids"); err == nil {
		t.Error("nil list must be rejected")
	}
}

func TestUserOpenIDList_RejectInvalid(t *testing.T) {
	list := UserOpenIDList{"ou_a", "bad", "ou_c"}
	err := list.ValidateValue(nil, "user-ids")
	if err == nil {
		t.Fatal("expected error for invalid entry")
	}
	var ve *errs.ValidationError
	if !errors.As(err, &ve) {
		t.Fatalf("expected *errs.ValidationError, got %T", err)
	}
}

func TestUserOpenIDList_ParseCSV(t *testing.T) {
	got := ParseUserOpenIDList("ou_a,ou_b , ou_c")
	want := UserOpenIDList{"ou_a", "ou_b", "ou_c"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
}
