// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package common

import (
	"reflect"
	"testing"

	"github.com/larksuite/cli/internal/schema"
)

func props(marked ...string) *schema.OrderedProps {
	op := &schema.OrderedProps{}
	set := map[string]bool{}
	for _, m := range marked {
		set[m] = true
	}
	for _, k := range []string{"name", "avatar", "tenant_key"} {
		op.Set(k, schema.Property{Type: "string", Projected: set[k]})
	}
	return op
}

func TestProjectBySchema_PositivePolarity(t *testing.T) {
	in := map[string]interface{}{"name": "g", "avatar": "u", "tenant_key": "t"}
	out := ProjectBySchema(in, props("name"), false)
	want := map[string]interface{}{"name": "g"}
	if !reflect.DeepEqual(out, want) {
		t.Fatalf("got %v want %v", out, want)
	}
	if len(in) != 3 {
		t.Fatalf("input map mutated: %v", in)
	}
}

func TestProjectBySchema_FailOpen(t *testing.T) {
	in := map[string]interface{}{"name": "g", "avatar": "u"}
	if got := ProjectBySchema(in, props("name"), true); !reflect.DeepEqual(got, in) {
		t.Fatalf("full=true should passthrough, got %v", got)
	}
	if got := ProjectBySchema(in, nil, false); !reflect.DeepEqual(got, in) {
		t.Fatalf("nil props should passthrough, got %v", got)
	}
	if got := ProjectBySchema("scalar", props("name"), false); got != "scalar" {
		t.Fatalf("non-map should passthrough, got %v", got)
	}
}

func TestProjectBySchema_Array(t *testing.T) {
	in := []interface{}{
		map[string]interface{}{"name": "a", "avatar": "x"},
		map[string]interface{}{"name": "b", "avatar": "y"},
	}
	out := ProjectBySchema(in, props("name"), false).([]interface{})
	for i, it := range out {
		m := it.(map[string]interface{})
		if _, ok := m["avatar"]; ok {
			t.Fatalf("elem %d kept avatar", i)
		}
		if m["name"] == nil {
			t.Fatalf("elem %d dropped projected name", i)
		}
	}
	// original input slice must be untouched (no in-place mutation)
	for i, it := range in {
		m := it.(map[string]interface{})
		if _, ok := m["avatar"]; !ok {
			t.Fatalf("input elem %d was mutated (avatar removed)", i)
		}
	}
}

func TestProjectBySchema_Nested(t *testing.T) {
	child := &schema.OrderedProps{}
	child.Set("chat_id", schema.Property{Type: "string", Projected: true})
	child.Set("avatar", schema.Property{Type: "string"})
	root := &schema.OrderedProps{}
	root.Set("detail", schema.Property{Type: "object", Projected: true, Properties: child})

	in := map[string]interface{}{"detail": map[string]interface{}{"chat_id": "oc", "avatar": "u"}}
	out := ProjectBySchema(in, root, false).(map[string]interface{})
	d := out["detail"].(map[string]interface{})
	if _, ok := d["avatar"]; ok {
		t.Fatalf("nested avatar should be dropped")
	}
	if d["chat_id"] != "oc" {
		t.Fatalf("nested chat_id should be kept")
	}
}

func TestProjectBySchema_ArrayFieldInMap(t *testing.T) {
	// Mirrors the real list shape: data = {chats: [ {chat_id, avatar}, ... ], page_token}.
	// The element schema lives in the "chats" field's Items.Properties.
	elem := &schema.OrderedProps{}
	elem.Set("chat_id", schema.Property{Type: "string", Projected: true})
	elem.Set("avatar", schema.Property{Type: "string"}) // full-only
	root := &schema.OrderedProps{}
	root.Set("chats", schema.Property{
		Type:      "array",
		Projected: true,
		Items:     &schema.Property{Type: "object", Properties: elem},
	})
	root.Set("page_token", schema.Property{Type: "string", Projected: true})
	root.Set("has_more", schema.Property{Type: "boolean"}) // unmarked → dropped

	in := map[string]interface{}{
		"chats":      []interface{}{map[string]interface{}{"chat_id": "oc", "avatar": "u"}},
		"page_token": "pt",
		"has_more":   true,
	}
	out := ProjectBySchema(in, root, false).(map[string]interface{})
	if out["page_token"] != "pt" {
		t.Fatalf("projected pagination field page_token should survive")
	}
	if _, ok := out["has_more"]; ok {
		t.Fatalf("unmarked has_more should be dropped")
	}
	chats := out["chats"].([]interface{})
	c0 := chats[0].(map[string]interface{})
	if c0["chat_id"] != "oc" {
		t.Fatalf("element projected field chat_id should survive")
	}
	if _, ok := c0["avatar"]; ok {
		t.Fatalf("element full-only avatar should be dropped (array element must be projected via Items.Properties)")
	}
}

