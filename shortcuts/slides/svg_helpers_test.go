// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"reflect"
	"strings"
	"testing"
)

func TestExtractSVGImagePlaceholderPaths(t *testing.T) {
	t.Parallel()

	svgs := []string{
		`<svg><image slide:role="image" href="@./hero.png"/><a href="@./link.png"/></svg>`,
		`<svg><image xlink:href='@./hero.png'/><image href = "@./other.png"/></svg>`,
	}
	got := extractSVGImagePlaceholderPaths(svgs, map[string]string{"@./other.png": "boxcn_other"})
	want := []string{"./hero.png"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %v, want %v", got, want)
	}
}

func TestRewriteSVGImagePlaceholdersWithTokens(t *testing.T) {
	t.Parallel()

	in := `<svg><image slide:role="image" href="@./hero.png"/><image xlink:href='@./logo.png'/><image data-href="@./ignored.png"/><a href="@./link.png">link</a><image href="https://example.com/noop.png"/></svg>`
	got, tokens := rewriteSVGImagePlaceholdersWithTokens(in, map[string]string{
		"./hero.png": "boxcn_hero",
		"./logo.png": "boxcn_logo",
	})
	for _, want := range []string{`href="boxcn_hero"`, `href="boxcn_logo"`} {
		if !strings.Contains(got, want) {
			t.Fatalf("rewritten SVG missing %s: %s", want, got)
		}
	}
	if strings.Contains(got, "xlink:href") {
		t.Fatalf("rewritten SVG must not retain xlink:href: %s", got)
	}
	if !strings.Contains(got, `<a href="@./link.png">`) {
		t.Fatalf("non-image href should be untouched: %s", got)
	}
	if !strings.Contains(got, `data-href="@./ignored.png"`) {
		t.Fatalf("non-href image attribute should be untouched: %s", got)
	}
	wantTokens := []string{"boxcn_hero", "boxcn_logo"}
	if !reflect.DeepEqual(tokens, wantTokens) {
		t.Fatalf("tokens = %v, want %v", tokens, wantTokens)
	}
}

