// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package common

import (
	"encoding/json"

	"github.com/larksuite/cli/internal/schema"
)

// ProjectBySchema trims data to the schema-curated default view.
//
// full==true / props==nil → passthrough (fail-open, never drops information).
// Otherwise the input is normalized to canonical JSON values first, then the
// core keeps only fields whose Projected==true (a field shows iff p.Projected
// || full). It rebuilds maps/slices (never mutates input), skips missing keys
// (no null padding), and carries zero business knowledge.
//
// Normalizing first is what makes this robust by construction: whatever native
// Go type a command emits — a typed slice ([]map[string]interface{}), a struct,
// a typed map, anything JSON-serializable — collapses to canonical
// map[string]interface{} / []interface{} / scalars, so the core's finite switch
// is COMPLETE. No command output, present or future, can fall through unprojected.
func ProjectBySchema(data interface{}, props *schema.OrderedProps, full bool) interface{} {
	if full || props == nil {
		return data
	}
	return projectCanonical(canonicalize(data), props)
}

// projectCanonical projects already-canonical JSON data. props==nil is a kept
// leaf with no child schema: pass its value through verbatim.
func projectCanonical(data interface{}, props *schema.OrderedProps) interface{} {
	if props == nil {
		return data
	}
	switch v := data.(type) {
	case map[string]interface{}:
		out := map[string]interface{}{}
		for _, key := range props.Order {
			p := props.Map[key]
			if !p.Projected {
				continue
			}
			if val, ok := v[key]; ok {
				out[key] = projectCanonical(val, childProps(p))
			}
		}
		return out
	case []interface{}:
		out := make([]interface{}, len(v))
		for i := range v {
			out[i] = projectCanonical(v[i], props)
		}
		return out
	default:
		// Canonical scalar (string / float64 / bool / nil): a leaf value, kept verbatim.
		return data
	}
}

// canonicalize converts any JSON-serializable value to canonical JSON values
// (map[string]interface{} / []interface{} / scalars) via a marshal round-trip,
// decoupling projection from a command's concrete Go types. Fail-open: input
// that does not serialize (never the case for command output) is returned as-is.
func canonicalize(data interface{}) interface{} {
	b, err := json.Marshal(data)
	if err != nil {
		return data
	}
	var out interface{}
	if err := json.Unmarshal(b, &out); err != nil {
		return data
	}
	return out
}

// childProps returns the schema to recurse with for a field's value. Array
// fields keep their element schema in Items.Properties; object fields use
// Properties directly. Without this, an array-typed field would recurse with
// nil props and pass its elements through unprojected.
func childProps(p schema.Property) *schema.OrderedProps {
	if p.Items != nil && p.Items.Properties != nil {
		return p.Items.Properties
	}
	return p.Properties
}

// droppedFieldNames returns the set of field names that projection removes from
// data under props (present in data but not declared projected, at any depth).
//
// Unlike a static schema scan, it diffs the actual response against the schema:
// with positive polarity the hidden fields are simply absent from the
// OutputSchema (not marked "false"), so the only way to name a trimmed field is
// to see it in the real data and find it missing from the projected set. Drives
// the on-demand jq-miss hint. Names only (no values) — never echoes user input
// or upstream data.
func droppedFieldNames(data interface{}, props *schema.OrderedProps) map[string]bool {
	out := map[string]bool{}
	var walk func(d interface{}, p *schema.OrderedProps)
	walk = func(d interface{}, p *schema.OrderedProps) {
		switch v := d.(type) {
		case map[string]interface{}:
			for key := range v {
				var pr schema.Property
				ok := false
				if p != nil {
					pr, ok = p.Map[key]
				}
				if !ok || !pr.Projected {
					out[key] = true
					continue
				}
				// Kept field: recurse only when it has a child schema (object /
				// array element); a projected leaf keeps its whole value, so
				// nothing inside it is dropped.
				if cp := childProps(pr); cp != nil {
					walk(v[key], cp)
				}
			}
		case []interface{}:
			for _, e := range v {
				walk(e, p)
			}
		}
	}
	walk(canonicalize(data), props) // canonical input → the two-case walk is complete
	return out
}

// anyProjected reports whether any field in the tree carries Projected==true.
// Used as a guard: a Projectable command whose OutputSchema marks nothing is
// treated as pass-through rather than trimming everything away.
func anyProjected(props *schema.OrderedProps) bool {
	if props == nil {
		return false
	}
	for _, key := range props.Order {
		p := props.Map[key]
		if p.Projected {
			return true
		}
		if anyProjected(p.Properties) {
			return true
		}
	}
	return false
}

// ── OutputSchema builders ──
//
// These let a shortcut declare its OutputSchema inline in Go, shaped to match
// the data it emits. A field declared here shows in the default (projected)
// view; anything not declared is hidden until --full.

// KeepFields returns an OrderedProps with each name marked projected as a leaf
// field — the common case for a flat group of scalar fields kept by default.
func KeepFields(names ...string) *schema.OrderedProps {
	props := &schema.OrderedProps{}
	for _, n := range names {
		props.Set(n, schema.Property{Projected: true})
	}
	return props
}

// ArrayOf returns a projected array-typed property whose elements are projected
// by elem. Use for a default-shown list field: root.Set("chats", ArrayOf(chat)).
func ArrayOf(elem *schema.OrderedProps) schema.Property {
	return schema.Property{Projected: true, Items: &schema.Property{Properties: elem}}
}

// ObjectOf returns a projected nested-object property whose sub-fields are
// projected by child. Use for a default-shown object field.
func ObjectOf(child *schema.OrderedProps) schema.Property {
	return schema.Property{Projected: true, Properties: child}
}
