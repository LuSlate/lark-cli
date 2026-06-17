// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"image/png"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/google/uuid"

	"github.com/larksuite/cli/extension/fileio"
	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
)

const (
	svgRasterizerSkillPath        = "lark-slides/scripts/svg_rasterize_effects.py"
	svgRasterizerSourcePath       = "skills/" + svgRasterizerSkillPath
	svgRasterizedOutputRoot       = ".lark-slides/rasterized"
	maxSVGRasterPNGBytes    int64 = 20 * 1024 * 1024
)

var svgRasterizerEmbeddedSkillPaths = []string{
	"lark-slides/scripts/svg_rasterize_effects.py",
	"lark-slides/scripts/svg_effect_classifier.py",
	"lark-slides/scripts/svg_safe_rewrite.py",
	"lark-slides/scripts/svg_raster_renderer.py",
}

type svgRasterRuntime struct {
	PythonPath string
}

type svgRasterizerInvocation struct {
	PythonPath string
	ScriptPath string
	Args       []string
}

var (
	svgRasterizeResolveRuntime = resolveSVGRasterRuntime
	svgRasterizeRunScript      = runSVGRasterizerScript
)

func rasterizeRichSVGEffects(
	runtime *common.RuntimeContext,
	svgs []string,
	paths []string,
	opts svgPrepareOptions,
) ([]string, *svgPrepareReport, error) {
	if len(svgs) != len(paths) {
		return nil, nil, output.ErrValidation("internal svg rasterization error: SVG count %d does not match path count %d", len(svgs), len(paths))
	}
	if opts.RasterizeScale == 0 {
		opts.RasterizeScale = 2
	}

	scriptPath, err := resolveSVGRasterizerScript(runtime)
	if err != nil {
		return nil, nil, err
	}
	rasterRuntime, err := svgRasterizeResolveRuntime(contextFromRuntime(runtime))
	if err != nil {
		return nil, nil, err
	}

	baseDir, err := runtime.ResolveSavePath(".")
	if err != nil {
		return nil, nil, output.ErrValidation("resolve current working directory for SVG rasterization: %v", err)
	}
	runID := newSVGRasterRunID()
	runDir := filepath.ToSlash(filepath.Join(svgRasterizedOutputRoot, runID))
	if err := ensureSVGRasterOutputDir(runtime, runDir); err != nil {
		return nil, nil, err
	}

	report := &svgPrepareReport{
		Version: "1",
		Mode:    string(opts.RasterizeMode),
		RunID:   runID,
		BaseDir: baseDir,
		Quality: svgPrepareQuality{
			GatePassed: true,
		},
		Pages: make([]svgPreparePageReport, 0, len(svgs)),
	}
	prepared := make([]string, 0, len(svgs))
	for i, svg := range svgs {
		pageNo := i + 1
		inputPath := filepath.ToSlash(filepath.Join(runDir, fmt.Sprintf("page-%03d.rich.svg", pageNo)))
		outputPath := filepath.ToSlash(filepath.Join(runDir, fmt.Sprintf("page-%03d.safe.svg", pageNo)))
		pageReportPath := filepath.ToSlash(filepath.Join(runDir, fmt.Sprintf("page-%03d-raster-report.json", pageNo)))
		if _, err := runtime.FileIO().Save(inputPath, fileio.SaveOptions{ContentType: "image/svg+xml", ContentLength: int64(len(svg))}, strings.NewReader(svg)); err != nil {
			return nil, report, common.WrapSaveErrorTyped(err)
		}

		invocation := svgRasterizerInvocation{
			PythonPath: rasterRuntime.PythonPath,
			ScriptPath: scriptPath,
			Args: []string{
				"--mode", string(opts.RasterizeMode),
				"--scale", strconv.Itoa(opts.RasterizeScale),
				"--input", inputPath,
				"--output", outputPath,
				"--asset-dir", runDir,
				"--base-dir", baseDir,
				"--report", pageReportPath,
			},
		}
		start := time.Now()
		if err := svgRasterizeRunScript(contextFromRuntime(runtime), invocation); err != nil {
			return nil, report, err
		}
		renderMS := time.Since(start).Milliseconds()

		data, err := cmdutil.ReadInputFile(runtime.FileIO(), outputPath)
		if err != nil {
			return nil, report, common.WrapInputStatError(err, fmt.Sprintf("raster safe SVG %s", outputPath))
		}
		safeSVG := string(data)
		pageReport := readSVGRasterPageReport(runtime, pageReportPath)
		if pageReport.SourcePath == "" {
			pageReport.SourcePath = paths[i]
		}
		pageReport.SafePath = outputPath
		if pageReport.Mode == "" {
			pageReport.Mode = string(opts.RasterizeMode)
		}
		if opts.RasterizeMode == svgRasterizeForcePage && pageReport.FallbackReason == "" {
			pageReport.FallbackReason = "force-page"
		}
		pngs := extractSVGImagePlaceholderPaths([]string{safeSVG}, nil)
		if len(pngs) == 0 {
			pngs = pageReport.PNGs
		}
		pngs = dedupeStrings(pngs)
		pageReport.PNGs = pngs
		if len(pageReport.Islands) == 0 {
			pageReport.Islands = islandsFromRasterPNGs(pngs, opts.RasterizeScale, renderMS)
		}
		if err := validateSVGRasterPNGs(runtime, pngs); err != nil {
			return nil, report, err
		}
		for _, pngPath := range pngs {
			report.GeneratedAssets = append(report.GeneratedAssets, pngPath)
		}
		report.RasterImageCount += len(pngs)
		report.RasterTotalMS += renderMS
		if pageReport.FallbackReason != "" {
			report.FullPageFallbackCount++
		}
		for _, island := range pageReport.Islands {
			report.RasterTotalBytes += island.Bytes
		}
		report.Pages = append(report.Pages, pageReport)
		prepared = append(prepared, safeSVG)
	}
	report.GeneratedAssets = dedupeStrings(report.GeneratedAssets)
	if err := writeSVGRasterDeckReport(runtime, report, runDir, opts.ReportPath); err != nil {
		return nil, report, err
	}
	return prepared, report, nil
}

