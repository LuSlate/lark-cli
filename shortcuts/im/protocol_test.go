// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package im

import "testing"

func TestMessageTarget_SatisfiesOneOfMarker(t *testing.T) {
	var v interface{} = MessageTarget{}
	if _, ok := v.(interface{ OneOf() }); !ok {
		t.Fatal("MessageTarget must satisfy OneOfMarker")
	}
}

func TestMessageContent_SatisfiesOneOfMarker(t *testing.T) {
	var v interface{} = MessageContent{}
	if _, ok := v.(interface{ OneOf() }); !ok {
		t.Fatal("MessageContent must satisfy OneOfMarker")
	}
}

func TestVideoContent_FieldsExist(t *testing.T) {
	v := VideoContent{}
	_ = v.File
	_ = v.Cover
}

func TestRawContent_InvalidJSONFails(t *testing.T) {
	r := &RawContent{JSON: "{ broken"}
	if err := r.ValidateValue(nil, "content"); err == nil {
		t.Fatal("expected validation error for malformed JSON")
	}
}