func TestProjectBySchema_MissingFieldSkipped(t *testing.T) {
	in := map[string]interface{}{"name": "g"} // avatar missing
	out := ProjectBySchema(in, props("name", "avatar"), false).(map[string]interface{})
	if _, ok := out["avatar"]; ok {
		t.Fatalf("missing field should not be added as null")
	}
}

func TestDroppedFieldNames(t *testing.T) {
	// props("name") declares only "name" projected; avatar/tenant_key are absent
	// from the schema (positive polarity), so the engine trims them. droppedFieldNames
	// must find them by diffing the real data against the schema.
	op := props("name")
	data := map[string]interface{}{"name": "g", "avatar": "x", "tenant_key": "t"}
	got := droppedFieldNames(data, op)

	if !got["avatar"] || !got["tenant_key"] {
		t.Errorf("avatar/tenant_key should be reported dropped, got %v", got)
	}
	if got["name"] {
		t.Error("projected field name must not be reported dropped")
	}
}

func TestDroppedFieldNames_Nested(t *testing.T) {
	// root keeps "detail" (object) with only "chat_id" projected; the response's
	// detail.avatar and root-level total are not declared, so both are dropped.
	child := &schema.OrderedProps{}
	child.Set("chat_id", schema.Property{Type: "string", Projected: true})
	root := &schema.OrderedProps{}
	root.Set("detail", schema.Property{Type: "object", Projected: true, Properties: child})

	data := map[string]interface{}{
		"detail": map[string]interface{}{"chat_id": "oc_1", "avatar": "x"},
		"total":  5,
	}
	got := droppedFieldNames(data, root)

	if !got["avatar"] {
		t.Error("nested detail.avatar should be reported dropped")
	}
	if !got["total"] {
		t.Error("undeclared root-level total should be reported dropped")
	}
	if got["detail"] || got["chat_id"] {
		t.Errorf("projected detail/chat_id must not be dropped, got %v", got)
	}
}

func TestAnyProjected(t *testing.T) {
	none := &schema.OrderedProps{}
	none.Set("a", schema.Property{})
	if anyProjected(none) {
		t.Fatalf("no marks should report false")
	}
	some := &schema.OrderedProps{}
	some.Set("a", schema.Property{})
	some.Set("b", schema.Property{Projected: true})
	if !anyProjected(some) {
		t.Fatalf("a mark should report true")
	}
	child := &schema.OrderedProps{}
	child.Set("c", schema.Property{Projected: true})
	nested := &schema.OrderedProps{}
	nested.Set("obj", schema.Property{Type: "object", Properties: child})
	if !anyProjected(nested) {
		t.Fatalf("nested mark should report true")
	}
	if anyProjected(nil) {
		t.Fatalf("nil should report false")
	}
}

// ── OutputSchema builder tests ──

// TestKeepFields verifies KeepFields marks every named field projected, as a
// leaf (no Items/Properties), preserving declaration order.
func TestKeepFields(t *testing.T) {
	op := KeepFields("chat_id", "name", "owner_id")
	if want := []string{"chat_id", "name", "owner_id"}; !reflect.DeepEqual(op.Order, want) {
		t.Fatalf("Order = %v, want %v", op.Order, want)
	}
	for _, k := range op.Order {
		p := op.Map[k]
		if !p.Projected {
			t.Errorf("field %q should be projected", k)
		}
		if p.Items != nil || p.Properties != nil {
			t.Errorf("field %q should be a leaf (no Items/Properties)", k)
		}
	}
	if len(KeepFields().Order) != 0 {
		t.Fatalf("KeepFields() with no names should yield empty props")
	}
}

// TestArrayOf verifies ArrayOf returns a projected property whose elements are
// projected by the supplied element schema (carried in Items.Properties), and
// that childProps recurses into that element schema.
func TestArrayOf(t *testing.T) {
	elem := KeepFields("chat_id", "name")
	p := ArrayOf(elem)
	if !p.Projected {
		t.Fatalf("ArrayOf should mark the array field projected")
	}
	if p.Items == nil || p.Items.Properties != elem {
		t.Fatalf("ArrayOf should carry the element schema in Items.Properties")
	}
	if childProps(p) != elem {
		t.Fatalf("childProps should recurse into the array element schema")
	}
}

// TestObjectOf verifies ObjectOf returns a projected object property whose
// sub-fields are projected by the supplied child schema (carried in Properties),
// and that childProps recurses into that child schema.
func TestObjectOf(t *testing.T) {
	child := KeepFields("chat_id", "chat_mode")
	p := ObjectOf(child)
	if !p.Projected {
		t.Fatalf("ObjectOf should mark the object field projected")
	}
	if p.Properties != child {
		t.Fatalf("ObjectOf should carry the child schema in Properties")
	}
	if p.Items != nil {
		t.Fatalf("ObjectOf should not set Items")
	}
	if childProps(p) != child {
		t.Fatalf("childProps should recurse into the object child schema")
	}
}