func resolveSVGRasterizerScript(runtime *common.RuntimeContext) (string, error) {
	if _, err := runtime.FileIO().Stat(svgRasterizerSourcePath); err == nil {
		return svgRasterizerSourcePath, nil
	}
	if runtime.Factory == nil || runtime.Factory.SkillContent == nil {
		return "", output.ErrValidation("svg rasterization requires bundled lark-slides raster scripts; rebuild CLI with scripts embedded")
	}
	dir, err := os.MkdirTemp("", "lark-cli-svg-rasterizer-*") //nolint:forbidigo // extracting embedded runtime script to process-local temp dir for execution.
	if err != nil {
		return "", output.ErrValidation("extract SVG rasterizer script: %v", err)
	}
	for _, skillPath := range svgRasterizerEmbeddedSkillPaths {
		data, err := fs.ReadFile(runtime.Factory.SkillContent, skillPath)
		if err != nil {
			return "", output.ErrValidation("svg rasterization requires bundled lark-slides raster script %s; rebuild CLI with scripts embedded", skillPath)
		}
		target := filepath.Join(dir, filepath.Base(skillPath))
		if err := os.WriteFile(target, data, 0o600); err != nil { //nolint:forbidigo // writes embedded scripts into the temp dir created above.
			return "", output.ErrValidation("extract SVG rasterizer script %s: %v", skillPath, err)
		}
	}
	return filepath.Join(dir, "svg_rasterize_effects.py"), nil
}

func resolveSVGRasterRuntime(ctx context.Context) (svgRasterRuntime, error) {
	pythonPath, err := exec.LookPath("python3")
	if err != nil {
		return svgRasterRuntime{}, output.ErrValidation("svg rasterization requires python3 on PATH")
	}
	cmd := exec.CommandContext(ctx, pythonPath, "-c", "import playwright") //nolint:gosec // fixed interpreter probe, no user-controlled code.
	if out, err := cmd.CombinedOutput(); err != nil {
		return svgRasterRuntime{}, output.ErrValidation("svg rasterization requires Python package 'playwright' and installed Chromium; run `python3 -m pip install playwright && python3 -m playwright install chromium` (%s)", strings.TrimSpace(string(out)))
	}
	return svgRasterRuntime{PythonPath: pythonPath}, nil
}

func runSVGRasterizerScript(ctx context.Context, invocation svgRasterizerInvocation) error {
	args := append([]string{invocation.ScriptPath}, invocation.Args...)
	cmd := exec.CommandContext(ctx, invocation.PythonPath, args...) //nolint:gosec // script path is resolved from source or embedded skill content; args are fixed CLI flags.
	out, err := cmd.CombinedOutput()
	if err != nil {
		msg := strings.TrimSpace(string(out))
		if msg == "" {
			msg = err.Error()
		}
		return output.ErrValidation("svg rasterization failed: %s", msg)
	}
	return nil
}

func ensureSVGRasterOutputDir(runtime *common.RuntimeContext, runDir string) error {
	keep := filepath.ToSlash(filepath.Join(runDir, ".keep"))
	if _, err := runtime.FileIO().Save(keep, fileio.SaveOptions{ContentType: "text/plain", ContentLength: 0}, strings.NewReader("")); err != nil {
		return common.WrapSaveErrorTyped(err)
	}
	return nil
}

func readSVGRasterPageReport(runtime *common.RuntimeContext, path string) svgPreparePageReport {
	data, err := cmdutil.ReadInputFile(runtime.FileIO(), path)
	if err != nil || len(bytes.TrimSpace(data)) == 0 {
		return svgPreparePageReport{}
	}
	var page svgPreparePageReport
	if json.Unmarshal(data, &page) == nil && (page.SafePath != "" || len(page.PNGs) > 0 || len(page.Islands) > 0) {
		return page
	}
	var deck svgPrepareReport
	if json.Unmarshal(data, &deck) == nil && len(deck.Pages) > 0 {
		return deck.Pages[0]
	}
	return svgPreparePageReport{}
}

