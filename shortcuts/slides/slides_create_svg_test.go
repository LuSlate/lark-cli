// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"testing"

	"github.com/spf13/cobra"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/httpmock"
)

const testSVGlidePage1 = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><rect slide:role="shape" x="80" y="80" width="320" height="180"/></svg>`
const testSVGlidePage2 = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><foreignObject slide:role="shape" slide:shape-type="text" x="80" y="80" width="320" height="80"><p xmlns="http://www.w3.org/1999/xhtml">second</p></foreignObject></svg>`

func TestSlidesCreateSVGMissingFileFlag(t *testing.T) {
	t.Parallel()

	f, stdout, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--title", "missing file",
		"--as", "user",
	})
	if err == nil {
		t.Fatal("expected missing --file error")
	}
	if !strings.Contains(err.Error(), "file") {
		t.Fatalf("err = %v, want mention of file", err)
	}
}

func TestSlidesCreateSVGFileMissing(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)

	f, stdout, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "missing.svg",
		"--title", "missing svg",
		"--as", "user",
	})
	if err == nil {
		t.Fatal("expected validation error for missing SVG")
	}
	if !strings.Contains(err.Error(), "missing.svg") {
		t.Fatalf("err = %v, want mention of missing.svg", err)
	}
}

func TestSlidesCreateSVGEmptyFile(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("empty.svg", nil, 0o644); err != nil {
		t.Fatalf("write empty.svg: %v", err)
	}

	f, stdout, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "empty.svg",
		"--title", "empty svg",
		"--as", "user",
	})
	if err == nil {
		t.Fatal("expected validation error for empty SVG")
	}
	if !strings.Contains(err.Error(), "empty.svg") || !strings.Contains(err.Error(), "empty") {
		t.Fatalf("err = %v, want empty.svg empty-file message", err)
	}
}

func TestSlidesCreateSVGExecuteCreatesSlidesInFileOrder(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page1.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page1.svg: %v", err)
	}
	if err := os.WriteFile("page2.svg", []byte(testSVGlidePage2), 0o644); err != nil {
		t.Fatalf("write page2.svg: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"xml_presentation_id": "pres_svg",
				"revision_id":         1,
			},
		},
	})
	slideStub1 := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_svg/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_1", "revision_id": 2}},
	}
	slideStub2 := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_svg/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_2", "revision_id": 3}},
	}
	reg.Register(slideStub1)
	reg.Register(slideStub2)
	registerBatchQueryStub(reg, "pres_svg", "https://x.feishu.cn/slides/pres_svg")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page1.svg",
		"--file", "page2.svg",
		"--title", "SVG Deck",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	data := decodeSlidesCreateEnvelope(t, stdout)
	if data["xml_presentation_id"] != "pres_svg" {
		t.Fatalf("xml_presentation_id = %v, want pres_svg", data["xml_presentation_id"])
	}
	if data["slides_added"] != float64(2) {
		t.Fatalf("slides_added = %v, want 2", data["slides_added"])
	}
	if data["revision_id"] != float64(3) {
		t.Fatalf("revision_id = %v, want latest revision 3", data["revision_id"])
	}
	slideIDs, ok := data["slide_ids"].([]interface{})
	if !ok || len(slideIDs) != 2 || slideIDs[0] != "slide_1" || slideIDs[1] != "slide_2" {
		t.Fatalf("slide_ids = %v, want [slide_1 slide_2]", data["slide_ids"])
	}

	assertSlideCreateBodyContains(t, slideStub1, `slide:contract-version="svglide-authoring-contract/v1"`)
	assertSlideCreateBodyContains(t, slideStub1, `<rect slide:role="shape" x="80" y="80" width="320" height="180"/>`)
	assertSlideCreateBodyContains(t, slideStub2, `slide:contract-version="svglide-authoring-contract/v1"`)
	assertSlideCreateBodyContains(t, slideStub2, `<foreignObject slide:role="shape" slide:shape-type="text" x="80" y="80" width="320" height="80">`)
}