// chatListShapeSchema mirrors the +chat-list OutputSchema built with the
// KeepFields/ArrayOf builders: root marks pagination + the chats wrapper; each
// chat keeps a curated field set while avatar stays full-only.
func chatListShapeSchema() *schema.OrderedProps {
	chat := KeepFields("chat_id", "name", "owner_id")
	root := KeepFields("has_more", "page_token")
	root.Set("chats", ArrayOf(chat))
	return root
}

// TestProjectBySchema_ChatListShape is the integration check the task asks for:
// against a chat-list-shaped map, projected fields (wrapper, pagination, the
// curated chat fields) survive, unmarked fields (top-level total, per-chat
// avatar) are trimmed, and --full passes the whole envelope through verbatim.
func TestProjectBySchema_ChatListShape(t *testing.T) {
	envelope := func() map[string]interface{} {
		return map[string]interface{}{
			"chats": []interface{}{
				map[string]interface{}{
					"chat_id":  "oc_1",
					"name":     "Team",
					"owner_id": "ou_owner",
					"avatar":   "http://img/1.png", // full-only
				},
			},
			"has_more":   true,
			"page_token": "pt_next",
			"total":      1, // unmarked top-level key → trimmed by default
		}
	}

	// Default (projected) view.
	out := ProjectBySchema(envelope(), chatListShapeSchema(), false).(map[string]interface{})
	if out["has_more"] != true || out["page_token"] != "pt_next" {
		t.Fatalf("projected pagination fields should survive, got %v", out)
	}
	if _, ok := out["total"]; ok {
		t.Fatalf("unmarked top-level total should be trimmed")
	}
	chats := out["chats"].([]interface{})
	c0 := chats[0].(map[string]interface{})
	for _, k := range []string{"chat_id", "name", "owner_id"} {
		if _, ok := c0[k]; !ok {
			t.Fatalf("projected chat field %q should survive", k)
		}
	}
	if _, ok := c0["avatar"]; ok {
		t.Fatalf("full-only chat field avatar should be trimmed by default")
	}

	// --full passthrough: identical to the untouched envelope.
	full := ProjectBySchema(envelope(), chatListShapeSchema(), true)
	if !reflect.DeepEqual(full, envelope()) {
		t.Fatalf("--full should pass the whole envelope through verbatim, got %v", full)
	}
}

// TestProjectBySchema_TypedMapSlice guards the []map[string]interface{} case:
// +chat-list re-collects API items into a typed []map[string]interface{} (not
// []interface{}). Before the fix that slice fell through to the default branch
// and was returned unprojected — avatar/tenant_key leaked into the default view.
// Regression test for that real E2E failure.
func TestProjectBySchema_TypedMapSlice(t *testing.T) {
	envelope := map[string]interface{}{
		"chats": []map[string]interface{}{ // typed slice, NOT []interface{}
			{"chat_id": "oc_1", "name": "Team", "owner_id": "ou_o", "avatar": "http://img"},
		},
		"has_more": true,
	}
	out := ProjectBySchema(envelope, chatListShapeSchema(), false).(map[string]interface{})
	chats, ok := out["chats"].([]interface{})
	if !ok {
		t.Fatalf("typed []map slice should be recursed into []interface{}, got %T", out["chats"])
	}
	c0 := chats[0].(map[string]interface{})
	if _, ok := c0["avatar"]; ok {
		t.Fatalf("full-only avatar must be trimmed from a []map[string]interface{} element, got %v", c0)
	}
	if c0["chat_id"] != "oc_1" || c0["name"] != "Team" {
		t.Fatalf("projected fields must survive, got %v", c0)
	}
}

// TestProjectBySchema_AnyGoType is the robustness proof: a command may emit any
// JSON-serializable Go type — here a []struct, a shape the engine never special-
// cases. Normalization collapses it to canonical JSON, so projection still trims
// it. This is what makes the engine immune to "the next weird box".
func TestProjectBySchema_AnyGoType(t *testing.T) {
	type chatStruct struct {
		ChatID string `json:"chat_id"`
		Name   string `json:"name"`
		Avatar string `json:"avatar"` // not declared projected → must be trimmed
	}
	root := KeepFields("has_more")
	root.Set("chats", ArrayOf(KeepFields("chat_id", "name")))

	data := map[string]interface{}{
		"has_more": true,
		"chats":    []chatStruct{{ChatID: "oc_1", Name: "Team", Avatar: "http://img"}},
	}
	out := ProjectBySchema(data, root, false).(map[string]interface{})
	chats, ok := out["chats"].([]interface{})
	if !ok {
		t.Fatalf("a []struct must normalize + recurse into []interface{}, got %T", out["chats"])
	}
	c0 := chats[0].(map[string]interface{})
	if _, ok := c0["avatar"]; ok {
		t.Fatalf("avatar must be trimmed even from a []struct, got %v", c0)
	}
	if c0["chat_id"] != "oc_1" || c0["name"] != "Team" {
		t.Fatalf("projected fields must survive, got %v", c0)
	}
}