func islandsFromRasterPNGs(pngs []string, scale int, renderMS int64) []svgPrepareIslandReport {
	islands := make([]svgPrepareIslandReport, 0, len(pngs))
	for i, pngPath := range pngs {
		islands = append(islands, svgPrepareIslandReport{
			ID:        fmt.Sprintf("page-island-%03d", i+1),
			Reason:    "script-generated",
			OutputPNG: pngPath,
			Scale:     scale,
			RenderMS:  renderMS,
		})
	}
	return islands
}

func validateSVGRasterPNGs(runtime *common.RuntimeContext, paths []string) error {
	for _, path := range paths {
		if err := validateSVGRasterPNGPath(path); err != nil {
			return err
		}
		stat, err := runtime.FileIO().Stat(path)
		if err != nil {
			return common.WrapInputStatError(err, fmt.Sprintf("raster PNG %s", path))
		}
		if stat.Size() <= 0 {
			return output.ErrValidation("raster PNG %s is empty", path)
		}
		if stat.Size() > maxSVGRasterPNGBytes {
			return output.ErrValidation("raster PNG %s size %s exceeds %s limit", path, common.FormatSize(stat.Size()), common.FormatSize(maxSVGRasterPNGBytes))
		}
		if err := validateSVGRasterPNGContent(runtime, path); err != nil {
			return err
		}
	}
	return nil
}

func validateSVGRasterPNGPath(path string) error {
	clean := filepath.ToSlash(filepath.Clean(path))
	if strings.HasPrefix(path, "/private/tmp/") {
		return nil
	}
	if filepath.IsAbs(path) {
		return output.ErrValidation("raster PNG %s must use a cwd-relative @./ path for upload", path)
	}
	if !strings.HasPrefix(clean, ".lark-slides/rasterized/") {
		return output.ErrValidation("raster PNG %s must be generated under .lark-slides/rasterized", path)
	}
	if strings.Contains(clean, "../") || clean == ".." {
		return output.ErrValidation("raster PNG %s cannot escape the raster output directory", path)
	}
	return nil
}

func validateSVGRasterPNGContent(runtime *common.RuntimeContext, path string) error {
	f, err := runtime.FileIO().Open(path)
	if err != nil {
		return common.WrapInputStatError(err, fmt.Sprintf("raster PNG %s", path))
	}
	defer f.Close()
	img, err := png.Decode(f)
	if err != nil {
		if err == io.ErrUnexpectedEOF {
			return output.ErrValidation("raster PNG %s is truncated", path)
		}
		return output.ErrValidation("raster PNG %s is not a valid PNG: %v", path, err)
	}
	bounds := img.Bounds()
	if bounds.Dx() <= 0 || bounds.Dy() <= 0 {
		return output.ErrValidation("raster PNG %s has invalid dimensions %dx%d", path, bounds.Dx(), bounds.Dy())
	}
	allTransparent := true
	for y := bounds.Min.Y; y < bounds.Max.Y && allTransparent; y++ {
		for x := bounds.Min.X; x < bounds.Max.X; x++ {
			_, _, _, a := img.At(x, y).RGBA()
			if a != 0 {
				allTransparent = false
				break
			}
		}
	}
	if allTransparent {
		return output.ErrValidation("raster PNG %s is fully transparent", path)
	}
	return nil
}

func writeSVGRasterDeckReport(runtime *common.RuntimeContext, report *svgPrepareReport, runDir, requestedPath string) error {
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return output.ErrValidation("marshal SVG raster report: %v", err)
	}
	defaultPath := filepath.ToSlash(filepath.Join(runDir, "raster-report.json"))
	if _, err := runtime.FileIO().Save(defaultPath, fileio.SaveOptions{ContentType: "application/json", ContentLength: int64(len(data))}, bytes.NewReader(data)); err != nil {
		return common.WrapSaveErrorTyped(err)
	}
	if strings.TrimSpace(requestedPath) == "" || filepath.Clean(requestedPath) == filepath.Clean(defaultPath) {
		return nil
	}
	if _, err := runtime.FileIO().Save(requestedPath, fileio.SaveOptions{ContentType: "application/json", ContentLength: int64(len(data))}, bytes.NewReader(data)); err != nil {
		return common.WrapSaveErrorTyped(err)
	}
	return nil
}

func newSVGRasterRunID() string {
	id := strings.ReplaceAll(uuid.NewString(), "-", "")
	return time.Now().UTC().Format("20060102-150405") + "-" + id[:8]
}

func contextFromRuntime(runtime *common.RuntimeContext) context.Context {
	if runtime == nil || runtime.Ctx() == nil {
		return context.Background()
	}
	return runtime.Ctx()
}