func TestSlidesCreateSVGRequestHeaderPassesToCreateAndSlideCalls(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	createStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"xml_presentation_id": "pres_header",
				"revision_id":         1,
			},
		},
	}
	slideStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_header/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_header", "revision_id": 2}},
	}
	reg.Register(createStub)
	reg.Register(slideStub)
	registerBatchQueryStub(reg, "pres_header", "https://x.feishu.cn/slides/pres_header")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--title", "SVG Header Deck",
		"--request-header", "x-tt-env=ppe_pure_svg",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if got := createStub.CapturedHeaders.Get("x-tt-env"); got != "ppe_pure_svg" {
		t.Fatalf("create x-tt-env = %q, want ppe_pure_svg", got)
	}
	if got := slideStub.CapturedHeaders.Get("x-tt-env"); got != "ppe_pure_svg" {
		t.Fatalf("slide x-tt-env = %q, want ppe_pure_svg", got)
	}
	data := decodeSlidesCreateEnvelope(t, stdout)
	headers, _ := data["request_headers"].(map[string]interface{})
	if headers["x-tt-env"] != "ppe_pure_svg" {
		t.Fatalf("request_headers = %#v, want x-tt-env", data["request_headers"])
	}
}

func TestSlidesCreateSVGPPEProfilePassesFixedHeaders(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	createStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"xml_presentation_id": "pres_ppe", "revision_id": 1}},
	}
	slideStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_ppe/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_ppe", "revision_id": 2}},
	}
	reg.Register(createStub)
	reg.Register(slideStub)
	registerBatchQueryStub(reg, "pres_ppe", "https://x.feishu.cn/slides/pres_ppe")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--ppe-profile", "ppe_pure_svg",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	for _, stub := range []*httpmock.Stub{createStub, slideStub} {
		if got := stub.CapturedHeaders.Get("Env"); got != "Pre_release" {
			t.Fatalf("%s Env = %q, want Pre_release", stub.URL, got)
		}
		if got := stub.CapturedHeaders.Get("x-tt-env"); got != "ppe_pure_svg" {
			t.Fatalf("%s x-tt-env = %q, want ppe_pure_svg", stub.URL, got)
		}
		if got := stub.CapturedHeaders.Get("x-use-ppe"); got != "1" {
			t.Fatalf("%s x-use-ppe = %q, want 1", stub.URL, got)
		}
	}
	data := decodeSlidesCreateEnvelope(t, stdout)
	headers, _ := data["request_headers"].(map[string]interface{})
	for _, key := range []string{"Env", "x-tt-env", "x-use-ppe"} {
		if headers[key] == nil {
			t.Fatalf("request_headers = %#v, want %s", headers, key)
		}
	}
}

func TestSlidesCreateSVGRejectsArbitraryRequestHeader(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	f, stdout, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--request-header", "Env=prod",
		"--as", "user",
	})
	if err == nil {
		t.Fatal("expected arbitrary request header value error")
	}
	if !strings.Contains(err.Error(), "allowed SVGlide PPE headers") {
		t.Fatalf("err = %v, want whitelist message", err)
	}
}

func TestSlidesCreateSVGAppendSkipsCreateAndPostsSlides(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	var capturedRevisionID string
	slideStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_append/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_append", "revision_id": 8}},
		OnMatch: func(req *http.Request) {
			capturedRevisionID = req.URL.Query().Get("revision_id")
		},
	}
	reg.Register(slideStub)
	registerBatchQueryStub(reg, "pres_append", "https://x.feishu.cn/slides/pres_append")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--append-to-presentation", "pres_append",
		"--revision-id", "7",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var body map[string]interface{}
	if err := json.Unmarshal(slideStub.CapturedBody, &body); err != nil {
		t.Fatalf("decode slide body: %v", err)
	}
	assertSlideCreateBodyContains(t, slideStub, `slide:contract-version="svglide-authoring-contract/v1"`)
	data := decodeSlidesCreateEnvelope(t, stdout)
	if data["xml_presentation_id"] != "pres_append" || data["slides_added"] != float64(1) || data["revision_id"] != float64(8) {
		t.Fatalf("append result = %#v", data)
	}
	if capturedRevisionID != "7" {
		t.Fatalf("revision_id query = %q, want 7", capturedRevisionID)
	}
}

