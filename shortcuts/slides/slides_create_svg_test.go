// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"bytes"
	"encoding/json"
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

	assertSlideCreateBodyContains(t, slideStub1, testSVGlidePage1)
	assertSlideCreateBodyContains(t, slideStub2, testSVGlidePage2)
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
	if err := os.WriteFile("assets.json", []byte(`{"@./hero.png":"boxcn_asset"}`), 0o644); err != nil {
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
	for _, want := range []string{`href="boxcn_asset"`, `<metadata data-svglide-assets="true">`, `<img src="boxcn_asset" />`} {
		if !strings.Contains(content, want) {
			t.Fatalf("content missing %s: %s", want, content)
		}
	}
	if _, ok := decodeSlidesCreateEnvelope(t, stdout)["images_uploaded"]; ok {
		t.Fatalf("--assets token mapping should not upload local images")
	}
}

func TestSlidesCreateSVGNestedImageAssetsReplaceAndInjectMetadata(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	svg := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><g transform="translate(10 20)"><image slide:role="image" xlink:href='@./hero.png' x="0" y="0" width="320" height="180"/></g></svg>`
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
		`<metadata data-svglide-assets="true">`,
		`<img src="boxcn_asset" />`,
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
	if err := os.WriteFile("hero.png", []byte("png"), 0o644); err != nil {
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
	for _, want := range []string{`href="boxcn_uploaded"`, `<img src="boxcn_uploaded" />`} {
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
