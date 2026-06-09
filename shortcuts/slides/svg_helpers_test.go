// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
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

func TestClassifySVGlideSVGPageRoutes(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		svg      string
		wantMode svgClassifyMode
		wantCode string
	}{
		{
			name:     "native supported shape",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></svg>`,
			wantMode: svgClassifyNative,
		},
		{
			name:     "native supported server line role",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><line slide:role="line" x1="0" y1="0" x2="100" y2="60" stroke="#112233"/></svg>`,
			wantMode: svgClassifyNative,
		},
		{
			name:     "native supported server text role",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><foreignObject slide:role="text" x="0" y="0" width="300" height="80"><p xmlns="http://www.w3.org/1999/xhtml">SVGlide</p></foreignObject></svg>`,
			wantMode: svgClassifyNative,
		},
		{
			name:     "marked svg text still falls back",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><text slide:role="text" x="20" y="40">render me</text></svg>`,
			wantMode: svgClassifyFallback,
			wantCode: svgDiagNativeUnsupported,
		},
		{
			name:     "wrong contract native rejects",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" slide:contract-version="svglide-authoring-contract/v0" viewBox="0 0 1280 720"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></svg>`,
			wantMode: svgClassifyReject,
			wantCode: svgDiagContractVersion,
		},
		{
			name:     "wrong contract server text role rejects",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" slide:contract-version="svglide-authoring-contract/v0" viewBox="0 0 1280 720"><foreignObject slide:role="text" x="0" y="0" width="300" height="80"><p xmlns="http://www.w3.org/1999/xhtml">SVGlide</p></foreignObject></svg>`,
			wantMode: svgClassifyReject,
			wantCode: svgDiagContractVersion,
		},
		{
			name:     "unsupported but renderable text falls back",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><text x="20" y="40">render me</text></svg>`,
			wantMode: svgClassifyFallback,
			wantCode: svgDiagNativeUnsupported,
		},
		{
			name:     "wrong contract fallback-only svg still falls back",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" slide:contract-version="svglide-authoring-contract/v0" viewBox="0 0 1280 720"><text x="20" y="40">render me</text></svg>`,
			wantMode: svgClassifyFallback,
			wantCode: svgDiagNativeUnsupported,
		},
		{
			name:     "table defaults to fallback",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><foreignObject x="20" y="40" width="400" height="240"><table xmlns="http://www.w3.org/1999/xhtml"><tr><td>a</td></tr></table></foreignObject></svg>`,
			wantMode: svgClassifyFallback,
			wantCode: svgDiagNativeUnsupported,
		},
		{
			name:     "script rejects before create",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><script>alert(1)</script></svg>`,
			wantMode: svgClassifyReject,
			wantCode: svgDiagDisallowedScript,
		},
		{
			name:     "external href rejects before create",
			svg:      `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><image href="https://example.com/a.png" x="0" y="0" width="10" height="10"/></svg>`,
			wantMode: svgClassifyReject,
			wantCode: svgDiagExternalReference,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got := classifySVGlideSVGPage(tt.svg, "page.svg", 0)
			if got.Mode != tt.wantMode {
				t.Fatalf("mode = %s, want %s; diagnostics=%v", got.Mode, tt.wantMode, got.Diagnostics)
			}
			if tt.wantCode == "" {
				return
			}
			if len(got.Diagnostics) == 0 || got.Diagnostics[0].Code != tt.wantCode {
				t.Fatalf("diagnostics = %v, want first code %s", got.Diagnostics, tt.wantCode)
			}
		})
	}
}

func TestBuildSVGFallbackImageOnlyPage(t *testing.T) {
	t.Parallel()

	source := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><text x="20" y="40">fallback</text></svg>`
	got, err := buildSVGFallbackImageOnlyPage(source, "boxcn_full_page")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	for _, want := range []string{
		`xmlns:slide="https://slides.bytedance.com/ns"`,
		`slide:role="slide"`,
		`slide:contract-version="svglide-authoring-contract/v1"`,
		`viewBox="0 0 1280 720"`,
		`<image slide:role="image" href="boxcn_full_page" x="0" y="0" width="1280" height="720" preserveAspectRatio="none"/>`,
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("image-only SVG missing %s: %s", want, got)
		}
	}
	if err := validateSVGlideSVG(got, "fallback.svg"); err != nil {
		t.Fatalf("image-only SVG should be native-valid: %v", err)
	}
}

func TestEnsureSVGlideContractRootAttrsInjectsMissingVersion(t *testing.T) {
	t.Parallel()

	source := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><rect slide:role="shape" x="0" y="0" width="100" height="60"/></svg>`
	got, err := ensureSVGlideContractRootAttrs(source)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(got, `slide:contract-version="svglide-authoring-contract/v1"`) {
		t.Fatalf("contract version missing: %s", got)
	}
	if strings.Contains(got, `slide:contract-version="svglide-authoring-contract/v1" slide:contract-version`) {
		t.Fatalf("contract version duplicated: %s", got)
	}
}

