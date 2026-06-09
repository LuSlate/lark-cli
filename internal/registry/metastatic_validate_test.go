//go:build larkmeta

// Phase-1 validation for the static-meta migration: proves the generated
// metastatic.Registry carries the same services/resources/methods/fields as the
// embedded JSON, and that reading it costs zero allocation (vs the JSON parse).
package registry

import (
	"encoding/json"
	"testing"

	"github.com/larksuite/cli/internal/registry/metaschema"
	"github.com/larksuite/cli/internal/registry/metastatic"
)

// --- equivalence: counts must match so no service/resource/method/field is lost ---

func countFieldsJSON(v interface{}) int {
	fm, _ := v.(map[string]interface{})
	n := 0
	for _, fv := range fm {
		n++
		if f, ok := fv.(map[string]interface{}); ok {
			n += countFieldsJSON(f["properties"])
		}
	}
	return n
}

func countJSON(data []byte) (svc, res, meth, fld int) {
	var reg map[string]interface{}
	if err := json.Unmarshal(data, &reg); err != nil {
		return
	}
	svcs, _ := reg["services"].([]interface{})
	svc = len(svcs)
	for _, sv := range svcs {
		s, _ := sv.(map[string]interface{})
		rs, _ := s["resources"].(map[string]interface{})
		for _, rv := range rs {
			res++
			r, _ := rv.(map[string]interface{})
			ms, _ := r["methods"].(map[string]interface{})
			for _, mv := range ms {
				meth++
				m, _ := mv.(map[string]interface{})
				fld += countFieldsJSON(m["parameters"]) + countFieldsJSON(m["requestBody"]) + countFieldsJSON(m["responseBody"])
			}
		}
	}
	return
}

func countFieldsStatic(fs []metaschema.Field) int {
	n := 0
	for _, f := range fs {
		n++
		n += countFieldsStatic(f.Properties)
	}
	return n
}

func countStatic() (svc, res, meth, fld int) {
	svc = len(metastatic.Registry.Services)
	for _, s := range metastatic.Registry.Services {
		for _, r := range s.Resources {
			res++
			for _, m := range r.Methods {
				meth++
				fld += countFieldsStatic(m.Parameters) + countFieldsStatic(m.RequestBody) + countFieldsStatic(m.ResponseBody)
			}
		}
	}
	return
}

func TestStaticEquivalence(t *testing.T) {
	if len(embeddedMetaJSON) == 0 {
		t.Skip("no embedded meta_data.json")
	}
	js, jr, jm, jf := countJSON(embeddedMetaJSON)
	ss, sr, sm, sf := countStatic()
	t.Logf("JSON   : services=%d resources=%d methods=%d fields=%d", js, jr, jm, jf)
	t.Logf("static : services=%d resources=%d methods=%d fields=%d", ss, sr, sm, sf)
	if js != ss || jr != sr || jm != sm || jf != sf {
		t.Fatalf("count mismatch: static vs JSON (svc %d/%d, res %d/%d, meth %d/%d, fld %d/%d)",
			ss, js, sr, jr, sm, jm, sf, jf)
	}
	if metastatic.Registry.Version != "" {
		var reg map[string]interface{}
		_ = json.Unmarshal(embeddedMetaJSON, &reg)
		if v, _ := reg["version"].(string); v != metastatic.Registry.Version {
			t.Errorf("version mismatch: static=%q json=%q", metastatic.Registry.Version, v)
		}
	}
}

var sinkInt int

// --- zero-alloc: a deep read of the static registry must allocate nothing ---

func deepReadStatic() int {
	n := 0
	for _, s := range metastatic.Registry.Services {
		n += len(s.Name)
		for _, r := range s.Resources {
			for _, m := range r.Methods {
				n += len(m.ID) + len(m.Scopes) + countFieldsStatic(m.Parameters) + countFieldsStatic(m.ResponseBody)
			}
		}
	}
	return n
}

func TestStaticReadZeroAlloc(t *testing.T) {
	avg := testing.AllocsPerRun(50, func() { sinkInt = deepReadStatic() })
	t.Logf("static deep-read: %.1f allocs/op", avg)
	if avg > 0 {
		t.Errorf("static read allocates %.1f/op, want 0 (data should be in the binary, not heap)", avg)
	}
}

// --- benchmarks: contrast the current JSON parse vs static read ---

func BenchmarkParseEmbeddedJSONBaseline(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		var reg map[string]interface{}
		if err := json.Unmarshal(embeddedMetaJSON, &reg); err != nil {
			b.Fatal(err)
		}
		sinkInt = len(reg)
	}
}

func BenchmarkReadStaticRegistry(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		sinkInt = deepReadStatic()
	}
}