func TestSlidesCreateSVGAppendUploadsImagesAndPassesHeaders(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	svg := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><image slide:role="image" href="@hero.png" x="0" y="0" width="320" height="180"/></svg>`
	if err := os.WriteFile("page.svg", []byte(svg), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}
	if err := os.WriteFile("hero.png", testOneByOnePNG(t), 0o644); err != nil {
		t.Fatalf("write hero.png: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	uploadStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/drive/v1/medias/upload_all",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"file_token": "boxcn_uploaded_append"}},
	}
	slideStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_append_upload/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_append_upload", "revision_id": 4}},
	}
	reg.Register(uploadStub)
	reg.Register(slideStub)
	registerBatchQueryStub(reg, "pres_append_upload", "https://x.feishu.cn/slides/pres_append_upload")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--append-to-presentation", "pres_append_upload",
		"--ppe-profile", "ppe_pure_svg",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got := slideStub.CapturedHeaders.Get("x-tt-env"); got != "ppe_pure_svg" {
		t.Fatalf("append slide x-tt-env = %q, want ppe_pure_svg", got)
	}
	if got := slideStub.CapturedHeaders.Get("Env"); got != "Pre_release" {
		t.Fatalf("append slide Env = %q, want Pre_release", got)
	}
	data := decodeSlidesCreateEnvelope(t, stdout)
	if data["images_uploaded"] != float64(1) {
		t.Fatalf("images_uploaded = %v, want 1", data["images_uploaded"])
	}
	assertSlideCreateBodyContains(t, slideStub, `src="boxcn_uploaded_append"`)
	assertSlideCreateBodyContains(t, slideStub, `<metadata data-svglide-assets="svglide-assets/v1">`)
}

func TestSlidesCreateSVGFontFamilyRewritesTextContent(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	svg := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720">` +
		`<foreignObject slide:role="shape" slide:shape-type="text" x="80" y="80" width="320" height="80" style="font-family:Inter;color:#111;">` +
		`<div xmlns="http://www.w3.org/1999/xhtml"><span style="font-family:Arial;color:#222;">hello</span></div>` +
		`</foreignObject></svg>`
	if err := os.WriteFile("page.svg", []byte(svg), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"xml_presentation_id": "pres_font", "revision_id": 1}},
	})
	slideStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_font/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_font", "revision_id": 2}},
	}
	reg.Register(slideStub)
	registerBatchQueryStub(reg, "pres_font", "https://x.feishu.cn/slides/pres_font")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--font-family", "Noto Serif SC",
		"--title", "font family",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(slideStub.CapturedBody, &body); err != nil {
		t.Fatalf("decode slide body: %v", err)
	}
	slide, ok := body["slide"].(map[string]interface{})
	if !ok || len(slide) != 1 {
		t.Fatalf("slide create body should be {slide:{content}}, got: %v", body)
	}
	content := slide["content"].(string)
	for _, want := range []string{
		`font-family:Noto Serif SC`,
		`slide:contract-version="svglide-authoring-contract/v1"`,
	} {
		if !strings.Contains(content, want) {
			t.Fatalf("slide content missing %s: %s", want, content)
		}
	}
	for _, notWant := range []string{`font-family:Inter`, `font-family:Arial`} {
		if strings.Contains(content, notWant) {
			t.Fatalf("slide content should not contain %s: %s", notWant, content)
		}
	}
	if data := decodeSlidesCreateEnvelope(t, stdout); data["font_family"] != "Noto Serif SC" {
		t.Fatalf("font_family = %v, want Noto Serif SC", data["font_family"])
	}
}

