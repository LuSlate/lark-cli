// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package common

import (
	"errors"
	"reflect"
	"testing"

	"github.com/spf13/cobra"

	"github.com/larksuite/cli/errs"
)

type simpleArgs struct {
	Name  string `flag:"name" desc:"a name"`
	Count int    `flag:"count" default:"3"`
}

func TestWalkArgs_Simple(t *testing.T) {
	specs, err := walkArgs(reflect.TypeOf(&simpleArgs{}))
	if err != nil {
		t.Fatalf("walkArgs: %v", err)
	}
	if len(specs) != 2 {
		t.Fatalf("expected 2 field specs, got %d", len(specs))
	}
	if specs[0].FlagName != "name" || specs[1].FlagName != "count" {
		t.Errorf("flag names: %+v", specs)
	}
}

type dupTagArgs struct {
	A string `flag:"x"`
	B string `flag:"x"`
}

func TestWalkArgs_DuplicateTagPanics(t *testing.T) {
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic for duplicate flag tag")
		}
	}()
	_, _ = walkArgs(reflect.TypeOf(&dupTagArgs{}))
}

type bindArgs struct {
	Name  string `flag:"name"`
	Count int    `flag:"count" default:"7"`
}

func TestRegisterAndBind_StringInt(t *testing.T) {
	cmd := &cobra.Command{Use: "test"}
	specs, _ := walkArgs(reflect.TypeOf(&bindArgs{}))
	if err := registerFlags(cmd, specs); err != nil {
		t.Fatalf("registerFlags: %v", err)
	}
	_ = cmd.ParseFlags([]string{"--name", "alice", "--count", "12"})
	out := &bindArgs{}
	if err := bindFlags(cmd, reflect.ValueOf(out).Elem(), specs); err != nil {
		t.Fatalf("bindFlags: %v", err)
	}
	if out.Name != "alice" {
		t.Errorf("Name = %q, want alice", out.Name)
	}
	if out.Count != 12 {
		t.Errorf("Count = %d, want 12", out.Count)
	}
}

func TestRegister_DefaultApplies(t *testing.T) {
	cmd := &cobra.Command{Use: "test"}
	specs, _ := walkArgs(reflect.TypeOf(&bindArgs{}))
	_ = registerFlags(cmd, specs)
	_ = cmd.ParseFlags(nil)
	out := &bindArgs{}
	_ = bindFlags(cmd, reflect.ValueOf(out).Elem(), specs)
	if out.Count != 7 {
		t.Errorf("default not applied: Count = %d, want 7", out.Count)
	}
}

type withValidatable struct {
	ID dummyValidatable `flag:"id"`
}

func TestRunValidateValue_CallsValidatable(t *testing.T) {
	v := &withValidatable{}
	specs, _ := walkArgs(reflect.TypeOf(v))
	rt := &RuntimeContext{}
	if err := runValidateValue(rt, reflect.ValueOf(v).Elem(), specs); err != nil {
		t.Errorf("runValidateValue: %v", err)
	}
}

type oneOfArgs struct {
	A *string `flag:"a"`
	B *string `flag:"b"`
}

func (oneOfArgs) OneOf() {}

type bucketArgs struct {
	Bucket oneOfArgs
}

func TestFrameworkRules_OneOfMissing(t *testing.T) {
	cmd := &cobra.Command{Use: "test"}
	specs, _ := walkArgs(reflect.TypeOf(&bucketArgs{}))
	_ = registerFlags(cmd, specs)
	_ = cmd.ParseFlags(nil)
	out := &bucketArgs{}
	_ = bindFlags(cmd, reflect.ValueOf(out).Elem(), specs)
	err := runFrameworkRules(cmd, reflect.ValueOf(out).Elem(), specs)
	if err == nil {
		t.Fatal("expected oneof_missing error")
	}
	ve := mustValidationError(t, err)
	if ve.Subtype != errs.SubtypeShortcutOneOfMissing {
		t.Errorf("Subtype = %q", ve.Subtype)
	}
}

func TestFrameworkRules_OneOfMultiple(t *testing.T) {
	cmd := &cobra.Command{Use: "test"}
	specs, _ := walkArgs(reflect.TypeOf(&bucketArgs{}))
	_ = registerFlags(cmd, specs)
	_ = cmd.ParseFlags([]string{"--a", "1", "--b", "2"})
	out := &bucketArgs{}
	_ = bindFlags(cmd, reflect.ValueOf(out).Elem(), specs)
	err := runFrameworkRules(cmd, reflect.ValueOf(out).Elem(), specs)
	if err == nil {
		t.Fatal("expected oneof_multiple error")
	}
	ve := mustValidationError(t, err)
	if ve.Subtype != errs.SubtypeShortcutOneOfMultiple {
		t.Errorf("Subtype = %q", ve.Subtype)
	}
}

func mustValidationError(t *testing.T, err error) *errs.ValidationError {
	t.Helper()
	var ve *errs.ValidationError
	if !errors.As(err, &ve) {
		t.Fatalf("expected *errs.ValidationError, got %T", err)
	}
	return ve
}