func TestInjectSVGTransportAssetMetadata(t *testing.T) {
	t.Parallel()

	in := `<?xml version="1.0"?><!DOCTYPE svg><!-- lead --><svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect/></svg>`
	got, err := injectSVGTransportAssetMetadata(in, []string{"boxcn_a", "boxcn_b", "boxcn_a"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	rootIdx := strings.Index(got, "<svg")
	metaIdx := strings.Index(got, `<metadata data-svglide-assets="true">`)
	if rootIdx < 0 || metaIdx < rootIdx {
		t.Fatalf("metadata should be injected inside root <svg>, got: %s", got)
	}
	if strings.Count(got, `src="boxcn_a"`) != 1 {
		t.Fatalf("boxcn_a should be deduped, got: %s", got)
	}
	if !strings.Contains(got, `src="boxcn_b"`) {
		t.Fatalf("boxcn_b missing, got: %s", got)
	}
}

func TestInjectSVGTransportAssetMetadataMergesExisting(t *testing.T) {
	t.Parallel()

	in := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><metadata data-svglide-assets="true"><img src="boxcn_a" /></metadata><image href="boxcn_a"/></svg>`
	got, err := injectSVGTransportAssetMetadata(in, []string{"boxcn_a", "boxcn_b"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if strings.Count(got, `<metadata data-svglide-assets="true">`) != 1 {
		t.Fatalf("should keep a single transport metadata block, got: %s", got)
	}
	if strings.Count(got, `src="boxcn_a"`) != 1 {
		t.Fatalf("boxcn_a should remain deduped, got: %s", got)
	}
	if !strings.Contains(got, `src="boxcn_b"`) {
		t.Fatalf("boxcn_b should be appended, got: %s", got)
	}
}

func TestEnsureSVGlideRootContractVersionInjectsMissingVersion(t *testing.T) {
	t.Parallel()

	in := `<?xml version="1.0"?><!DOCTYPE svg><!-- lead --><svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></svg>`
	got, err := ensureSVGlideRootContractVersion(in, "page.svg")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(got, `slide:contract-version="svglide-authoring-contract/v1"`) {
		t.Fatalf("contract version missing after normalization: %s", got)
	}
	if strings.Index(got, `slide:contract-version`) > strings.Index(got, `><rect`) {
		t.Fatalf("contract version should be injected on the root open tag: %s", got)
	}
	if err := validateSVGlideSVG(got, "page.svg"); err != nil {
		t.Fatalf("normalized SVG should pass validation: %v", err)
	}
}

func TestEnsureSVGlideRootContractVersionRejectsWrongVersion(t *testing.T) {
	t.Parallel()

	in := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" slide:contract-version="old"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></svg>`
	_, err := ensureSVGlideRootContractVersion(in, "page.svg")
	if err == nil {
		t.Fatal("expected wrong contract-version to fail")
	}
	if !strings.Contains(err.Error(), `slide:contract-version="svglide-authoring-contract/v1"`) {
		t.Fatalf("error = %v, want contract-version guidance", err)
	}
}

func TestValidateSVGlideSVGRecursiveChildren(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		svg     string
		wantErr string
	}{
		{
			name: "supported shape rect",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></svg>`,
		},
		{
			name: "supported text foreignObject",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><foreignObject slide:role="shape" slide:shape-type="text" x="0" y="0" width="200" height="80"><p xmlns="http://www.w3.org/1999/xhtml">hello</p></foreignObject></svg>`,
		},
		{
			name: "supported image href",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><image slide:role="image" href="boxcn_img" x="0" y="0" width="100" height="60"/></svg>`,
		},
		{
			name: "supported image xlink href before rewrite",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><image slide:role="image" xlink:href="@./hero.png" x="0" y="0" width="100" height="60"/></svg>`,
		},
		{
			name: "supported path commands",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><path slide:role="shape" d="M1e-3 0 L80 0 H120 V40 C120 60 100 80 80 80 Q40 80 20 40 Z" fill="#123456"/></svg>`,
		},
		{
			name: "defs and metadata are ignored",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><defs><rect id="r"/></defs><metadata data-svglide-assets="true"><img src="boxcn_img"/></metadata><circle slide:role="shape" cx="50" cy="50" r="20"/></svg>`,
		},
		{
			name: "group container with role-fixed child",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><g fill="#112233" transform="translate(10 20)"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></g></svg>`,
		},
		{
			name: "nested svg container with role-fixed child",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><svg viewBox="0 0 100 100"><circle slide:role="shape" cx="50" cy="50" r="20"/></svg></svg>`,
		},
		{
			name: "group container ignores its own role",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><g slide:role="shape"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></g></svg>`,
		},
		{
			name: "nested svg container ignores its own role",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><svg slide:role="shape" viewBox="0 0 100 100"><circle slide:role="shape" cx="50" cy="50" r="20"/></svg></svg>`,
		},
		{
			name: "root chart marker with inline payload",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">` + testSVGlideChartMarker(testSVGlideChartMetadata(`<chart><chartData /></chart>`)) + `</svg>`,
		},
		{
			name: "style and nested defs are ignored",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><style>.primary{fill:#123456}</style><g><defs><linearGradient id="g"><stop offset="0%" stop-color="#fff"/><stop offset="100%" stop-color="#000"/></linearGradient></defs></g><rect slide:role="shape" class="primary" x="0" y="0" width="100" height="60" fill="url(#g)"/></svg>`,
		},
		{
			name: "filter and shadow styles are preserved",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><style>.card{filter:drop-shadow(2px 4px 8px rgba(0,0,0,.2));box-shadow:0 8px 20px rgba(0,0,0,.18)}</style><g><defs><filter id="shadow"><feDropShadow dx="2" dy="3" stdDeviation="5" flood-color="#000" flood-opacity=".25"/></filter></defs></g><rect slide:role="shape" class="card" x="0" y="0" width="100" height="60" filter="url(#shadow)"/></svg>`,
		},
		{
			name: "foreignObject XHTML subtree is not role-validated",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><foreignObject slide:role="shape" slide:shape-type="text" x="0" y="0" width="200" height="80"><div xmlns="http://www.w3.org/1999/xhtml"><span>hello</span></div></foreignObject></svg>`,
		},
		{
			name: "foreignObject XHTML br is allowed",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><foreignObject slide:role="shape" slide:shape-type="text" x="0" y="0" width="200" height="80"><div xmlns="http://www.w3.org/1999/xhtml">hello<br />world</div></foreignObject></svg>`,
		},
		{
			name:    "namespaced root is rejected with precise message",
			svg:     `<svg:svg xmlns:svg="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></svg:svg>`,
			wantErr: `root element must be non-namespaced <svg>`,
		},
		{
			name:    "root child missing role",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect x="0" y="0" width="100" height="60"/></svg>`,
			wantErr: `<rect> must include slide:role="shape" or slide:role="image"`,
		},
		{
			name:    "group child missing role is rejected",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><g><rect x="0" y="0" width="100" height="60"/></g></svg>`,
			wantErr: `<rect> must include slide:role="shape" or slide:role="image"`,
		},
		{
			name:    "unsupported text element remains rejected",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><text slide:role="shape" x="0" y="20">bad</text></svg>`,
			wantErr: `<text slide:role="shape"> is not supported by SVGlide`,
		},
		{
			name:    "rect shape requires geometry",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="shape" x="0" y="0" height="60"/></svg>`,
			wantErr: `<rect slide:role="shape"> missing required attribute "width"`,
		},
		{
			name:    "path shape requires d",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><path slide:role="shape" fill="#123456"/></svg>`,
			wantErr: `<path slide:role="shape"> missing required attribute "d"`,
		},
		{
			name:    "rect rejects percent geometry",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="shape" x="0" y="0" width="50%" height="60"/></svg>`,
			wantErr: `attribute "width" must be a number or px length`,
		},
		{
			name:    "rect rejects calc geometry",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="shape" x="calc(10px)" y="0" width="100" height="60"/></svg>`,
			wantErr: `attribute "x" must be a number or px length`,
		},
		{
			name:    "container transform rejects percent argument",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><g transform="translate(10% 20)"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></g></svg>`,
			wantErr: `transform translate() argument must be a number or px length`,
		},
		{
			name:    "path rejects arc command",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><path slide:role="shape" d="M0 0 A10 10 0 0 1 20 20" fill="#123456"/></svg>`,
			wantErr: `unsupported path command or character "A"`,
		},
		{
			name:    "path rejects smooth command",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><path slide:role="shape" d="M0 0 S10 10 20 20" fill="#123456"/></svg>`,
			wantErr: `unsupported path command or character "S"`,
		},
		{
			name:    "plain metadata remains rejected",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><metadata><desc>not transport metadata</desc></metadata></svg>`,
			wantErr: `<metadata> must include slide:role="shape" or slide:role="image"`,
		},
		{
			name:    "whiteboard role is explicitly rejected",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><g slide:role="whiteboard" x="0" y="0" width="100" height="60"/></svg>`,
			wantErr: `slide:role="whiteboard" is not supported`,
		},
		{
			name:    "legacy whiteboard marker metadata is explicitly rejected",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><metadata data-svglide-whiteboard="svglide-whiteboard-inline/v1">abc</metadata></svg>`,
			wantErr: `legacy SVGlide whiteboard marker metadata is not supported`,
		},
		{
			name:    "foreignObject shape requires text type",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><foreignObject slide:role="shape"><p xmlns="http://www.w3.org/1999/xhtml">hello</p></foreignObject></svg>`,
			wantErr: `<foreignObject slide:role="shape"> must include slide:shape-type="text"`,
		},
		{
			name:    "image role must be image tag",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="image" href="boxcn_img"/></svg>`,
			wantErr: `<rect slide:role="image"> is not supported`,
		},
		{
			name:    "image requires href",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><image slide:role="image" x="0" y="0" width="100" height="60"/></svg>`,
			wantErr: `<image slide:role="image"> must include href`,
		},
		{
			name:    "image requires geometry",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><image slide:role="image" href="boxcn_img" x="0" y="0" height="60"/></svg>`,
			wantErr: `<image slide:role="image"> missing required attribute "width"`,
		},
		{
			name:    "image rejects external href",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><image slide:role="image" href="https://images.unsplash.com/photo.jpg" x="0" y="0" width="100" height="60"/></svg>`,
			wantErr: `<image slide:role="image"> must not use external http(s) or data href`,
		},
		{
			name:    "unsupported role",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="decor"/></svg>`,
			wantErr: `unsupported slide:role="decor"`,
		},
		{
			name:    "nested chart marker is rejected",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><g>` + testSVGlideChartMarker(testSVGlideChartMetadata(`<chart />`)) + `</g></svg>`,
			wantErr: `<g slide:role="chart"> must be a direct child of root <svg>`,
		},
		{
			name:    "chart marker requires ref",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><g slide:role="chart" x="0" y="0" width="100" height="60">` + testSVGlideChartMetadata(`<chart />`) + `</g></svg>`,
			wantErr: `missing required attribute "slide:chart-ref"`,
		},
		{
			name:    "chart marker rejects bad bbox",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><g slide:role="chart" slide:chart-ref="chart-1" x="10%" y="0" width="100" height="60">` + testSVGlideChartMetadata(`<chart />`) + `</g></svg>`,
			wantErr: `attribute "x" must be a number or px length`,
		},
		{
			name:    "chart marker requires single metadata",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">` + testSVGlideChartMarker(testSVGlideChartMetadata(`<chart />`)+testSVGlideChartMetadata(`<chart />`)) + `</svg>`,
			wantErr: `must contain exactly one metadata child`,
		},
		{
			name:    "chart marker rejects duplicate chart refs",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">` + testSVGlideChartMarker(testSVGlideChartMetadata(`<chart />`)) + testSVGlideChartMarker(testSVGlideChartMetadata(`<chart><chartData /></chart>`)) + `</svg>`,
			wantErr: `duplicate slide:chart-ref "chart-1"`,
		},
		{
			name:    "chart marker rejects bad base64url",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">` + testSVGlideChartMarker(`<metadata data-svglide-chart="svglide-chart-inline/v1" data-format="sxsd-chart-v1" data-encoding="base64url" data-payload-hash="sha256:`+strings.Repeat("0", 64)+`">bad+payload</metadata>`) + `</svg>`,
			wantErr: `payload must be base64url`,
		},
		{
			name:    "chart marker rejects hash mismatch",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">` + testSVGlideChartMarker(testSVGlideChartMetadataWithHash(`<chart />`, "sha256:"+strings.Repeat("0", 64))) + `</svg>`,
			wantErr: `data-payload-hash does not match`,
		},
		{
			name:    "chart marker decoded payload must be chart root",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">` + testSVGlideChartMarker(testSVGlideChartMetadata(`<table />`)) + `</svg>`,
			wantErr: `decoded payload must be a single <chart> root`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			err := validateSVGlideSVG(withTestSVGlideContractVersion(tt.svg), "page.svg")
			if tt.wantErr == "" {
				if err != nil {
					t.Fatalf("unexpected error: %v", err)
				}
				return
			}
			if err == nil {
				t.Fatalf("expected error containing %q", tt.wantErr)
			}
			if !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("error = %q, want to contain %q", err.Error(), tt.wantErr)
			}
		})
	}
}