func TestSlidesCreateSVGFontFamilyDryRunReportsSelectedFamily(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage2), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	f, stdout, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--font-family", "Noto Serif SC",
		"--dry-run",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var data map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &data); err != nil {
		t.Fatalf("decode dry-run output: %v\nraw=%s", err, stdout.String())
	}
	if data["font_family"] != "Noto Serif SC" {
		t.Fatalf("font_family = %v, want Noto Serif SC", data["font_family"])
	}
}

func TestSlidesCreateSVGLocalImageDryRunUsesRealMetadata(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	svg := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><image slide:role="image" href="@hero.png" x="0" y="0" width="320" height="180"/></svg>`
	if err := os.WriteFile("page.svg", []byte(svg), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}
	png := testTwoByTwoPNG(t)
	if err := os.WriteFile("hero.png", png, 0o644); err != nil {
		t.Fatalf("write hero.png: %v", err)
	}

	f, stdout, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--title", "dry-run image meta",
		"--dry-run",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	content := dryRunSlideContent(t, stdout)
	for _, want := range []string{
		`<metadata data-svglide-assets="svglide-assets/v1">`,
		`src="&lt;uploaded_file_token:hero.png&gt;"`,
		`name="hero.png"`,
		`mimeType="image/png"`,
		fmt.Sprintf(`size="%d"`, len(png)),
		`width="2"`,
		`height="2"`,
	} {
		if !strings.Contains(content, want) {
			t.Fatalf("dry-run slide content missing %s:\n%s", want, content)
		}
	}
}

func TestSlidesCreateSVGRejectsCustomFontFamily(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage2), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	f, stdout, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--font-family", "slide-font-0123456789abcdef0123456789abcdef",
		"--as", "user",
	})
	if err == nil {
		t.Fatal("expected custom font family to fail")
	}
	if !strings.Contains(err.Error(), "custom slide-font-* fonts are not supported") {
		t.Fatalf("err = %v, want custom font guidance", err)
	}
}

func TestSlidesCreateSVGRejectsUnsupportedRequestHeader(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	f, stdout, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--request-header", "authorization=secret",
		"--as", "user",
	})
	if err == nil {
		t.Fatal("expected unsupported request header error")
	}
	if !strings.Contains(err.Error(), "allowed SVGlide PPE headers") {
		t.Fatalf("err = %v, want supported-header message", err)
	}
}

func TestSlidesCreateSVGChartMarkerPassesThroughSlideContent(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	svg := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720">` + testSVGlideChartMarker(testSVGlideChartMetadata(testSVGlideChartSpecJSON())) + `</svg>`
	if err := os.WriteFile("chart.svg", []byte(svg), 0o644); err != nil {
		t.Fatalf("write chart.svg: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"xml_presentation_id": "pres_chart", "revision_id": 1}},
	})
	slideStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_chart/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_chart", "revision_id": 2}},
	}
	reg.Register(slideStub)
	registerBatchQueryStub(reg, "pres_chart", "https://x.feishu.cn/slides/pres_chart")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "chart.svg",
		"--title", "chart marker",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(slideStub.CapturedBody, &body); err != nil {
		t.Fatalf("decode slide body: %v", err)
	}
	if len(body) != 1 {
		t.Fatalf("slide create body should only contain slide wrapper, got: %v", body)
	}
	slide, ok := body["slide"].(map[string]interface{})
	if !ok || len(slide) != 1 {
		t.Fatalf("slide create body should be {slide:{content}}, got: %v", body)
	}
	content, ok := slide["content"].(string)
	if !ok {
		t.Fatalf("slide.content should be a string, got: %v", slide["content"])
	}
	for _, want := range []string{
		`slide:contract-version="svglide-authoring-contract/v1"`,
		`<g slide:role="chart" slide:chart-ref="chart-1" x="80" y="96" width="420" height="260">`,
		`data-svglide-chart="svglide-chart-inline/v1"`,
		`data-format="svglide-chart-spec-v1"`,
		`data-encoding="base64url-json"`,
		`data-payload-hash="sha256:`,
	} {
		if !strings.Contains(content, want) {
			t.Fatalf("content missing %s: %s", want, content)
		}
	}
}

