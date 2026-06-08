// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package doc

import (
	"bytes"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/httpmock"
	"github.com/larksuite/cli/internal/output"
)

func TestDocsCreateV2HTML5BlockReferenceMapFromPath(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)
	if err := os.WriteFile("widget.html", []byte("<html><body>hello</body></html>"), 0o600); err != nil {
		t.Fatalf("WriteFile() error: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, docsCreateTestConfig(t, ""))
	stub := registerDocsAIStub(reg, "POST", "/open-apis/docs_ai/v1/documents", map[string]interface{}{
		"document": map[string]interface{}{
			"document_id": "doxcn_new_doc",
			"revision_id": float64(1),
		},
	})

	err := runDocsCreateShortcut(t, f, stdout, []string{
		"+create",
		"--api-version", "v2",
		"--content", `<title>demo</title><html5-block path="@widget.html"></html5-block>`,
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	body := decodeRequestBody(t, stub.CapturedBody)
	if got := body["content"].(string); !strings.Contains(got, `<html5-block data-ref="html5_1"></html5-block>`) {
		t.Fatalf("content was not rewritten with data-ref: %s", got)
	}
	refMap := decodeHTML5ReferenceMap(t, body["reference_map"])
	if got := refMap[html5BlockTag]["html5_1"].Data; got != "<html><body>hello</body></html>" {
		t.Fatalf("reference_map html data = %q", got)
	}
	if _, ok := body["resources"]; ok {
		t.Fatalf("request body must not use resources: %#v", body)
	}
}

func TestDocsUpdateV2HTML5BlockReferenceMapFromPath(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)
	if err := os.WriteFile("widget.html", []byte("<section>updated</section>"), 0o600); err != nil {
		t.Fatalf("WriteFile() error: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, docsTestConfigWithAppID("docs-html5-update"))
	stub := registerDocsAIStub(reg, "PUT", "/open-apis/docs_ai/v1/documents/doxcn_doc", map[string]interface{}{
		"document": map[string]interface{}{
			"revision_id": float64(2),
			"new_blocks": []interface{}{
				map[string]interface{}{
					"block_type":  "html5-block",
					"block_id":    "blk_html5",
					"block_token": "blk_html5",
				},
			},
		},
		"result": "success",
	})

	err := mountAndRunDocs(t, DocsUpdate, []string{
		"+update",
		"--api-version", "v2",
		"--doc", "doxcn_doc",
		"--command", "append",
		"--content", `<html5-block path="@widget.html"></html5-block>`,
		"--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	body := decodeRequestBody(t, stub.CapturedBody)
	if got := body["content"].(string); got != `<html5-block data-ref="html5_1"></html5-block>` {
		t.Fatalf("content = %q", got)
	}
	refMap := decodeHTML5ReferenceMap(t, body["reference_map"])
	if got := refMap[html5BlockTag]["html5_1"].Data; got != "<section>updated</section>" {
		t.Fatalf("reference_map html data = %q", got)
	}

	var envelope map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("decode stdout: %v\n%s", err, stdout.String())
	}
	data, _ := envelope["data"].(map[string]interface{})
	doc, _ := data["document"].(map[string]interface{})
	if blocks, _ := doc["new_blocks"].([]interface{}); len(blocks) != 1 {
		t.Fatalf("new_blocks not preserved in stdout: %#v", doc)
	}
}

func TestDocsUpdateV2FailedResultExitsNonZeroWithRawOutput(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, docsTestConfigWithAppID("docs-html5-update-failed"))
	registerDocsAIStub(reg, "PUT", "/open-apis/docs_ai/v1/documents/doxcn_doc", map[string]interface{}{
		"result": "failed",
		"warnings": []interface{}{
			map[string]interface{}{
				"code":    float64(1011),
				"message": "Instruction produced no document changes for <html5-block data-ref=\"html5_1\"></html5-block>",
			},
		},
	})

	err := mountAndRunDocs(t, DocsUpdate, []string{
		"+update",
		"--api-version", "v2",
		"--doc", "doxcn_doc",
		"--command", "block_delete",
		"--block-id", "stale_block_id",
		"--as", "user",
	}, f, stdout)
	var pfErr *output.PartialFailureError
	if !errors.As(err, &pfErr) || pfErr.Code != output.ExitAPI {
		t.Fatalf("expected API partial-failure exit, got %T: %v", err, err)
	}

	var envelope map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("decode stdout: %v\n%s", err, stdout.String())
	}
	if ok, _ := envelope["ok"].(bool); ok {
		t.Fatalf("stdout envelope should mark failed docs_ai result as ok=false: %s", stdout.String())
	}
	data, _ := envelope["data"].(map[string]interface{})
	if got, _ := data["result"].(string); got != "failed" {
		t.Fatalf("data.result = %q, stdout: %s", got, stdout.String())
	}
	warnings, _ := data["warnings"].([]interface{})
	if len(warnings) != 1 {
		t.Fatalf("warnings not preserved in stdout: %#v", data)
	}
	if !strings.Contains(stdout.String(), `<html5-block data-ref=\"html5_1\"></html5-block>`) {
		t.Fatalf("raw XML/HTML should not be escaped in failed output: %s", stdout.String())
	}
}

func TestDocsFetchV2HTML5BlockKeepsSmallReferenceMapInline(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)

	f, stdout, _, reg := cmdutil.TestFactory(t, docsTestConfigWithAppID("docs-html5-fetch"))
	registerDocsAIStub(reg, "POST", "/open-apis/docs_ai/v1/documents/doxcn_fetch/fetch", map[string]interface{}{
		"document": map[string]interface{}{
			"document_id": "doxcn_fetch",
			"revision_id": float64(3),
			"content":     `<docx><html5-block data-ref="html5_1"></html5-block></docx>`,
			"reference_map": map[string]interface{}{
				"html5-block": map[string]interface{}{
					"html5_1": map[string]interface{}{"data": "<html><main>fetched</main></html>"},
				},
			},
		},
	})

	err := mountAndRunDocs(t, DocsFetch, []string{
		"+fetch",
		"--api-version", "v2",
		"--doc", "doxcn_fetch",
		"--format", "json",
		"--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	written := filepath.Join(dir, html5BlockReferenceRoot, "doxcn_fetch", "html5_1.html")
	if _, err := os.Stat(written); err == nil {
		t.Fatalf("small html should stay inline, got file %s", written)
	}

	var envelope map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("decode stdout: %v\n%s", err, stdout.String())
	}
	data, _ := envelope["data"].(map[string]interface{})
	doc, _ := data["document"].(map[string]interface{})
	if got := doc["content"].(string); !strings.Contains(got, `<html5-block data-ref="html5_1"></html5-block>`) {
		t.Fatalf("content should keep data-ref: %s", got)
	}
	refMap := decodeHTML5ReferenceMap(t, doc["reference_map"])
	if got := refMap[html5BlockTag]["html5_1"].Data; got != "<html><main>fetched</main></html>" {
		t.Fatalf("reference_map html data = %q", got)
	}
	if _, ok := doc["resources"]; ok {
		t.Fatalf("fetch output must not use resources: %#v", doc)
	}
	if suggestions, _ := data["suggestions"].([]interface{}); len(suggestions) != 1 || suggestions[0] != html5BlockSuggestionRead {
		t.Fatalf("suggestions not preserved: %#v", data["suggestions"])
	}
}

func TestDocsFetchV2HTML5BlockLargeReferenceMapUsesPath(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)

	largeHTML := "<html><main>" + strings.Repeat("x", html5BlockReferenceMaxRaw+1) + "</main></html>"
	f, stdout, _, reg := cmdutil.TestFactory(t, docsTestConfigWithAppID("docs-html5-fetch-large"))
	registerDocsAIStub(reg, "POST", "/open-apis/docs_ai/v1/documents/doxcn_fetch/fetch", map[string]interface{}{
		"document": map[string]interface{}{
			"document_id": "doxcn_fetch",
			"revision_id": float64(3),
			"content":     `<docx><html5-block data-ref="html5_1"></html5-block></docx>`,
			"reference_map": map[string]interface{}{
				"html5-block": map[string]interface{}{
					"html5_1": map[string]interface{}{"data": largeHTML},
				},
			},
		},
	})

	err := mountAndRunDocs(t, DocsFetch, []string{
		"+fetch",
		"--api-version", "v2",
		"--doc", "doxcn_fetch",
		"--format", "json",
		"--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	written := filepath.Join(dir, html5BlockReferenceRoot, "doxcn_fetch", "html5_1.html")
	raw, err := os.ReadFile(written)
	if err != nil {
		t.Fatalf("ReadFile(%s) error: %v", written, err)
	}
	if string(raw) != largeHTML {
		t.Fatalf("materialized html = %q", raw)
	}

	var envelope map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("decode stdout: %v\n%s", err, stdout.String())
	}
	data, _ := envelope["data"].(map[string]interface{})
	doc, _ := data["document"].(map[string]interface{})
	if got := doc["content"].(string); strings.Contains(got, `path="@`) || !strings.Contains(got, `data-ref="html5_1"`) {
		t.Fatalf("content should keep data-ref and not path: %s", got)
	}
	refMap := decodeHTML5ReferenceMap(t, doc["reference_map"])
	entry := refMap[html5BlockTag]["html5_1"]
	if entry.Data != "" || entry.Path != "@doc-fetch-resources/doxcn_fetch/html5_1.html" {
		t.Fatalf("large html should be represented as path, got %#v", entry)
	}
}

func TestDocsCreateV2HTML5BlockReferenceMapAdvancedInput(t *testing.T) {
	f, stdout, _, reg := cmdutil.TestFactory(t, docsCreateTestConfig(t, ""))
	stub := registerDocsAIStub(reg, "POST", "/open-apis/docs_ai/v1/documents", map[string]interface{}{
		"document": map[string]interface{}{
			"document_id": "doxcn_new_doc",
			"revision_id": float64(1),
		},
	})

	err := runDocsCreateShortcut(t, f, stdout, []string{
		"+create",
		"--api-version", "v2",
		"--content", `<html5-block data-ref="html5_1"></html5-block>`,
		"--reference-map", `{"html5-block":{"html5_1":{"data":"<html></html>"}}}`,
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	body := decodeRequestBody(t, stub.CapturedBody)
	if got := body["content"].(string); got != `<html5-block data-ref="html5_1"></html5-block>` {
		t.Fatalf("content = %q", got)
	}
	refMap := decodeHTML5ReferenceMap(t, body["reference_map"])
	if got := refMap[html5BlockTag]["html5_1"].Data; got != "<html></html>" {
		t.Fatalf("reference_map html data = %q", got)
	}
}

func TestDocsCreateV2HTML5BlockRejectsMissingReferenceMap(t *testing.T) {
	f, stdout, _, _ := cmdutil.TestFactory(t, docsCreateTestConfig(t, ""))

	err := runDocsCreateShortcut(t, f, stdout, []string{
		"+create",
		"--api-version", "v2",
		"--content", `<html5-block data-ref="html5_1"></html5-block>`,
		"--as", "user",
	})
	if err == nil || !strings.Contains(err.Error(), `reference_map.html5-block.html5_1 is required`) {
		t.Fatalf("expected missing reference_map error, got: %v", err)
	}
}

func TestDocsCreateV2HTML5BlockRejectsInternalDataAttr(t *testing.T) {
	f, stdout, _, _ := cmdutil.TestFactory(t, docsCreateTestConfig(t, ""))

	err := runDocsCreateShortcut(t, f, stdout, []string{
		"+create",
		"--api-version", "v2",
		"--content", `<html5-block data="PGh0bWw+PC9odG1sPg=="></html5-block>`,
		"--as", "user",
	})
	if err == nil || !strings.Contains(err.Error(), `html5-block data is reserved for SDK internals`) {
		t.Fatalf("expected internal data attr error, got: %v", err)
	}
}

func TestDocsCreateV2HTML5BlockPathReadFailure(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)
	f, stdout, _, _ := cmdutil.TestFactory(t, docsCreateTestConfig(t, ""))

	err := runDocsCreateShortcut(t, f, stdout, []string{
		"+create",
		"--api-version", "v2",
		"--content", `<html5-block path="@missing.html"></html5-block>`,
		"--as", "user",
	})
	if err == nil || !strings.Contains(err.Error(), `html5-block path "missing.html" cannot be read from the current working directory`) {
		t.Fatalf("expected path read error, got: %v", err)
	}
}

func TestDocsCreateV2HTML5BlockRejectsInlineContent(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)
	if err := os.WriteFile("widget.html", []byte("<section>from file</section>"), 0o600); err != nil {
		t.Fatalf("WriteFile() error: %v", err)
	}

	f, stdout, _, _ := cmdutil.TestFactory(t, docsCreateTestConfig(t, ""))
	err := runDocsCreateShortcut(t, f, stdout, []string{
		"+create",
		"--api-version", "v2",
		"--content", `<html5-block path="@widget.html"><section>inline</section></html5-block>`,
		"--as", "user",
	})
	if err == nil || !strings.Contains(err.Error(), `html5-block content must be loaded from path="@relative.html"`) {
		t.Fatalf("expected inline content error, got: %v", err)
	}
}

func TestDocsFetchV2MissingHTML5BlockReferenceFails(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)

	f, stdout, _, reg := cmdutil.TestFactory(t, docsTestConfigWithAppID("docs-html5-fetch-missing"))
	registerDocsAIStub(reg, "POST", "/open-apis/docs_ai/v1/documents/doxcn_fetch/fetch", map[string]interface{}{
		"document": map[string]interface{}{
			"document_id": "doxcn_fetch",
			"revision_id": float64(3),
			"content":     `<docx><html5-block data-ref="html5_missing"></html5-block></docx>`,
			"reference_map": map[string]interface{}{
				"html5-block": map[string]interface{}{
					"html5_1": map[string]interface{}{"data": "<html></html>"},
				},
			},
		},
	})

	err := mountAndRunDocs(t, DocsFetch, []string{
		"+fetch",
		"--api-version", "v2",
		"--doc", "doxcn_fetch",
		"--format", "json",
		"--as", "user",
	}, f, stdout)
	if err == nil || !strings.Contains(err.Error(), "Re-run fetch or check that the upstream document.reference_map field includes this ref") {
		t.Fatalf("expected missing reference_map error, got: %v", err)
	}
}

func TestHTML5BlockMarkdownCodeFenceIsIgnored(t *testing.T) {
	content := "```xml\n<html5-block data-ref=\"html5_1\"></html5-block>\n```\n"
	if hasProcessableHTML5Block("markdown", content) {
		t.Fatalf("html5-block inside markdown code fence should be ignored")
	}
}

func TestPrepareHTML5BlockWriteContentMarkdownRaw(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)
	if err := os.WriteFile("widget.html", []byte("<html><body>markdown</body></html>"), 0o600); err != nil {
		t.Fatalf("WriteFile() error: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, docsCreateTestConfig(t, ""))
	stub := registerDocsAIStub(reg, "POST", "/open-apis/docs_ai/v1/documents", map[string]interface{}{
		"document": map[string]interface{}{
			"document_id": "doxcn_new_doc",
			"revision_id": float64(1),
		},
	})

	err := runDocsCreateShortcut(t, f, stdout, []string{
		"+create",
		"--api-version", "v2",
		"--doc-format", "markdown",
		"--content", "before\n<html5-block path=\"@widget.html\"></html5-block>\nafter",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	body := decodeRequestBody(t, stub.CapturedBody)
	if got := body["content"].(string); !strings.Contains(got, `<html5-block data-ref="html5_1"></html5-block>`) {
		t.Fatalf("content was not rewritten: %s", got)
	}
	refMap := decodeHTML5ReferenceMap(t, body["reference_map"])
	if got := refMap[html5BlockTag]["html5_1"].Data; got != "<html><body>markdown</body></html>" {
		t.Fatalf("reference_map html data = %q", got)
	}
}

func TestDocsUpdateV2HTML5BlockInputRoundTrip(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)
	resourceDir := filepath.Join(html5BlockReferenceRoot, "doxcn_fetch")
	if err := os.MkdirAll(resourceDir, 0o700); err != nil {
		t.Fatalf("MkdirAll() error: %v", err)
	}
	if err := os.WriteFile(filepath.Join(resourceDir, "html5_1.html"), []byte("<html><main>roundtrip</main></html>"), 0o600); err != nil {
		t.Fatalf("WriteFile() error: %v", err)
	}
	fetchJSON := `{"ok":true,"data":{"document":{"content":"<docx><html5-block data-ref=\"html5_1\"></html5-block></docx>","reference_map":{"html5-block":{"html5_1":{"path":"@doc-fetch-resources/doxcn_fetch/html5_1.html"}}}}}}`
	if err := os.WriteFile("fetch.json", []byte(fetchJSON), 0o600); err != nil {
		t.Fatalf("WriteFile(fetch.json) error: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, docsTestConfigWithAppID("docs-html5-input"))
	stub := registerDocsAIStub(reg, "PUT", "/open-apis/docs_ai/v1/documents/doxcn_doc", map[string]interface{}{
		"document": map[string]interface{}{"revision_id": float64(2)},
		"result":   "success",
	})

	err := mountAndRunDocs(t, DocsUpdate, []string{
		"+update",
		"--api-version", "v2",
		"--doc", "doxcn_doc",
		"--command", "append",
		"--input", "@fetch.json",
		"--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	body := decodeRequestBody(t, stub.CapturedBody)
	if got := body["content"].(string); got != `<docx><html5-block data-ref="html5_1"></html5-block></docx>` {
		t.Fatalf("content = %q", got)
	}
	refMap := decodeHTML5ReferenceMap(t, body["reference_map"])
	entry := refMap[html5BlockTag]["html5_1"]
	if entry.Data != "<html><main>roundtrip</main></html>" || entry.Path != "" {
		t.Fatalf("reference path should be converted to data before API call: %#v", entry)
	}
}

func registerDocsAIStub(reg *httpmock.Registry, method string, url string, data map[string]interface{}) *httpmock.Stub {
	stub := &httpmock.Stub{
		Method: method,
		URL:    url,
		Body: map[string]interface{}{
			"code": 0,
			"msg":  "ok",
			"data": data,
		},
	}
	reg.Register(stub)
	return stub
}

func decodeRequestBody(t *testing.T, raw []byte) map[string]interface{} {
	t.Helper()
	var body map[string]interface{}
	if err := json.Unmarshal(bytes.TrimSpace(raw), &body); err != nil {
		t.Fatalf("decode request body: %v\n%s", err, raw)
	}
	return body
}

func decodeHTML5ReferenceMap(t *testing.T, raw interface{}) html5BlockReferenceMap {
	t.Helper()
	data, err := json.Marshal(raw)
	if err != nil {
		t.Fatalf("marshal reference_map: %v\n%#v", err, raw)
	}
	var refMap html5BlockReferenceMap
	if err := json.Unmarshal(data, &refMap); err != nil {
		t.Fatalf("decode reference_map: %v\n%s", err, data)
	}
	return refMap
}