func TestCommandSVGRasterizerUnavailableDiagnostic(t *testing.T) {
	t.Parallel()

	r := commandSVGRasterizer{
		command: "missing-svglide-renderer",
		lookPath: func(string) (string, error) {
			return "", os.ErrNotExist
		},
	}
	err := r.CheckAvailable(context.Background())
	if err == nil {
		t.Fatal("expected renderer unavailable error")
	}
	diags := svglideDiagnosticsFromError(err)
	if len(diags) != 1 || diags[0].Code != svgDiagRendererUnavailable {
		t.Fatalf("diagnostics = %v, want renderer_unavailable", diags)
	}
}

func TestCommandSVGRasterizerArgvAndOutputSize(t *testing.T) {
	dir := t.TempDir()
	script := filepath.Join(dir, "fake-resvg")
	argvFile := filepath.Join(dir, "argv.txt")
	if err := os.WriteFile(script, []byte("#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$ARGV_FILE\"\nprintf png > \"$2\"\n"), 0o755); err != nil {
		t.Fatalf("write fake renderer: %v", err)
	}
	in := filepath.Join(dir, "page.svg")
	if err := os.WriteFile(in, []byte(`<svg/>`), 0o644); err != nil {
		t.Fatalf("write svg: %v", err)
	}
	r := commandSVGRasterizer{
		command:       script,
		timeout:       time.Second,
		maxOutputSize: 20,
		env:           []string{"ARGV_FILE=" + argvFile},
	}

	out, size, err := r.Rasterize(context.Background(), in)
	if err != nil {
		t.Fatalf("unexpected rasterize error: %v", err)
	}
	if size != int64(len("png")) {
		t.Fatalf("size = %d, want %d", size, len("png"))
	}
	if _, err := os.Stat(out); err != nil {
		t.Fatalf("output file missing: %v", err)
	}
	argv, err := os.ReadFile(argvFile)
	if err != nil {
		t.Fatalf("read argv: %v", err)
	}
	lines := strings.Split(strings.TrimSpace(string(argv)), "\n")
	if len(lines) != 2 || lines[0] != in || lines[1] != out {
		t.Fatalf("argv = %q, want input and output path", string(argv))
	}

	r.maxOutputSize = 2
	_, _, err = r.Rasterize(context.Background(), in)
	if err == nil {
		t.Fatal("expected output-size validation error")
	}
	diags := svglideDiagnosticsFromError(err)
	if len(diags) == 0 || diags[0].Code != svgDiagRasterOutputTooLarge {
		t.Fatalf("diagnostics = %v, want raster_output_too_large", diags)
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
			name: "supported server text foreignObject",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><foreignObject slide:role="text" x="0" y="0" width="200" height="80"><p xmlns="http://www.w3.org/1999/xhtml">hello</p></foreignObject></svg>`,
		},
		{
			name: "supported server line role",
			svg:  `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><line slide:role="line" x1="0" y1="0" x2="100" y2="60"/></svg>`,
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
			wantErr: `<rect> must include slide:role="shape", "image", "line", or "text"`,
		},
		{
			name:    "group child missing role is rejected",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><g><rect x="0" y="0" width="100" height="60"/></g></svg>`,
			wantErr: `<rect> must include slide:role="shape", "image", "line", or "text"`,
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
			wantErr: `<metadata> must include slide:role="shape", "image", "line", or "text"`,
		},
		{
			name:    "foreignObject shape requires text type",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><foreignObject slide:role="shape"><p xmlns="http://www.w3.org/1999/xhtml">hello</p></foreignObject></svg>`,
			wantErr: `<foreignObject slide:role="shape"> must include slide:shape-type="text"`,
		},
		{
			name:    "line role must be line tag",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="line" x="0" y="0" width="100" height="60"/></svg>`,
			wantErr: `<rect slide:role="line"> is not supported`,
		},
		{
			name:    "text role must be foreignObject tag",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><rect slide:role="text" x="0" y="0" width="100" height="60"/></svg>`,
			wantErr: `<rect slide:role="text"> is not supported`,
		},
		{
			name:    "svg text role is not native yet",
			svg:     `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide"><text slide:role="text" x="0" y="20">later</text></svg>`,
			wantErr: `<text slide:role="text"> is not supported`,
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
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			err := validateSVGlideSVG(tt.svg, "page.svg")
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
