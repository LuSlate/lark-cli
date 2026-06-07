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

func TestDocsCreateV2HTML5BlockResources(t *testing.T) {
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
	resources := decodeHTML5Resources(t, body["resources"].(string))
	if got := resources[html5BlockTag]["html5_1"].Data; got != "<html><body>hello</body></html>" {
		t.Fatalf("resources html data = %q", got)
	}
}

func TestDocsUpdateV2HTML5BlockResources(t *testing.T) {
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
	resources := decodeHTML5Resources(t, body["resources"].(string))
	if got := resources[html5BlockTag]["html5_1"].Data; got != "<section>updated</section>" {
		t.Fatalf("resources html data = %q", got)
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

func TestDocsFetchV2MaterializesHTML5BlockResources(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)

	f, stdout, _, reg := cmdutil.TestFactory(t, docsTestConfigWithAppID("docs-html5-fetch"))
	registerDocsAIStub(reg, "POST", "/open-apis/docs_ai/v1/documents/doxcn_fetch/fetch", map[string]interface{}{
		"document": map[string]interface{}{
			"document_id": "doxcn_fetch",
			"revision_id": float64(3),
			"content":     `<docx><html5-block data-ref="html5_1"></html5-block></docx>`,
			"resources":   `{"html5-block":{"html5_1":{"data":"<html><main>fetched</main></html>"}}}`,
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

	written := filepath.Join(dir, html5BlockResourceRoot, "doxcn_fetch", "html5_1.html")
	raw, err := os.ReadFile(written)
	if err != nil {
		t.Fatalf("ReadFile(%s) error: %v", written, err)
	}
	if string(raw) != "<html><main>fetched</main></html>" {
		t.Fatalf("materialized html = %q", raw)
	}

	var envelope map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("decode stdout: %v\n%s", err, stdout.String())
	}
	data, _ := envelope["data"].(map[string]interface{})
	doc, _ := data["document"].(map[string]interface{})
	if got := doc["content"].(string); !strings.Contains(got, `path="@./doc-fetch-resources/doxcn_fetch/html5_1.html"`) {
		t.Fatalf("content was not rewritten to local path: %s", got)
	}
	if _, ok := doc["resources"]; ok {
		t.Fatalf("resources should be removed after materializing html files: %#v", doc)
	}
}

func TestDocsCreateV2HTML5BlockRejectsDataRefInput(t *testing.T) {
	f, stdout, _, _ := cmdutil.TestFactory(t, docsCreateTestConfig(t, ""))

	err := runDocsCreateShortcut(t, f, stdout, []string{
		"+create",
		"--api-version", "v2",
		"--content", `<html5-block data-ref="html5_1"></html5-block>`,
		"--as", "user",
	})
	if err == nil || !strings.Contains(err.Error(), `must use path="@relative.html"`) {
		t.Fatalf("expected data-ref misuse error, got: %v", err)
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

func TestDocsFetchV2MissingHTML5BlockResourceFails(t *testing.T) {
	dir := t.TempDir()
	cmdutil.TestChdir(t, dir)

	f, stdout, _, reg := cmdutil.TestFactory(t, docsTestConfigWithAppID("docs-html5-fetch-missing"))
	registerDocsAIStub(reg, "POST", "/open-apis/docs_ai/v1/documents/doxcn_fetch/fetch", map[string]interface{}{
		"document": map[string]interface{}{
			"document_id": "doxcn_fetch",
			"revision_id": float64(3),
			"content":     `<docx><html5-block data-ref="html5_missing"></html5-block></docx>`,
			"resources":   `{"html5-block":{}}`,
		},
	})

	err := mountAndRunDocs(t, DocsFetch, []string{
		"+fetch",
		"--api-version", "v2",
		"--doc", "doxcn_fetch",
		"--format", "json",
		"--as", "user",
	}, f, stdout)
	if err == nil || !strings.Contains(err.Error(), "Re-run fetch or check that the upstream document.resources field includes this ref") {
		t.Fatalf("expected missing resource error, got: %v", err)
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
	resources := decodeHTML5Resources(t, body["resources"].(string))
	if got := resources[html5BlockTag]["html5_1"].Data; got != "<html><body>markdown</body></html>" {
		t.Fatalf("resources html data = %q", got)
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

func decodeHTML5Resources(t *testing.T, raw string) html5BlockResourceMap {
	t.Helper()
	var resources html5BlockResourceMap
	if err := json.Unmarshal([]byte(raw), &resources); err != nil {
		t.Fatalf("decode resources: %v\n%s", err, raw)
	}
	return resources
}
