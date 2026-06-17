// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"bytes"
	"context"
	"encoding/json"
	"image"
	"image/color"
	"image/png"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/spf13/cobra"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/shortcuts/common"
)

func TestSlidesCreateSVGFlagsExposeRasterOptions(t *testing.T) {
	byName := map[string]common.Flag{}
	for _, fl := range SlidesCreateSVG.Flags {
		byName[fl.Name] = fl
	}
	if got := byName["svg-rasterize-effects"]; got.Default != "off" || strings.Join(got.Enum, ",") != "off,auto,strict,force-page" {
		t.Fatalf("svg-rasterize-effects flag = %+v", got)
	}
	if got := byName["svg-rasterize-scale"]; got.Type != "int" || got.Default != "2" {
		t.Fatalf("svg-rasterize-scale flag = %+v", got)
	}
	if _, ok := byName["svg-rasterize-report"]; !ok {
		t.Fatal("missing svg-rasterize-report flag")
	}
}

func TestPrepareSVGFilesForCreateOffKeepsNativeReadPath(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}
	runtime := newSVGRasterTestRuntime(t, nil)
	got, report, err := prepareSVGFilesForCreate(runtime, []string{"page.svg"}, svgPrepareOptions{RasterizeMode: svgRasterizeOff})
	if err != nil {
		t.Fatalf("prepare off: %v", err)
	}
	if report != nil {
		t.Fatalf("report = %+v, want nil in off mode", report)
	}
	if len(got) != 1 || !strings.Contains(got[0], `slide:contract-version="svglide-authoring-contract/v1"`) {
		t.Fatalf("prepared SVG = %#v", got)
	}
}