func TestSlidesCreateSVGPartialFailureIncludesRecoveryContext(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page1.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page1.svg: %v", err)
	}
	if err := os.WriteFile("page2.svg", []byte(testSVGlidePage2), 0o644); err != nil {
		t.Fatalf("write page2.svg: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"xml_presentation_id": "pres_svg_partial",
				"revision_id":         1,
			},
		},
	})
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_svg_partial/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_ok", "revision_id": 2}},
	})
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_svg_partial/slide",
		Body: map[string]interface{}{
			"code": 400,
			"msg":  "invalid svg",
		},
	})

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page1.svg",
		"--file", "page2.svg",
		"--title", "partial svg",
		"--as", "user",
	})
	if err == nil {
		t.Fatal("expected slide create failure")
	}
	errMsg := err.Error()
	for _, want := range []string{"pres_svg_partial", "page 2/2", "1 slide(s) added", "slide_ok"} {
		if !strings.Contains(errMsg, want) {
			t.Fatalf("err = %v, want mention of %q", err, want)
		}
	}
}

func TestSlidesCreateSVGFailureExtractsSVGlideMarker(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"xml_presentation_id": "pres_marker", "revision_id": 1}},
	})
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_marker/slide",
		Body: map[string]interface{}{
			"code": 400,
			"msg":  `SVGLIDE_ERROR_JSON:{"type":"svg_validation_error","page_index":0,"tag_name":"foreignObject","hint":"Use supported elements"}`,
		},
	})

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--title", "marker",
		"--as", "user",
	})
	if err == nil {
		t.Fatal("expected marker failure")
	}
	errMsg := err.Error()
	for _, want := range []string{"svglide_error=", "svg_validation_error", "foreignObject", "Use supported elements"} {
		if !strings.Contains(errMsg, want) {
			t.Fatalf("err = %v, want marker field %q", err, want)
		}
	}
}

func TestSlidesCreateSVGAssetsReplaceImageAndInjectMetadata(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	svg := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><image slide:role="image" xlink:href='@./hero.png' x="0" y="0" width="320" height="180"/></svg>`
	if err := os.WriteFile("page.svg", []byte(svg), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}
	if err := os.WriteFile("assets.json", []byte(`{"@./hero.png":{"token":"boxcn_asset","name":"hero.png","mimeType":"image/png","size":1234,"width":640,"height":360}}`), 0o644); err != nil {
		t.Fatalf("write assets.json: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"xml_presentation_id": "pres_asset", "revision_id": 1}},
	})
	slideStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_asset/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_asset", "revision_id": 2}},
	}
	reg.Register(slideStub)
	registerBatchQueryStub(reg, "pres_asset", "https://x.feishu.cn/slides/pres_asset")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--assets", "assets.json",
		"--title", "assets",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(slideStub.CapturedBody, &body); err != nil {
		t.Fatalf("decode slide body: %v", err)
	}
	content := body["slide"].(map[string]interface{})["content"].(string)
	if strings.Contains(content, "@./hero.png") || strings.Contains(content, "xlink:href") {
		t.Fatalf("content should canonicalize asset placeholder: %s", content)
	}
	for _, want := range []string{
		`href="boxcn_asset"`,
		`<metadata data-svglide-assets="svglide-assets/v1">`,
		`<img xmlns="" src="boxcn_asset" name="hero.png" mimeType="image/png" size="1234" width="640" height="360" />`,
	} {
		if !strings.Contains(content, want) {
			t.Fatalf("content missing %s: %s", want, content)
		}
	}
	if _, ok := decodeSlidesCreateEnvelope(t, stdout)["images_uploaded"]; ok {
		t.Fatalf("--assets token mapping should not upload local images")
	}
}

func TestSlidesCreateSVGAssetsTokenOnlyRequiresMetadata(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	svg := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><image slide:role="image" xlink:href='@./hero.png' x="0" y="0" width="320" height="180"/></svg>`
	if err := os.WriteFile("page.svg", []byte(svg), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}
	if err := os.WriteFile("assets.json", []byte(`{"@./hero.png":"boxcn_asset"}`), 0o644); err != nil {
		t.Fatalf("write assets.json: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"xml_presentation_id": "pres_asset_token_only", "revision_id": 1}},
	})

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--assets", "assets.json",
		"--title", "assets token only",
		"--as", "user",
	})
	if err == nil {
		t.Fatal("expected token-only assets to fail before generating incomplete metadata")
	}
	for _, want := range []string{"incomplete SVG image asset metadata", "boxcn_asset", "name", "mimeType", "size", "width", "height"} {
		if !strings.Contains(err.Error(), want) {
			t.Fatalf("err = %v, want %q", err, want)
		}
	}
}