func testSVGlideChartMarker(metadata string) string {
	return `<g slide:role="chart" slide:chart-ref="chart-1" x="80" y="96" width="420" height="260">` + metadata + `</g>`
}

func testSVGlideChartMetadata(chartXML string) string {
	sum := sha256.Sum256([]byte(chartXML))
	return testSVGlideChartMetadataWithHash(chartXML, fmt.Sprintf("sha256:%x", sum))
}

func testSVGlideChartMetadataWithHash(chartXML, hash string) string {
	payload := base64.RawURLEncoding.EncodeToString([]byte(chartXML))
	return fmt.Sprintf(
		`<metadata data-svglide-chart="svglide-chart-inline/v1" data-format="sxsd-chart-v1" data-encoding="base64url" data-payload-hash="%s">%s</metadata>`,
		hash,
		payload,
	)
}

func withTestSVGlideContractVersion(svg string) string {
	if strings.Contains(svg, `slide:contract-version=`) {
		return svg
	}
	return strings.Replace(svg, `slide:role="slide"`, `slide:role="slide" slide:contract-version="svglide-authoring-contract/v1"`, 1)
}

func TestExtractSVGlideErrorJSON(t *testing.T) {
	t.Parallel()

	err := errors.New(`api error: SVGLIDE_ERROR_JSON:{"type":"svg_validation_error","page_index":0,"tag_name":"foreignObject","hint":"Use supported elements"}`)
	got := extractSVGlideErrorJSON(err)
	if got["type"] != "svg_validation_error" {
		t.Fatalf("type = %v", got["type"])
	}
	if got["tag_name"] != "foreignObject" {
		t.Fatalf("tag_name = %v", got["tag_name"])
	}
	suffix := formatSVGlideErrorSuffix(err)
	for _, want := range []string{"svglide_error=", "svg_validation_error", "foreignObject"} {
		if !strings.Contains(suffix, want) {
			t.Fatalf("suffix = %q, want %q", suffix, want)
		}
	}
}