func TestPrepareSVGFilesForCreateForcePageRunsScriptAndGatesSafeSVG(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 960 540"><defs><filter id="glow"/></defs><rect filter="url(#glow)" x="0" y="0" width="100" height="60"/></svg>`), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}

	restore := stubSVGRasterizer(t)
	defer restore()
	runtime := newSVGRasterTestRuntime(t, embeddedSVGRasterizerTestFS())
	got, report, err := prepareSVGFilesForCreate(runtime, []string{"page.svg"}, svgPrepareOptions{
		RasterizeMode:  svgRasterizeForcePage,
		RasterizeScale: 2,
	})
	if err != nil {
		t.Fatalf("prepare force-page: %v", err)
	}
	if len(got) != 1 || strings.Contains(got[0], "<filter") || !strings.Contains(got[0], `href="@./.lark-slides/rasterized/`) {
		t.Fatalf("safe SVG did not pass through rasterizer: %s", got[0])
	}
	if report == nil || report.Mode != "force-page" || len(report.Pages) != 1 || !report.Pages[0].RuntimeGateOK {
		t.Fatalf("report = %+v", report)
	}
	if len(report.GeneratedAssets) != 1 {
		t.Fatalf("GeneratedAssets = %v, want one PNG", report.GeneratedAssets)
	}
	if gotPaths := extractSVGImagePlaceholderPaths(got, nil); len(gotPaths) != 1 || gotPaths[0] != report.GeneratedAssets[0] {
		t.Fatalf("placeholder paths = %v, generated = %v", gotPaths, report.GeneratedAssets)
	}
}

func TestSlidesCreateSVGForcePageDryRunIncludesRasterReport(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	if err := os.WriteFile("page.svg", []byte(testSVGlidePage1), 0o644); err != nil {
		t.Fatalf("write page.svg: %v", err)
	}
	restore := stubSVGRasterizer(t)
	defer restore()

	f, stdout, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	f.SkillContent = embeddedSVGRasterizerTestFS()
	err := runSlidesCreateSVGShortcut(t, f, stdout, []string{
		"+create-svg",
		"--file", "page.svg",
		"--title", "raster dry",
		"--svg-rasterize-effects", "force-page",
		"--as", "user",
		"--dry-run",
	})
	if err != nil {
		t.Fatalf("dry-run force-page: %v", err)
	}
	out := stdout.String()
	for _, want := range []string{"svg_rasterize_report", ".lark-slides/rasterized/", "uploaded_file_token:"} {
		if !strings.Contains(out, want) {
			t.Fatalf("dry-run output missing %q: %s", want, out)
		}
	}
}

func TestValidateSVGRasterizeFlagsRejectsLowScale(t *testing.T) {
	runtime := newSVGRasterTestRuntime(t, nil)
	runtime.Cmd.Flags().Set("svg-rasterize-effects", "force-page")
	runtime.Cmd.Flags().Set("svg-rasterize-scale", "1")
	err := validateSVGRasterizeFlags(runtime)
	if err == nil || !strings.Contains(err.Error(), "svg-rasterize-scale") {
		t.Fatalf("err = %v, want scale validation", err)
	}
}

func TestValidateSafeSVGNoResidualRichEffectsRejectsHardTags(t *testing.T) {
	err := validateSafeSVGNoResidualRichEffects(`<svg><defs><filter id="f"/></defs><rect filter="url(#f)"/></svg>`, "safe.svg")
	if err == nil || !strings.Contains(err.Error(), "safe SVG") {
		t.Fatalf("err = %v, want safe SVG hard-tag rejection", err)
	}
}

func TestResolveSVGRasterizerScriptUsesSourceThenEmbedded(t *testing.T) {
	dir := t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	sourcePath := filepath.Join("skills", "lark-slides", "scripts")
	if err := os.MkdirAll(sourcePath, 0o755); err != nil {
		t.Fatalf("mkdir source: %v", err)
	}
	if err := os.WriteFile(filepath.Join(sourcePath, "svg_rasterize_effects.py"), []byte("# source"), 0o644); err != nil {
		t.Fatalf("write source: %v", err)
	}
	runtime := newSVGRasterTestRuntime(t, nil)
	got, err := resolveSVGRasterizerScript(runtime)
	if err != nil {
		t.Fatalf("resolve source: %v", err)
	}
	if got != svgRasterizerSourcePath {
		t.Fatalf("script path = %s, want source path", got)
	}

	dir = t.TempDir()
	withSlidesTestWorkingDir(t, dir)
	runtime = newSVGRasterTestRuntime(t, embeddedSVGRasterizerTestFS())
	got, err = resolveSVGRasterizerScript(runtime)
	if err != nil {
		t.Fatalf("resolve embedded: %v", err)
	}
	data, err := os.ReadFile(got)
	if err != nil {
		t.Fatalf("read extracted script: %v", err)
	}
	if string(data) != "# embedded" {
		t.Fatalf("extracted script = %q", data)
	}
}

func embeddedSVGRasterizerTestFS() fstest.MapFS {
	return fstest.MapFS{
		"lark-slides/scripts/svg_rasterize_effects.py": &fstest.MapFile{Data: []byte("# embedded")},
		"lark-slides/scripts/svg_effect_classifier.py": &fstest.MapFile{Data: []byte("# classifier")},
		"lark-slides/scripts/svg_safe_rewrite.py":      &fstest.MapFile{Data: []byte("# rewrite")},
		"lark-slides/scripts/svg_raster_renderer.py":   &fstest.MapFile{Data: []byte("# renderer")},
	}
}

func TestValidateSVGRasterAssetConflicts(t *testing.T) {
	report := &svgPrepareReport{GeneratedAssets: []string{".lark-slides/rasterized/run/page.png"}}
	err := validateSVGRasterAssetConflicts(map[string]string{"@.lark-slides/rasterized/run/page.png": "boxcn_existing"}, report)
	if err == nil || !strings.Contains(err.Error(), "--assets conflicts") {
		t.Fatalf("err = %v, want conflict", err)
	}
}

func newSVGRasterTestRuntime(t *testing.T, skills fs.FS) *common.RuntimeContext {
	t.Helper()
	f, _, _, _ := cmdutil.TestFactory(t, slidesTestConfig(t, ""))
	f.SkillContent = skills
	cmd := &cobra.Command{Use: "test"}
	for _, fl := range SlidesCreateSVG.Flags {
		switch fl.Type {
		case "int":
			cmd.Flags().Int(fl.Name, 0, "")
			if fl.Default != "" {
				cmd.Flags().Set(fl.Name, fl.Default)
			}
		case "string_array":
			cmd.Flags().StringArray(fl.Name, nil, "")
		default:
			cmd.Flags().String(fl.Name, fl.Default, "")
		}
	}
	return &common.RuntimeContext{
		Config:  slidesTestConfig(t, ""),
		Cmd:     cmd,
		Factory: f,
	}
}

func stubSVGRasterizer(t *testing.T) func() {
	t.Helper()
	origResolve := svgRasterizeResolveRuntime
	origRun := svgRasterizeRunScript
	svgRasterizeResolveRuntime = func(context.Context) (svgRasterRuntime, error) {
		return svgRasterRuntime{PythonPath: "python3"}, nil
	}
	svgRasterizeRunScript = func(_ context.Context, invocation svgRasterizerInvocation) error {
		args := map[string]string{}
		for i := 0; i+1 < len(invocation.Args); i += 2 {
			args[invocation.Args[i]] = invocation.Args[i+1]
		}
		out := args["--output"]
		assetDir := args["--asset-dir"]
		reportPath := args["--report"]
		pngPath := "./" + filepath.ToSlash(filepath.Join(assetDir, "page-001-island-001.png"))
		if err := writeTestRasterPNG(pngPath); err != nil {
			return err
		}
		safe := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 960 540"><image slide:role="image" href="@` + pngPath + `" x="0" y="0" width="960" height="540"/></svg>`
		if err := os.WriteFile(out, []byte(safe), 0o644); err != nil {
			return err
		}
		report := svgPreparePageReport{
			Mode:           "force-page",
			FallbackReason: "force-page",
			PNGs:           []string{pngPath},
			Islands: []svgPrepareIslandReport{{
				ID:        "page-001-island-001",
				Reason:    "force-page",
				OutputPNG: pngPath,
				Scale:     2,
				Bytes:     1,
				RenderMS:  1,
			}},
		}
		data, err := json.Marshal(report)
		if err != nil {
			return err
		}
		return os.WriteFile(reportPath, data, 0o644)
	}
	return func() {
		svgRasterizeResolveRuntime = origResolve
		svgRasterizeRunScript = origRun
	}
}

func writeTestRasterPNG(path string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	img := image.NewRGBA(image.Rect(0, 0, 4, 4))
	img.Set(0, 0, color.RGBA{R: 255, A: 255})
	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		return err
	}
	return os.WriteFile(path, buf.Bytes(), 0o644)
}