func TestSlidesCreateSVGNestedImageAssetsReplaceAndInjectMetadata(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	svg := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><g transform="translate(10 20)"><image slide:role="image" xlink:href='@./hero.png' x="0" y="0" width="320" height="180"/></g></svg>`
	if err := os.WriteFile("page.svg", []byte(svg), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}
	if err := os.WriteFile("assets.json", []byte(`{"@./hero.png":{"token":"boxcn_asset","name":"hero.png","mimeType":"image/png","size":1234,"width":640,"height":360}}`), 0o644); err != nil {
		t.Fatalf("write assets.json: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"xml_presentation_id": "pres_nested_asset", "revision_id": 1}},
	})
	slideStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_nested_asset/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_nested_asset", "revision_id": 2}},
	}
	reg.Register(slideStub)
	registerBatchQueryStub(reg, "pres_nested_asset", "https://x.feishu.cn/slides/pres_nested_asset")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--assets", "assets.json",
		"--title", "nested assets",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(slideStub.CapturedBody, &body); err != nil {
		t.Fatalf("decode slide body: %v", err)
	}
	content := body["slide"].(map[string]interface{})["content"].(string)
	for _, want := range []string{
		`href="boxcn_asset"`,
		`<metadata data-svglide-assets="svglide-assets/v1">`,
		`<img xmlns="" src="boxcn_asset" name="hero.png" mimeType="image/png" size="1234" width="640" height="360" />`,
		`<g transform="translate(10 20)">`,
	} {
		if !strings.Contains(content, want) {
			t.Fatalf("content missing %s: %s", want, content)
		}
	}
	for _, notWant := range []string{`xlink:href`, `@./hero.png`} {
		if strings.Contains(content, notWant) {
			t.Fatalf("content should not contain %s: %s", notWant, content)
		}
	}
	if _, ok := decodeSlidesCreateEnvelope(t, stdout)["images_uploaded"]; ok {
		t.Fatalf("--assets token mapping should not upload local images")
	}
}

func TestSlidesCreateSVGUploadsLocalImagesAndInjectsMetadata(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	svg := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><image slide:role="image" href="@hero.png" x="0" y="0" width="320" height="180"/></svg>`
	if err := os.WriteFile("page.svg", []byte(svg), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}
	png := testOneByOnePNG(t)
	if err := os.WriteFile("hero.png", png, 0o644); err != nil {
		t.Fatalf("write hero.png: %v", err)
	}

	f, stdout, _, reg := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"xml_presentation_id": "pres_upload", "revision_id": 1}},
	})
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/drive/v1/medias/upload_all",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"file_token": "boxcn_uploaded"}},
	})
	slideStub := &httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/slides_ai/v1/xml_presentations/pres_upload/slide",
		Body:   map[string]interface{}{"code": 0, "data": map[string]interface{}{"slide_id": "slide_upload", "revision_id": 2}},
	}
	reg.Register(slideStub)
	registerBatchQueryStub(reg, "pres_upload", "https://x.feishu.cn/slides/pres_upload")

	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--title", "upload",
		"--as", "user",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	data := decodeSlidesCreateEnvelope(t, stdout)
	if data["images_uploaded"] != float64(1) {
		t.Fatalf("images_uploaded = %v, want 1", data["images_uploaded"])
	}
	var body map[string]interface{}
	if err := json.Unmarshal(slideStub.CapturedBody, &body); err != nil {
		t.Fatalf("decode slide body: %v", err)
	}
	content := body["slide"].(map[string]interface{})["content"].(string)
	for _, want := range []string{
		`href="boxcn_uploaded"`,
		`<metadata data-svglide-assets="svglide-assets/v1">`,
		`src="boxcn_uploaded"`,
		`name="hero.png"`,
		`mimeType="image/png"`,
		fmt.Sprintf(`size="%d"`, len(png)),
		`width="1"`,
		`height="1"`,
	} {
		if !strings.Contains(content, want) {
			t.Fatalf("content missing %s: %s", want, content)
		}
	}
}

func runSlidesCreateSVGShortcut(t *testing.T, f *cmdutil.Factory, stdout *bytes.Buffer, args []string) error {
	t.Helper()
	parent := &cobra.Command{Use: "slides"}
	SlidesCreateSVG.Mount(parent, f)
	parent.SetArgs(args)
	parent.SilenceErrors = true
	parent.SilenceUsage = true
	if stdout != nil {
		stdout.Reset()
	}
	return parent.Execute()
}

func dryRunSlideContent(t *testing.T, stdout *bytes.Buffer) string {
	t.Helper()
	var data map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &data); err != nil {
		t.Fatalf("decode dry-run output: %v\nraw=%s", err, stdout.String())
	}
	api, _ := data["api"].([]interface{})
	if len(api) == 0 {
		t.Fatalf("dry-run output missing api steps: %#v", data)
	}
	step, _ := api[len(api)-1].(map[string]interface{})
	body, _ := step["body"].(map[string]interface{})
	slide, _ := body["slide"].(map[string]interface{})
	content, _ := slide["content"].(string)
	if content == "" {
		t.Fatalf("dry-run output missing slide content: %#v", step)
	}
	return content
}

func assertSlideCreateBodyContains(t *testing.T, stub *httpmock.Stub, want string) {
	t.Helper()
	var body map[string]interface{}
	if err := json.Unmarshal(stub.CapturedBody, &body); err != nil {
		t.Fatalf("decode slide body: %v\nraw=%s", err, string(stub.CapturedBody))
	}
	slide, _ := body["slide"].(map[string]interface{})
	content, _ := slide["content"].(string)
	if !strings.Contains(content, want) {
		t.Fatalf("slide content = %s\nwant to contain %s", content, want)
	}
}

func registerBatchQueryStub(_ *httpmock.Registry, _, _ string) {
	// fillPresentationResult now builds presentation URLs locally, so SVG create
	// tests keep this helper as a no-op compatibility shim for older assertions.
}

func testOneByOnePNG(t *testing.T) []byte {
	t.Helper()
	data, err := base64.StdEncoding.DecodeString("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
	if err != nil {
		t.Fatalf("decode test PNG: %v", err)
	}
	return data
}

func testTwoByTwoPNG(t *testing.T) []byte {
	t.Helper()
	data, err := base64.StdEncoding.DecodeString("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAFElEQVR4nGNQT379/72Ly38GGAMAVT4J1YcAuVoAAAAASUVORK5CYII=")
	if err != nil {
		t.Fatalf("decode test PNG: %v", err)
	}
	return data
}
