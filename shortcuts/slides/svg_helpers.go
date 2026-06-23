// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"bytes"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"image"
	_ "image/gif"
	_ "image/jpeg"
	_ "image/png"
	"math"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
)

const (
	maxSVGFileSizeBytes           int64 = 2 * 1024 * 1024
	svglideSlideNS                      = "https://slides.bytedance.com/ns"
	svglideContractVersion              = "svglide-authoring-contract/v1"
	svglideChartMarkerVersion           = "svglide-chart-inline/v1"
	svglideChartFormat                  = "svglide-chart-spec-v1"
	svglideChartSpecVersion             = "svglide-chart-spec/v1"
	svglideChartEncoding                = "base64url-json"
	svglideCustomFontFamilyPrefix       = "slide-font-"
	svglideAssetsVersion                = "svglide-assets/v1"
)

type svglideChartSpecPayload struct {
	Version   *string               `json:"version"`
	ChartType *string               `json:"chartType"`
	Data      *svglideChartSpecData `json:"data"`
}

type svglideChartSpecData struct {
	Categories []string                 `json:"categories"`
	Series     []svglideChartSpecSeries `json:"series"`
}

type svglideChartSpecSeries struct {
	Name   *string           `json:"name"`
	Values []json.RawMessage `json:"values"`
}

type RewrittenSVGPage struct {
	Content string
	Assets  []svgAssetMeta
}

type svgRasterizeMode string

const (
	svgRasterizeOff       svgRasterizeMode = "off"
	svgRasterizeAuto      svgRasterizeMode = "auto"
	svgRasterizeStrict    svgRasterizeMode = "strict"
	svgRasterizeForcePage svgRasterizeMode = "force-page"
)

type svgPrepareOptions struct {
	RasterizeMode  svgRasterizeMode
	RasterizeScale int
	ReportPath     string
	DryRun         bool
}

type svgPrepareReport struct {
	Version                  string                 `json:"version"`
	Mode                     string                 `json:"mode"`
	RunID                    string                 `json:"run_id"`
	BaseDir                  string                 `json:"base_dir"`
	Pages                    []svgPreparePageReport `json:"pages"`
	GeneratedAssets          []string               `json:"generated_assets"`
	VisualArtifacts          svgVisualArtifacts     `json:"visual_artifacts"`
	Quality                  svgPrepareQuality      `json:"quality"`
	NativeTextBlockCount     int                    `json:"native_text_blocks"`
	RasterizedTextBlockCount int                    `json:"rasterized_text_blocks"`
	RasterImageCount         int                    `json:"raster_images"`
	FullPageFallbackCount    int                    `json:"full_page_fallback_count"`
	RasterTotalBytes         int64                  `json:"raster_total_bytes"`
	RasterTotalMS            int64                  `json:"raster_total_ms"`
	Warnings                 []string               `json:"warnings,omitempty"`
}

type svgPreparePageReport struct {
	SourcePath     string                   `json:"source_path"`
	SafePath       string                   `json:"safe_path"`
	Mode           string                   `json:"mode"`
	FallbackReason string                   `json:"fallback_reason,omitempty"`
	Islands        []svgPrepareIslandReport `json:"islands"`
	PNGs           []string                 `json:"pngs"`
	RuntimeGateOK  bool                     `json:"runtime_gate_ok"`
}

type svgPrepareIslandReport struct {
	ID            string     `json:"id"`
	Reason        string     `json:"reason"`
	SourceNodeIDs []string   `json:"source_node_ids,omitempty"`
	BBox          [4]float64 `json:"bbox"`
	OutputPNG     string     `json:"output_png"`
	Scale         int        `json:"scale"`
	Bytes         int64      `json:"bytes"`
	RenderMS      int64      `json:"render_ms"`
	AlphaCrop     bool       `json:"alpha_crop"`
}

type svgVisualArtifacts struct {
	RichPreview      string `json:"rich_preview,omitempty"`
	SafePreview      string `json:"safe_preview,omitempty"`
	ReadbackSnapshot string `json:"readback_snapshot,omitempty"`
	ContactSheet     string `json:"contact_sheet,omitempty"`
}

type svgPrepareQuality struct {
	RichSafePixelDiff      *float64 `json:"rich_safe_pixel_diff,omitempty"`
	CriticalAreaPixelDiff  *float64 `json:"critical_area_pixel_diff,omitempty"`
	SafeReadbackVisualDiff *float64 `json:"safe_readback_visual_diff,omitempty"`
	WaiverRequired         bool     `json:"waiver_required,omitempty"`
	WaiverReason           string   `json:"waiver_reason,omitempty"`
	GatePassed             bool     `json:"gate_passed"`
}

type svgAssetMeta struct {
	Token    string `json:"token"`
	Name     string `json:"name"`
	MimeType string `json:"mimeType"`
	Size     int64  `json:"size"`
	Width    int    `json:"width"`
	Height   int    `json:"height"`
}

type svgAssetMap map[string]svgAssetMeta

var (
	svgRootOpenTagRegex        = regexp.MustCompile(`(?s)\A(\s*(?:<\?[^?]*(?:\?[^>][^?]*)*\?>\s*)?(?:<!DOCTYPE[^>]*>\s*)?(?:<!--.*?-->\s*)*)<([A-Za-z_][\w.:-]*)((?:\s[^>]*?)?)(/?>)`)
	svgImageTagRegex           = regexp.MustCompile(`(?is)<image\b[^>]*>`)
	svgImageHrefRegex          = regexp.MustCompile(`(?is)(^|\s)(xlink:href|href)\s*=\s*(["'])([^"']*)(["'])`)
	svgMetadataRegex           = regexp.MustCompile(`(?is)<metadata\b[^>]*\bdata-svglide-assets\s*=\s*(["'])(?:true|svglide-assets/v1)(["'])[^>]*>.*?</metadata>`)
	svgMetadataEndRegex        = regexp.MustCompile(`(?is)</metadata\s*>`)
	svgMetadataImgRegex        = regexp.MustCompile(`(?is)<img\b[^>]*\bsrc\s*=\s*(["'])([^"']+)(["'])`)
	svgMetadataImgTagRegex     = regexp.MustCompile(`(?is)<img\b[^>]*>`)
	svgAssetsMetadataAttrRegex = regexp.MustCompile(`(?is)\bdata-svglide-assets\s*=\s*(["'])(?:true|svglide-assets/v1)(["'])`)
	svgStyleAttrRegex          = regexp.MustCompile(`(?is)(^|\s)style\s*=\s*(["'])([^"']*)(["'])`)
	svgFontAttrRegex           = regexp.MustCompile(`(?is)(^|\s)font-family\s*=\s*(["'])([^"']*)(["'])`)
	svgNumberRegex             = regexp.MustCompile(`^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?(?:px)?$`)
	svgPathNumberRegex         = regexp.MustCompile(`[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?`)
	svgTransformRegex          = regexp.MustCompile(`(?is)([a-zA-Z]+)\(([^)]*)\)`)
	svgBase64URLRegex          = regexp.MustCompile(`^[A-Za-z0-9_-]+$`)
	svgSHA256HashRegex         = regexp.MustCompile(`^sha256:[0-9a-fA-F]{64}$`)
	svgRasterUnsafeChecks      = []struct {
		re   *regexp.Regexp
		desc string
	}{
		{regexp.MustCompile(`(?is)<!DOCTYPE\b`), "DOCTYPE declarations are not allowed before rasterization"},
		{regexp.MustCompile(`(?is)<\s*script\b`), "<script> is not allowed before rasterization"},
		{regexp.MustCompile(`(?is)<\s*(iframe|object|embed)\b`), "<iframe>, <object>, and <embed> are not allowed before rasterization"},
		{regexp.MustCompile(`(?is)\son[a-z]+\s*=`), "event handler attributes are not allowed before rasterization"},
		{regexp.MustCompile(`(?is)\b(?:href|xlink:href|src)\s*=\s*["']\s*javascript:`), "javascript: URLs are not allowed before rasterization"},
		{regexp.MustCompile(`(?is)<\s*link\b[^>]+\brel\s*=\s*["']stylesheet["'][^>]*\bhref\s*=\s*["']\s*https?://`), "external CSS is not allowed before rasterization"},
		{regexp.MustCompile(`(?is)<\s*script\b[^>]+\bsrc\s*=\s*["']\s*https?://`), "external JavaScript is not allowed before rasterization"},
	}
	svgSafeHardChecks = []struct {
		re   *regexp.Regexp
		desc string
	}{
		{regexp.MustCompile(`(?is)<\s*(filter|mask|clipPath|pattern|symbol|use|marker|animate|animateTransform|animateMotion)\b`), "safe SVG still contains unsupported rich SVG elements"},
		{regexp.MustCompile(`(?is)\s(?:filter|mask|clip-path)\s*=`), "safe SVG still contains unsupported filter/mask/clip-path attributes"},
		{regexp.MustCompile(`(?is)\sstyle\s*=\s*["'][^"']*(filter|backdrop-filter|mix-blend-mode|clip-path|mask|box-shadow)\s*:`), "safe SVG still contains unsupported rich CSS effects"},
		{regexp.MustCompile(`(?is)<\s*(text|polygon|polyline)\b`), "safe SVG still contains root-level text/polygon/polyline that must be rasterized or rewritten"},
		{regexp.MustCompile(`(?is)<\s*script\b`), "safe SVG still contains <script>"},
		{regexp.MustCompile(`(?is)\son[a-z]+\s*=`), "safe SVG still contains event handler attributes"},
	}
	svgShapeTags = map[string]bool{
		"circle":        true,
		"ellipse":       true,
		"foreignObject": true,
		"line":          true,
		"path":          true,
		"rect":          true,
	}
	svgRequiredAttrsByTag = map[string][]string{
		"circle":        {"cx", "cy", "r"},
		"ellipse":       {"cx", "cy", "rx", "ry"},
		"foreignObject": {"x", "y", "width", "height"},
		"image":         {"x", "y", "width", "height"},
		"line":          {"x1", "y1", "x2", "y2"},
		"path":          {"d"},
		"rect":          {"x", "y", "width", "height"},
	}
	svgGeometryAttrsByTag = map[string][]string{
		"circle":        {"cx", "cy", "r"},
		"ellipse":       {"cx", "cy", "rx", "ry"},
		"foreignObject": {"x", "y", "width", "height"},
		"image":         {"x", "y", "width", "height"},
		"line":          {"x1", "y1", "x2", "y2"},
		"rect":          {"x", "y", "width", "height"},
	}
	svgContainerTags = map[string]bool{
		"g":   true,
		"svg": true,
	}
	svgIgnoredSubtreeTags = map[string]bool{
		"defs":  true,
		"style": true,
	}
)

type svgValidationMode int

const (
	svgValidationDescend svgValidationMode = iota
	svgValidationSkipSubtree
	svgValidationStop
)

func validateSVGFileInputs(runtime *common.RuntimeContext, paths []string) error {
	if len(paths) == 0 {
		return common.FlagErrorf("--file is required")
	}
	for _, path := range paths {
		if strings.TrimSpace(path) == "" {
			return common.FlagErrorf("--file cannot be empty")
		}
		stat, err := runtime.FileIO().Stat(path)
		if err != nil {
			return common.WrapInputStatError(err, fmt.Sprintf("--file %s: file not found", path))
		}
		if !stat.Mode().IsRegular() {
			return output.ErrValidation("--file %s: must be a regular file", path)
		}
		if stat.Size() == 0 {
			return output.ErrValidation("--file %s: SVG file is empty", path)
		}
		if stat.Size() > maxSVGFileSizeBytes {
			return output.ErrValidation("--file %s: SVG file size %s exceeds %s limit",
				path, common.FormatSize(stat.Size()), common.FormatSize(maxSVGFileSizeBytes))
		}
	}
	return nil
}

func readSVGFiles(runtime *common.RuntimeContext, paths []string) ([]string, error) {
	svgs := make([]string, 0, len(paths))
	for _, path := range paths {
		data, err := cmdutil.ReadInputFile(runtime.FileIO(), path)
		if err != nil {
			return nil, common.WrapInputStatError(err, fmt.Sprintf("--file %s", path))
		}
		if strings.TrimSpace(string(data)) == "" {
			return nil, output.ErrValidation("--file %s: SVG file is empty", path)
		}
		svg := string(data)
		var normalizeErr error
		svg, normalizeErr = ensureSVGlideRootContractVersion(svg, path)
		if normalizeErr != nil {
			return nil, normalizeErr
		}
		if err := validateSVGlideSVG(svg, path); err != nil {
			return nil, err
		}
		svgs = append(svgs, svg)
	}
	return svgs, nil
}

func prepareSVGFilesForCreate(runtime *common.RuntimeContext, paths []string, opts svgPrepareOptions) ([]string, *svgPrepareReport, error) {
	if opts.RasterizeMode == svgRasterizeOff {
		svgs, err := readSVGFiles(runtime, paths)
		return svgs, nil, err
	}

	rawSVGS, err := readRawSVGFilesForRaster(runtime, paths)
	if err != nil {
		return nil, nil, err
	}

	prepared, report, err := rasterizeRichSVGEffects(runtime, rawSVGS, paths, opts)
	if err != nil {
		return nil, report, err
	}
	if report == nil {
		report = &svgPrepareReport{
			Version: "1",
			Mode:    string(opts.RasterizeMode),
			Quality: svgPrepareQuality{GatePassed: true},
		}
	}
	for i, svg := range prepared {
		normalized, err := ensureSVGlideRootContractVersion(svg, paths[i])
		if err != nil {
			return nil, report, err
		}
		if err := validateSafeSVGNoResidualRichEffects(normalized, paths[i]); err != nil {
			return nil, report, err
		}
		if err := validateSVGlideSVG(normalized, paths[i]); err != nil {
			return nil, report, err
		}
		prepared[i] = normalized
		if i < len(report.Pages) {
			report.Pages[i].RuntimeGateOK = true
		}
	}
	return prepared, report, nil
}

func svgPrepareOptionsFromRuntime(runtime *common.RuntimeContext, dryRun bool) svgPrepareOptions {
	mode := svgRasterizeMode(strings.TrimSpace(runtime.Str("svg-rasterize-effects")))
	if mode == "" {
		mode = svgRasterizeOff
	}
	return svgPrepareOptions{
		RasterizeMode:  mode,
		RasterizeScale: runtime.Int("svg-rasterize-scale"),
		ReportPath:     strings.TrimSpace(runtime.Str("svg-rasterize-report")),
		DryRun:         dryRun,
	}
}

func validateSVGRasterizeFlags(runtime *common.RuntimeContext) error {
	mode := svgRasterizeMode(strings.TrimSpace(runtime.Str("svg-rasterize-effects")))
	if mode == "" {
		mode = svgRasterizeOff
	}
	switch mode {
	case svgRasterizeOff, svgRasterizeAuto, svgRasterizeStrict, svgRasterizeForcePage:
	default:
		return common.FlagErrorf("--svg-rasterize-effects must be one of off, auto, strict, force-page")
	}
	if mode != svgRasterizeOff {
		scale := runtime.Int("svg-rasterize-scale")
		if scale < 2 || scale > 4 {
			return output.ErrValidation("--svg-rasterize-scale must be between 2 and 4 when --svg-rasterize-effects is not off")
		}
	}
	reportPath := strings.TrimSpace(runtime.Str("svg-rasterize-report"))
	if reportPath != "" {
		if _, err := runtime.ResolveSavePath(reportPath); err != nil {
			return output.ErrValidation("--svg-rasterize-report %s: %v", reportPath, err)
		}
	}
	return nil
}

func readRawSVGFilesForRaster(runtime *common.RuntimeContext, paths []string) ([]string, error) {
	svgs := make([]string, 0, len(paths))
	for _, path := range paths {
		data, err := cmdutil.ReadInputFile(runtime.FileIO(), path)
		if err != nil {
			return nil, common.WrapInputStatError(err, fmt.Sprintf("--file %s", path))
		}
		if strings.TrimSpace(string(data)) == "" {
			return nil, output.ErrValidation("--file %s: SVG file is empty", path)
		}
		svg := string(data)
		if err := validateSVGRasterInputSafeToRender(svg, path); err != nil {
			return nil, err
		}
		svgs = append(svgs, svg)
	}
	return svgs, nil
}

func validateSVGRasterInputSafeToRender(svg, path string) error {
	for _, check := range svgRasterUnsafeChecks {
		if check.re.MatchString(svg) {
			return output.ErrValidation("--file %s: unsafe SVG raster input: %s", path, check.desc)
		}
	}
	for _, tag := range svgImageTagRegex.FindAllString(svg, -1) {
		for _, m := range svgImageHrefRegex.FindAllStringSubmatch(tag, -1) {
			if len(m) < 6 || m[3] != m[5] {
				continue
			}
			value := strings.TrimSpace(m[4])
			lower := strings.ToLower(value)
			if strings.HasPrefix(lower, "http://") || strings.HasPrefix(lower, "https://") {
				return output.ErrValidation("--file %s: unsafe SVG raster input: external image resources must be resolved locally before rasterization", path)
			}
			if strings.HasPrefix(lower, "file://") {
				return output.ErrValidation("--file %s: unsafe SVG raster input: arbitrary file:// URLs are not allowed", path)
			}
		}
	}
	return nil
}

func validateSafeSVGNoResidualRichEffects(svg, path string) error {
	for _, check := range svgSafeHardChecks {
		if check.re.MatchString(svg) {
			return output.ErrValidation("--file %s: %s", path, check.desc)
		}
	}
	return nil
}

func normalizeSVGFontFamily(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", nil
	}
	parts := strings.Split(raw, ",")
	families := make([]string, 0, len(parts))
	for _, part := range parts {
		family := strings.TrimSpace(part)
		if family == "" {
			return "", output.ErrValidation("--font-family contains an empty family name")
		}
		if strings.HasPrefix(strings.ToLower(family), svglideCustomFontFamilyPrefix) {
			return "", output.ErrValidation("--font-family only supports existing web/system fonts; custom slide-font-* fonts are not supported")
		}
		for _, r := range family {
			if r < 0x20 || strings.ContainsRune(`"'&;:{}()[]<>\`, r) {
				return "", output.ErrValidation("--font-family contains unsupported character %q", r)
			}
		}
		families = append(families, family)
	}
	return strings.Join(families, ", "), nil
}

func applySVGlideFontFamily(svg, fontFamily string) string {
	if strings.TrimSpace(fontFamily) == "" {
		return svg
	}
	var out strings.Builder
	offset := 0
	for {
		rel := strings.Index(svg[offset:], "<foreignObject")
		if rel < 0 {
			out.WriteString(svg[offset:])
			return out.String()
		}
		start := offset + rel
		end := findSVGTagEnd(svg, start)
		if end < 0 {
			out.WriteString(svg[offset:])
			return out.String()
		}
		name, attrs, selfClosing := parseSVGStartTag(svg[start+1 : end])
		if name != "foreignObject" || !hasXMLAttr(attrs, "slide:role", "shape") || !hasXMLAttr(attrs, "slide:shape-type", "text") {
			out.WriteString(svg[offset : end+1])
			offset = end + 1
			continue
		}

		out.WriteString(svg[offset:start])
		out.WriteString(rewriteSVGStartTagFontFamily(svg[start:end+1], fontFamily, true))
		if selfClosing {
			offset = end + 1
			continue
		}

		closeStart, closeEnd := findSVGElementClose(svg, end+1, name)
		if closeStart < 0 {
			out.WriteString(svg[end+1:])
			return out.String()
		}
		out.WriteString(rewriteSVGTextFragmentFontFamily(svg[end+1:closeStart], fontFamily))
		out.WriteString(svg[closeStart : closeEnd+1])
		offset = closeEnd + 1
	}
}

func rewriteSVGTextFragmentFontFamily(fragment, fontFamily string) string {
	var out strings.Builder
	offset := 0
	for offset < len(fragment) {
		rel := strings.IndexByte(fragment[offset:], '<')
		if rel < 0 {
			out.WriteString(fragment[offset:])
			break
		}
		start := offset + rel
		out.WriteString(fragment[offset:start])
		switch {
		case strings.HasPrefix(fragment[start:], "</"),
			strings.HasPrefix(fragment[start:], "<!"),
			strings.HasPrefix(fragment[start:], "<?"):
			end := findSVGTagEnd(fragment, start)
			if end < 0 {
				out.WriteString(fragment[start:])
				return out.String()
			}
			out.WriteString(fragment[start : end+1])
			offset = end + 1
			continue
		}
		end := findSVGTagEnd(fragment, start)
		if end < 0 {
			out.WriteString(fragment[start:])
			return out.String()
		}
		out.WriteString(rewriteSVGStartTagFontFamily(fragment[start:end+1], fontFamily, false))
		offset = end + 1
	}
	return out.String()
}

func rewriteSVGStartTagFontFamily(tag, fontFamily string, forceStyle bool) string {
	if !strings.HasPrefix(tag, "<") || strings.HasPrefix(tag, "</") || len(tag) < 3 {
		return tag
	}
	name, attrs, selfClosing := parseSVGStartTag(tag[1 : len(tag)-1])
	if name == "" {
		return tag
	}

	changed := false
	var attrChanged bool
	attrs, attrChanged = setXMLAttr(attrs, "font-family", fontFamily, false)
	changed = changed || attrChanged
	attrs, attrChanged = setSVGStyleFontFamily(attrs, fontFamily, forceStyle)
	changed = changed || attrChanged
	if !changed {
		return tag
	}

	var b strings.Builder
	b.WriteByte('<')
	b.WriteString(name)
	if strings.TrimSpace(attrs) != "" {
		b.WriteByte(' ')
		b.WriteString(strings.TrimSpace(attrs))
	}
	if selfClosing {
		b.WriteString("/>")
	} else {
		b.WriteByte('>')
	}
	return b.String()
}

func setXMLAttr(attrs, name, value string, add bool) (string, bool) {
	re := regexp.MustCompile(`(?is)(^|\s)` + regexp.QuoteMeta(name) + `\s*=\s*(["'])([^"']*)(["'])`)
	loc := re.FindStringSubmatchIndex(attrs)
	if loc == nil {
		if !add {
			return attrs, false
		}
		sep := ""
		if strings.TrimSpace(attrs) != "" {
			sep = " "
		}
		return strings.TrimSpace(attrs) + sep + name + `="` + value + `"`, true
	}
	leading := attrs[loc[2]:loc[3]]
	quote := attrs[loc[4]:loc[5]]
	replacement := leading + name + "=" + quote + value + quote
	return attrs[:loc[0]] + replacement + attrs[loc[1]:], true
}

func setSVGStyleFontFamily(attrs, fontFamily string, force bool) (string, bool) {
	loc := svgStyleAttrRegex.FindStringSubmatchIndex(attrs)
	if loc == nil {
		if !force {
			return attrs, false
		}
		return setXMLAttr(attrs, "style", "font-family:"+fontFamily+";", true)
	}
	leading := attrs[loc[2]:loc[3]]
	quote := attrs[loc[4]:loc[5]]
	style := rewriteCSSFontFamily(attrs[loc[6]:loc[7]], fontFamily)
	replacement := leading + "style=" + quote + style + quote
	return attrs[:loc[0]] + replacement + attrs[loc[1]:], true
}

func rewriteCSSFontFamily(style, fontFamily string) string {
	parts := strings.Split(style, ";")
	out := make([]string, 0, len(parts)+1)
	found := false
	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed == "" {
			continue
		}
		key, _, ok := strings.Cut(trimmed, ":")
		if ok && strings.EqualFold(strings.TrimSpace(key), "font-family") {
			out = append(out, "font-family:"+fontFamily)
			found = true
			continue
		}
		out = append(out, trimmed)
	}
	if !found {
		out = append(out, "font-family:"+fontFamily)
	}
	return strings.Join(out, ";") + ";"
}

func validateSVGlideSVG(svg, path string) error {
	m := svgRootOpenTagRegex.FindStringSubmatchIndex(svg)
	if m == nil {
		return output.ErrValidation("--file %s: SVG root element not found", path)
	}
	tagName := svg[m[4]:m[5]]
	if tagName != "svg" {
		return output.ErrValidation("--file %s: root element must be non-namespaced <svg>", path)
	}
	attrs := svg[m[6]:m[7]]
	if !hasXMLAttr(attrs, "xmlns:slide", svglideSlideNS) {
		return output.ErrValidation("--file %s: root <svg> must declare xmlns:slide=\"%s\"", path, svglideSlideNS)
	}
	if !hasXMLAttr(attrs, "slide:role", "slide") {
		return output.ErrValidation("--file %s: root <svg> must include slide:role=\"slide\"", path)
	}
	if version := xmlAttrValue(attrs, "slide:contract-version"); version != svglideContractVersion {
		return output.ErrValidation("--file %s: root <svg> must include slide:contract-version=\"%s\"", path, svglideContractVersion)
	}
	if svg[m[8]:m[9]] == "/>" {
		return nil
	}
	return validateSVGlideChildren(svg[m[9]:], path)
}

func ensureSVGlideRootContractVersion(svg, path string) (string, error) {
	m := svgRootOpenTagRegex.FindStringSubmatchIndex(svg)
	if m == nil {
		return svg, nil
	}
	tagName := svg[m[4]:m[5]]
	if tagName != "svg" {
		return svg, nil
	}
	attrs := svg[m[6]:m[7]]
	version := xmlAttrValue(attrs, "slide:contract-version")
	if version == svglideContractVersion {
		return svg, nil
	}
	if strings.TrimSpace(version) != "" {
		return "", output.ErrValidation("--file %s: root <svg> must include slide:contract-version=\"%s\"", path, svglideContractVersion)
	}
	return svg[:m[8]] + fmt.Sprintf(` slide:contract-version="%s"`, svglideContractVersion) + svg[m[8]:], nil
}

func hasXMLAttr(attrs, name, want string) bool {
	return xmlAttrValue(attrs, name) == want
}

func xmlAttrValue(attrs, name string) string {
	re := regexp.MustCompile(`(?is)(?:^|\s)` + regexp.QuoteMeta(name) + `\s*=\s*(["'])([^"']*)(["'])`)
	for _, m := range re.FindAllStringSubmatch(attrs, -1) {
		if len(m) >= 4 && m[1] == m[3] {
			return m[2]
		}
	}
	return ""
}

func validateSVGlideChildren(svgAfterRootOpen, path string) error {
	depth := 0
	skipDepth := -1
	chartRefs := map[string]bool{}
	for i := 0; i < len(svgAfterRootOpen); {
		rel := strings.IndexByte(svgAfterRootOpen[i:], '<')
		if rel < 0 {
			return nil
		}
		i += rel

		switch {
		case strings.HasPrefix(svgAfterRootOpen[i:], "<!--"):
			end := strings.Index(svgAfterRootOpen[i+4:], "-->")
			if end < 0 {
				return output.ErrValidation("--file %s: malformed SVG comment", path)
			}
			i += 4 + end + 3
			continue
		case strings.HasPrefix(svgAfterRootOpen[i:], "<![CDATA["):
			end := strings.Index(svgAfterRootOpen[i+9:], "]]>")
			if end < 0 {
				return output.ErrValidation("--file %s: malformed SVG CDATA", path)
			}
			i += 9 + end + 3
			continue
		case strings.HasPrefix(svgAfterRootOpen[i:], "<?"):
			end := strings.Index(svgAfterRootOpen[i+2:], "?>")
			if end < 0 {
				return output.ErrValidation("--file %s: malformed SVG processing instruction", path)
			}
			i += 2 + end + 2
			continue
		case strings.HasPrefix(svgAfterRootOpen[i:], "</"):
			end := findSVGTagEnd(svgAfterRootOpen, i)
			if end < 0 {
				return output.ErrValidation("--file %s: malformed SVG closing tag", path)
			}
			name := parseSVGClosingTagName(svgAfterRootOpen[i+2 : end])
			if depth == 0 && name == "svg" {
				return nil
			}
			if depth > 0 {
				depth--
			}
			if skipDepth >= 0 && depth < skipDepth {
				skipDepth = -1
			}
			i = end + 1
			continue
		case strings.HasPrefix(svgAfterRootOpen[i:], "<!"):
			end := findSVGTagEnd(svgAfterRootOpen, i)
			if end < 0 {
				return output.ErrValidation("--file %s: malformed SVG declaration", path)
			}
			i = end + 1
			continue
		}

		end := findSVGTagEnd(svgAfterRootOpen, i)
		if end < 0 {
			return output.ErrValidation("--file %s: malformed SVG element", path)
		}
		name, attrs, selfClosing := parseSVGStartTag(svgAfterRootOpen[i+1 : end])
		if name == "" {
			i = end + 1
			continue
		}
		if skipDepth < 0 && name == "g" && xmlAttrValue(attrs, "slide:role") == "chart" {
			if depth != 0 {
				return output.ErrValidation("--file %s: <g slide:role=\"chart\"> must be a direct child of root <svg>", path)
			}
			if selfClosing {
				return output.ErrValidation("--file %s: <g slide:role=\"chart\"> must contain one chart metadata child", path)
			}
			closeStart, closeEnd := findSVGElementClose(svgAfterRootOpen, end+1, name)
			if closeStart < 0 {
				return output.ErrValidation("--file %s: malformed chart marker: missing </g>", path)
			}
			chartRef, err := validateSVGlideChartMarker(path, attrs, svgAfterRootOpen[end+1:closeStart])
			if err != nil {
				return err
			}
			if chartRefs[chartRef] {
				return output.ErrValidation("--file %s: duplicate slide:chart-ref %q in SVG chart markers", path, chartRef)
			}
			chartRefs[chartRef] = true
			i = closeEnd + 1
			continue
		}
		if skipDepth < 0 {
			mode, err := validateSVGlideElement(path, name, attrs)
			if err != nil {
				return err
			}
			if mode == svgValidationSkipSubtree && !selfClosing {
				skipDepth = depth + 1
			}
		}
		if !selfClosing {
			depth++
		}
		i = end + 1
	}
	return output.ErrValidation("--file %s: malformed SVG root: missing </svg>", path)
}

func findSVGTagEnd(svg string, start int) int {
	var quote byte
	for i := start + 1; i < len(svg); i++ {
		c := svg[i]
		if quote != 0 {
			if c == quote {
				quote = 0
			}
			continue
		}
		if c == '"' || c == '\'' {
			quote = c
			continue
		}
		if c == '>' {
			return i
		}
	}
	return -1
}

func findSVGElementClose(svg string, start int, tagName string) (closeStart, closeEnd int) {
	depth := 1
	for i := start; i < len(svg); {
		rel := strings.IndexByte(svg[i:], '<')
		if rel < 0 {
			return -1, -1
		}
		i += rel
		switch {
		case strings.HasPrefix(svg[i:], "<!--"):
			end := strings.Index(svg[i+4:], "-->")
			if end < 0 {
				return -1, -1
			}
			i += 4 + end + 3
			continue
		case strings.HasPrefix(svg[i:], "<![CDATA["):
			end := strings.Index(svg[i+9:], "]]>")
			if end < 0 {
				return -1, -1
			}
			i += 9 + end + 3
			continue
		case strings.HasPrefix(svg[i:], "<?"):
			end := strings.Index(svg[i+2:], "?>")
			if end < 0 {
				return -1, -1
			}
			i += 2 + end + 2
			continue
		case strings.HasPrefix(svg[i:], "</"):
			end := findSVGTagEnd(svg, i)
			if end < 0 {
				return -1, -1
			}
			if parseSVGClosingTagName(svg[i+2:end]) == tagName {
				depth--
				if depth == 0 {
					return i, end
				}
			}
			i = end + 1
			continue
		case strings.HasPrefix(svg[i:], "<!"):
			end := findSVGTagEnd(svg, i)
			if end < 0 {
				return -1, -1
			}
			i = end + 1
			continue
		}
		end := findSVGTagEnd(svg, i)
		if end < 0 {
			return -1, -1
		}
		name, _, selfClosing := parseSVGStartTag(svg[i+1 : end])
		if name == tagName && !selfClosing {
			depth++
		}
		i = end + 1
	}
	return -1, -1
}

func parseSVGClosingTagName(raw string) string {
	raw = strings.TrimSpace(raw)
	for i, r := range raw {
		if r == '>' || r == '/' || isXMLSpace(r) {
			return raw[:i]
		}
	}
	return raw
}

func parseSVGStartTag(raw string) (name, attrs string, selfClosing bool) {
	raw = strings.TrimSpace(raw)
	if raw == "" || strings.HasPrefix(raw, "/") {
		return "", "", false
	}
	if strings.HasSuffix(raw, "/") {
		selfClosing = true
		raw = strings.TrimSpace(strings.TrimSuffix(raw, "/"))
	}
	nameEnd := len(raw)
	for i, r := range raw {
		if isXMLSpace(r) || r == '/' {
			nameEnd = i
			break
		}
	}
	name = raw[:nameEnd]
	attrs = strings.TrimSpace(raw[nameEnd:])
	return name, attrs, selfClosing
}

func isXMLSpace(r rune) bool {
	return r == ' ' || r == '\t' || r == '\n' || r == '\r'
}

func isSVGlideAssetsMetadata(attrs string) bool {
	value := strings.TrimSpace(xmlAttrValue(attrs, "data-svglide-assets"))
	return value == "true" || value == svglideAssetsVersion
}

func validateSVGlideElement(path, tagName, attrs string) (svgValidationMode, error) {
	if svgIgnoredSubtreeTags[tagName] {
		return svgValidationSkipSubtree, nil
	}
	if tagName == "metadata" && strings.TrimSpace(xmlAttrValue(attrs, "data-svglide-whiteboard")) != "" {
		return svgValidationStop, output.ErrValidation("--file %s: legacy SVGlide whiteboard marker metadata is not supported by slides +create-svg", path)
	}
	if tagName == "metadata" && isSVGlideAssetsMetadata(attrs) {
		return svgValidationSkipSubtree, nil
	}
	if err := validateSVGlideTransform(path, tagName, attrs); err != nil {
		return svgValidationStop, err
	}
	role := xmlAttrValue(attrs, "slide:role")
	if role == "whiteboard" {
		return svgValidationStop, output.ErrValidation("--file %s: slide:role=\"whiteboard\" is not supported by slides +create-svg", path)
	}
	if role == "chart" {
		return svgValidationStop, output.ErrValidation("--file %s: <g slide:role=\"chart\"> must be a direct child of root <svg>", path)
	}
	if svgContainerTags[tagName] {
		return svgValidationDescend, nil
	}

	if role == "" {
		return svgValidationStop, output.ErrValidation("--file %s: <%s> must include slide:role=\"shape\" or slide:role=\"image\" for SVGlide", path, tagName)
	}

	switch role {
	case "shape":
		if !svgShapeTags[tagName] {
			return svgValidationStop, output.ErrValidation("--file %s: <%s slide:role=\"shape\"> is not supported by SVGlide; use rect, ellipse, circle, line, path, or foreignObject", path, tagName)
		}
		if tagName == "foreignObject" && !hasXMLAttr(attrs, "slide:shape-type", "text") {
			return svgValidationStop, output.ErrValidation("--file %s: <foreignObject slide:role=\"shape\"> must include slide:shape-type=\"text\"", path)
		}
		if err := validateSVGlideRequiredAttrs(path, tagName, role, attrs); err != nil {
			return svgValidationStop, err
		}
		return svgValidationSkipSubtree, nil
	case "image":
		if tagName != "image" {
			return svgValidationStop, output.ErrValidation("--file %s: <%s slide:role=\"image\"> is not supported by SVGlide; use <image>", path, tagName)
		}
		href := xmlAttrValue(attrs, "href")
		if href == "" {
			href = xmlAttrValue(attrs, "xlink:href")
		}
		if href == "" {
			return svgValidationStop, output.ErrValidation("--file %s: <image slide:role=\"image\"> must include href", path)
		}
		if isExternalSVGHref(href) {
			return svgValidationStop, output.ErrValidation("--file %s: <image slide:role=\"image\"> must not use external http(s) or data href; download the image and use href=\"@./path\" or provide a file token", path)
		}
		if err := validateSVGlideRequiredAttrs(path, tagName, role, attrs); err != nil {
			return svgValidationStop, err
		}
		return svgValidationSkipSubtree, nil
	default:
		return svgValidationStop, output.ErrValidation("--file %s: <%s> has unsupported slide:role=%q; use \"shape\" or \"image\"", path, tagName, role)
	}
}

func validateSVGlideChartMarker(path, attrs, inner string) (string, error) {
	chartRef := strings.TrimSpace(xmlAttrValue(attrs, "slide:chart-ref"))
	if chartRef == "" {
		return "", output.ErrValidation("--file %s: <g slide:role=\"chart\"> missing required attribute \"slide:chart-ref\"", path)
	}
	for _, attr := range []string{"x", "y", "width", "height"} {
		value := xmlAttrValue(attrs, attr)
		if strings.TrimSpace(value) == "" {
			return "", output.ErrValidation("--file %s: <g slide:role=\"chart\"> missing required attribute %q", path, attr)
		}
		if !isSVGlideNumber(value) {
			return "", output.ErrValidation("--file %s: <g slide:role=\"chart\"> attribute %q must be a number or px length, got %q", path, attr, value)
		}
	}

	metadataAttrs, payload, err := extractSingleSVGlideChartMetadata(path, inner)
	if err != nil {
		return "", err
	}
	if strings.TrimSpace(xmlAttrValue(metadataAttrs, "data-svglide-whiteboard")) != "" {
		return "", output.ErrValidation("--file %s: legacy SVGlide whiteboard marker metadata is not supported by slides +create-svg", path)
	}
	if !hasXMLAttr(metadataAttrs, "data-svglide-chart", svglideChartMarkerVersion) {
		return "", output.ErrValidation("--file %s: chart marker metadata must include data-svglide-chart=\"%s\"", path, svglideChartMarkerVersion)
	}
	if !hasXMLAttr(metadataAttrs, "data-format", svglideChartFormat) {
		return "", output.ErrValidation("--file %s: chart marker metadata must include data-format=\"%s\"", path, svglideChartFormat)
	}
	if !hasXMLAttr(metadataAttrs, "data-encoding", svglideChartEncoding) {
		return "", output.ErrValidation("--file %s: chart marker metadata must include data-encoding=\"%s\"", path, svglideChartEncoding)
	}
	hash := xmlAttrValue(metadataAttrs, "data-payload-hash")
	if !svgSHA256HashRegex.MatchString(hash) {
		return "", output.ErrValidation("--file %s: chart marker metadata must include data-payload-hash=\"sha256:<64 hex>\"", path)
	}
	decoded, err := decodeSVGlideChartPayload(payload)
	if err != nil {
		return "", output.ErrValidation("--file %s: chart marker metadata payload must be base64url: %v", path, err)
	}
	sum := sha256.Sum256(decoded)
	if !strings.EqualFold(hash, "sha256:"+hex.EncodeToString(sum[:])) {
		return "", output.ErrValidation("--file %s: chart marker metadata data-payload-hash does not match decoded payload", path)
	}
	if err := validateSVGlideChartSpecPayload(decoded); err != nil {
		return "", output.ErrValidation("--file %s: chart marker metadata decoded payload must be valid %s JSON: %v", path, svglideChartFormat, err)
	}
	return chartRef, nil
}

func extractSingleSVGlideChartMetadata(path, inner string) (attrs, payload string, err error) {
	seen := false
	for i := 0; i < len(inner); {
		rel := strings.IndexByte(inner[i:], '<')
		if rel < 0 {
			if strings.TrimSpace(inner[i:]) != "" {
				return "", "", output.ErrValidation("--file %s: <g slide:role=\"chart\"> may only contain one metadata child", path)
			}
			break
		}
		if strings.TrimSpace(inner[i:i+rel]) != "" {
			return "", "", output.ErrValidation("--file %s: <g slide:role=\"chart\"> may only contain one metadata child", path)
		}
		i += rel
		switch {
		case strings.HasPrefix(inner[i:], "<!--"):
			end := strings.Index(inner[i+4:], "-->")
			if end < 0 {
				return "", "", output.ErrValidation("--file %s: malformed SVG comment", path)
			}
			i += 4 + end + 3
			continue
		case strings.HasPrefix(inner[i:], "<?"):
			end := strings.Index(inner[i+2:], "?>")
			if end < 0 {
				return "", "", output.ErrValidation("--file %s: malformed SVG processing instruction", path)
			}
			i += 2 + end + 2
			continue
		case strings.HasPrefix(inner[i:], "</"), strings.HasPrefix(inner[i:], "<!"):
			return "", "", output.ErrValidation("--file %s: <g slide:role=\"chart\"> may only contain one metadata child", path)
		}
		end := findSVGTagEnd(inner, i)
		if end < 0 {
			return "", "", output.ErrValidation("--file %s: malformed chart marker metadata", path)
		}
		name, metadataAttrs, selfClosing := parseSVGStartTag(inner[i+1 : end])
		if name != "metadata" {
			return "", "", output.ErrValidation("--file %s: <g slide:role=\"chart\"> may only contain one metadata child", path)
		}
		if seen {
			return "", "", output.ErrValidation("--file %s: <g slide:role=\"chart\"> must contain exactly one metadata child", path)
		}
		if selfClosing {
			return "", "", output.ErrValidation("--file %s: chart marker metadata payload is empty", path)
		}
		closeStart, closeEnd := findSVGElementClose(inner, end+1, "metadata")
		if closeStart < 0 {
			return "", "", output.ErrValidation("--file %s: malformed chart marker metadata: missing </metadata>", path)
		}
		seen = true
		attrs = metadataAttrs
		payload = strings.TrimSpace(inner[end+1 : closeStart])
		i = closeEnd + 1
	}
	if !seen {
		return "", "", output.ErrValidation("--file %s: <g slide:role=\"chart\"> must contain exactly one metadata child", path)
	}
	return attrs, payload, nil
}

func decodeSVGlideChartPayload(payload string) ([]byte, error) {
	payload = strings.TrimSpace(payload)
	if payload == "" {
		return nil, fmt.Errorf("empty payload")
	}
	if !svgBase64URLRegex.MatchString(payload) {
		return nil, fmt.Errorf("payload must use unpadded URL-safe base64 characters")
	}
	return base64.RawURLEncoding.DecodeString(payload)
}

func validateSVGlideChartSpecPayload(payload []byte) error {
	var spec svglideChartSpecPayload
	if err := json.Unmarshal(payload, &spec); err != nil {
		return err
	}
	if spec.Version == nil || strings.TrimSpace(*spec.Version) == "" {
		return fmt.Errorf("missing version")
	}
	if strings.TrimSpace(*spec.Version) != svglideChartSpecVersion {
		return fmt.Errorf("version must be %q", svglideChartSpecVersion)
	}
	if spec.ChartType == nil || strings.TrimSpace(*spec.ChartType) == "" {
		return fmt.Errorf("missing chartType")
	}
	switch strings.TrimSpace(*spec.ChartType) {
	case "bar", "line":
	default:
		return fmt.Errorf("chartType must be one of bar,line")
	}
	if spec.Data == nil {
		return fmt.Errorf("missing data")
	}
	if len(spec.Data.Categories) == 0 {
		return fmt.Errorf("data.categories must be a non-empty array")
	}
	for i, category := range spec.Data.Categories {
		if strings.TrimSpace(category) == "" {
			return fmt.Errorf("data.categories[%d] must be a non-empty string", i)
		}
	}
	if len(spec.Data.Series) == 0 {
		return fmt.Errorf("data.series must be a non-empty array")
	}
	for i, series := range spec.Data.Series {
		if series.Name == nil || strings.TrimSpace(*series.Name) == "" {
			return fmt.Errorf("data.series[%d].name must be a non-empty string", i)
		}
		if len(series.Values) != len(spec.Data.Categories) {
			return fmt.Errorf("data.series[%d].values length must match data.categories length", i)
		}
		for j, value := range series.Values {
			if err := validateSVGlideChartNumber(value); err != nil {
				return fmt.Errorf("data.series[%d].values[%d] must be a finite number: %v", i, j, err)
			}
		}
	}
	return nil
}

func validateSVGlideChartNumber(raw json.RawMessage) error {
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	var value any
	if err := decoder.Decode(&value); err != nil {
		return err
	}
	var extra any
	if err := decoder.Decode(&extra); err == nil {
		return fmt.Errorf("multiple JSON values")
	}
	number, ok := value.(json.Number)
	if !ok {
		return fmt.Errorf("got %T", value)
	}
	n, err := number.Float64()
	if err != nil {
		return err
	}
	if math.IsNaN(n) || math.IsInf(n, 0) {
		return fmt.Errorf("non-finite number")
	}
	return nil
}

func validateSVGlideRequiredAttrs(path, tagName, role, attrs string) error {
	for _, attr := range svgRequiredAttrsByTag[tagName] {
		if strings.TrimSpace(xmlAttrValue(attrs, attr)) == "" {
			return output.ErrValidation("--file %s: <%s slide:role=\"%s\"> missing required attribute %q for SVGlide", path, tagName, role, attr)
		}
	}
	for _, attr := range svgGeometryAttrsByTag[tagName] {
		value := xmlAttrValue(attrs, attr)
		if !isSVGlideNumber(value) {
			return output.ErrValidation("--file %s: <%s slide:role=\"%s\"> attribute %q must be a number or px length, got %q", path, tagName, role, attr, value)
		}
	}
	if tagName == "path" {
		if err := validateSVGlidePathData(path, attrs); err != nil {
			return err
		}
	}
	return nil
}

func isSVGlideNumber(value string) bool {
	value = strings.TrimSpace(value)
	return value != "" && svgNumberRegex.MatchString(value)
}

func validateSVGlideTransform(path, tagName, attrs string) error {
	transform := strings.TrimSpace(xmlAttrValue(attrs, "transform"))
	if transform == "" {
		return nil
	}
	for _, m := range svgTransformRegex.FindAllStringSubmatch(transform, -1) {
		if len(m) < 3 {
			continue
		}
		fn := strings.TrimSpace(m[1])
		for _, arg := range strings.FieldsFunc(m[2], func(r rune) bool {
			return r == ',' || isXMLSpace(r)
		}) {
			arg = strings.TrimSpace(arg)
			if arg == "" {
				continue
			}
			if !isSVGlideNumber(arg) {
				return output.ErrValidation("--file %s: <%s> transform %s() argument must be a number or px length, got %q", path, tagName, fn, arg)
			}
		}
	}
	return nil
}

func validateSVGlidePathData(path, attrs string) error {
	d := strings.TrimSpace(xmlAttrValue(attrs, "d"))
	withoutNumbers := svgPathNumberRegex.ReplaceAllString(d, "")
	hasCommand := false
	for _, r := range withoutNumbers {
		switch {
		case r == ',' || isXMLSpace(r):
			continue
		case strings.ContainsRune("MLHVZCQmlhvzcq", r):
			hasCommand = true
		default:
			return output.ErrValidation("--file %s: <path slide:role=\"shape\"> unsupported path command or character %q; use only M/L/H/V/C/Q/Z commands", path, string(r))
		}
	}
	if !hasCommand {
		return output.ErrValidation("--file %s: <path slide:role=\"shape\"> attribute \"d\" must include at least one M/L/H/V/C/Q/Z path command", path)
	}
	return nil
}

func isExternalSVGHref(value string) bool {
	lower := strings.ToLower(strings.TrimSpace(value))
	return strings.HasPrefix(lower, "http://") ||
		strings.HasPrefix(lower, "https://") ||
		strings.HasPrefix(lower, "data:")
}

func parseSVGAssets(runtime *common.RuntimeContext, path string) (svgAssetMap, error) {
	if strings.TrimSpace(path) == "" {
		return nil, nil
	}
	data, err := cmdutil.ReadInputFile(runtime.FileIO(), path)
	if err != nil {
		return nil, common.WrapInputStatError(err, fmt.Sprintf("--assets %s", path))
	}
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, output.ErrValidation("--assets %s: invalid JSON object: %v", path, err)
	}
	assets := make(svgAssetMap, len(raw))
	for k, v := range raw {
		if strings.TrimSpace(k) == "" {
			return nil, output.ErrValidation("--assets %s: keys must be non-empty strings", path)
		}
		var token string
		if err := json.Unmarshal(v, &token); err == nil {
			if strings.TrimSpace(token) == "" {
				return nil, output.ErrValidation("--assets %s: file tokens must be non-empty strings", path)
			}
			assets[k] = svgAssetMeta{Token: strings.TrimSpace(token)}
			continue
		}
		var meta svgAssetMeta
		if err := json.Unmarshal(v, &meta); err != nil {
			return nil, output.ErrValidation("--assets %s: values must be file token strings or metadata objects", path)
		}
		meta = normalizeSVGAssetMeta(meta)
		if meta.Token == "" {
			return nil, output.ErrValidation("--assets %s: metadata object for %s must include token", path, k)
		}
		assets[k] = meta
	}
	return assets, nil
}

func validateSVGAssetsPath(runtime *common.RuntimeContext, path string) error {
	if strings.TrimSpace(path) == "" {
		return nil
	}
	stat, err := runtime.FileIO().Stat(path)
	if err != nil {
		return common.WrapInputStatError(err, fmt.Sprintf("--assets %s: file not found", path))
	}
	if !stat.Mode().IsRegular() {
		return output.ErrValidation("--assets %s: must be a regular file", path)
	}
	if stat.Size() == 0 {
		return output.ErrValidation("--assets %s: file is empty", path)
	}
	return nil
}

func rewriteSVGImagePlaceholders(runtime *common.RuntimeContext, presentationID string, svgs []string, assets svgAssetMap) ([]RewrittenSVGPage, int, error) {
	paths := extractSVGImagePlaceholderPaths(svgs, assets)
	localAssets, uploaded, err := uploadSVGImagePlaceholders(runtime, presentationID, paths)
	if err != nil {
		return nil, uploaded, err
	}
	allAssets := mergedSVGAssets(assets, localAssets)
	pages := make([]RewrittenSVGPage, 0, len(svgs))
	for _, svg := range svgs {
		content, usedAssets := rewriteSVGImagePlaceholdersWithTokens(svg, allAssets)
		pages = append(pages, RewrittenSVGPage{Content: content, Assets: usedAssets})
	}
	return pages, uploaded, nil
}

func dryRunRewriteSVGImagePlaceholders(runtime *common.RuntimeContext, svgs []string, assets svgAssetMap) ([]RewrittenSVGPage, []string, error) {
	paths := extractSVGImagePlaceholderPaths(svgs, assets)
	localAssets := make(svgAssetMap, len(paths))
	for _, path := range paths {
		token := "<uploaded_file_token:" + filepath.Base(path) + ">"
		meta, err := probeSVGAssetMeta(runtime, path, token)
		if err != nil {
			return nil, paths, err
		}
		localAssets[path] = meta
	}
	allAssets := mergedSVGAssets(assets, localAssets)
	pages := make([]RewrittenSVGPage, 0, len(svgs))
	for _, svg := range svgs {
		content, usedAssets := rewriteSVGImagePlaceholdersWithTokens(svg, allAssets)
		pages = append(pages, RewrittenSVGPage{Content: content, Assets: usedAssets})
	}
	return pages, paths, nil
}

func uploadSVGImagePlaceholders(runtime *common.RuntimeContext, presentationID string, paths []string) (svgAssetMap, int, error) {
	assets := make(svgAssetMap, len(paths))
	for i, path := range paths {
		stat, err := runtime.FileIO().Stat(path)
		if err != nil {
			return assets, i, slidesInputStatError(err, "--slides", fmt.Sprintf("@%s: file not found", path))
		}
		if !stat.Mode().IsRegular() {
			return assets, i, output.ErrValidation("@%s: must be a regular file", path)
		}
		fileName := filepath.Base(path)
		fmt.Fprintf(runtime.IO().ErrOut, "Uploading image %d/%d: %s (%s)\n",
			i+1, len(paths), fileName, common.FormatSize(stat.Size()))

		token, err := uploadSlidesMedia(runtime, path, fileName, stat.Size(), presentationID)
		if err != nil {
			return assets, i, fmt.Errorf("@%s: %w", path, err) //nolint:forbidigo // preserves upload cause for caller progress context
		}
		meta, err := probeSVGAssetMeta(runtime, path, token)
		if err != nil {
			return assets, i + 1, err
		}
		assets[path] = meta
	}
	return assets, len(paths), nil
}

func probeSVGAssetMeta(runtime *common.RuntimeContext, path string, token string) (svgAssetMeta, error) {
	token = strings.TrimSpace(token)
	if token == "" {
		return svgAssetMeta{}, output.ErrValidation("@%s: uploaded file token is empty", path)
	}
	stat, err := runtime.FileIO().Stat(path)
	if err != nil {
		return svgAssetMeta{}, slidesInputStatError(err, "--slides", fmt.Sprintf("@%s: file not found", path))
	}
	data, err := cmdutil.ReadInputFile(runtime.FileIO(), path)
	if err != nil {
		return svgAssetMeta{}, common.WrapInputStatError(err, fmt.Sprintf("@%s", path))
	}
	config, format, err := image.DecodeConfig(bytes.NewReader(data))
	if err != nil {
		return svgAssetMeta{}, output.ErrValidation("@%s: cannot decode image metadata: %v", path, err)
	}
	meta := svgAssetMeta{
		Token:    token,
		Name:     filepath.Base(path),
		MimeType: mimeTypeForImageFormat(format),
		Size:     stat.Size(),
		Width:    config.Width,
		Height:   config.Height,
	}
	if meta.MimeType == "" {
		meta.MimeType = mimeTypeForImageFormat(strings.TrimPrefix(strings.ToLower(filepath.Ext(path)), "."))
	}
	if err := validateSVGAssetMeta(meta); err != nil {
		return svgAssetMeta{}, output.ErrValidation("@%s: %v", path, err)
	}
	return meta, nil
}

func mimeTypeForImageFormat(format string) string {
	switch strings.ToLower(strings.TrimSpace(format)) {
	case "png":
		return "image/png"
	case "jpeg", "jpg":
		return "image/jpeg"
	case "gif":
		return "image/gif"
	case "webp":
		return "image/webp"
	default:
		return ""
	}
}

func mergedSVGAssets(assets, localAssets svgAssetMap) svgAssetMap {
	merged := svgAssetMap{}
	for k, v := range assets {
		key := strings.TrimSpace(k)
		asset := normalizeSVGAssetMeta(v)
		if strings.HasPrefix(key, "@") {
			key = strings.TrimSpace(strings.TrimPrefix(key, "@"))
		}
		if key != "" && asset.Token != "" {
			merged[key] = asset
		}
	}
	for k, v := range localAssets {
		asset := normalizeSVGAssetMeta(v)
		if strings.TrimSpace(k) != "" && asset.Token != "" {
			merged[k] = asset
		}
	}
	return merged
}

func extractSVGImagePlaceholderPaths(svgs []string, assets svgAssetMap) []string {
	var paths []string
	seen := map[string]bool{}
	for _, svg := range svgs {
		for _, tag := range svgImageTagRegex.FindAllString(svg, -1) {
			for _, m := range svgImageHrefRegex.FindAllStringSubmatch(tag, -1) {
				if len(m) < 6 || m[3] != m[5] || !strings.HasPrefix(m[4], "@") {
					continue
				}
				path := strings.TrimSpace(strings.TrimPrefix(m[4], "@"))
				if path == "" || seen[path] || svgAssetTokenForPath(assets, path) != "" {
					continue
				}
				seen[path] = true
				paths = append(paths, path)
			}
		}
	}
	return paths
}

func rewriteSVGImagePlaceholdersWithTokens(svg string, assets svgAssetMap) (string, []svgAssetMeta) {
	var used []svgAssetMeta
	seen := map[string]bool{}
	remember := func(asset svgAssetMeta) {
		token := strings.TrimSpace(asset.Token)
		if token == "" || seen[token] {
			return
		}
		seen[token] = true
		asset.Token = token
		used = append(used, asset)
	}

	out := svgImageTagRegex.ReplaceAllStringFunc(svg, func(tag string) string {
		return svgImageHrefRegex.ReplaceAllStringFunc(tag, func(attr string) string {
			m := svgImageHrefRegex.FindStringSubmatch(attr)
			if len(m) < 6 || m[3] != m[5] {
				return attr
			}
			prefix := m[1]
			name := m[2]
			value := strings.TrimSpace(m[4])
			if strings.HasPrefix(value, "@") {
				path := strings.TrimSpace(strings.TrimPrefix(value, "@"))
				asset := assets[path]
				if asset.Token == "" {
					return attr
				}
				remember(asset)
				return fmt.Sprintf(`%shref="%s"`, prefix, xmlEscape(asset.Token))
			}
			if strings.EqualFold(name, "xlink:href") {
				if shouldTreatAsFileToken(value) {
					remember(assetForToken(assets, value))
				}
				return fmt.Sprintf(`%shref="%s"`, prefix, xmlEscape(value))
			}
			if shouldTreatAsFileToken(value) {
				remember(assetForToken(assets, value))
			}
			return attr
		})
	})
	return out, used
}

func assetForToken(assets svgAssetMap, token string) svgAssetMeta {
	token = strings.TrimSpace(token)
	for _, asset := range assets {
		if strings.TrimSpace(asset.Token) == token {
			return normalizeSVGAssetMeta(asset)
		}
	}
	return svgAssetMeta{Token: token}
}

func svgAssetTokenForPath(assets svgAssetMap, path string) string {
	if len(assets) == 0 {
		return ""
	}
	if asset := normalizeSVGAssetMeta(assets["@"+path]); asset.Token != "" {
		return asset.Token
	}
	return normalizeSVGAssetMeta(assets[path]).Token
}

func validateSVGRasterAssetConflicts(assets svgAssetMap, report *svgPrepareReport) error {
	if len(assets) == 0 || report == nil {
		return nil
	}
	for _, asset := range report.GeneratedAssets {
		key := strings.TrimSpace(asset)
		if key == "" {
			continue
		}
		if svgAssetTokenForPath(assets, key) != "" {
			return output.ErrValidation("--assets conflicts with generated raster asset %q; remove this key so create-svg can upload the generated PNG", key)
		}
	}
	return nil
}

func shouldTreatAsFileToken(value string) bool {
	value = strings.TrimSpace(value)
	if value == "" || strings.HasPrefix(value, "@") || strings.HasPrefix(value, "#") {
		return false
	}
	lower := strings.ToLower(value)
	return !strings.HasPrefix(lower, "http://") && !strings.HasPrefix(lower, "https://") && !strings.HasPrefix(lower, "data:")
}

func injectSVGTransportAssetMetadata(svg string, assets []svgAssetMeta) (string, error) {
	assets = dedupeSVGAssetMeta(assets)
	if len(assets) == 0 {
		return svg, nil
	}
	for _, asset := range assets {
		if err := validateSVGAssetMeta(asset); err != nil {
			return "", err
		}
	}
	m := svgRootOpenTagRegex.FindStringSubmatchIndex(svg)
	if m == nil {
		return "", fmt.Errorf("SVG root element not found")
	}
	tagName := svg[m[4]:m[5]]
	if tagName != "svg" {
		return "", fmt.Errorf("root element must be <svg>")
	}

	if existing := svgMetadataRegex.FindStringIndex(svg); existing != nil {
		block := svg[existing[0]:existing[1]]
		existingTokens := metadataImgTokens(block)
		var missing []svgAssetMeta
		for _, asset := range assets {
			if !existingTokens[asset.Token] {
				missing = append(missing, asset)
			}
		}
		upgraded := svgAssetsMetadataAttrRegex.ReplaceAllString(block, `data-svglide-assets="`+svglideAssetsVersion+`"`)
		upgraded = rewriteExistingSVGTransportImgs(upgraded, assets)
		if len(missing) == 0 {
			return svg[:existing[0]] + upgraded + svg[existing[1]:], nil
		}
		addition := renderSVGTransportImgs(missing)
		rewritten := svgMetadataEndRegex.ReplaceAllStringFunc(upgraded, func(end string) string {
			return addition + end
		})
		return svg[:existing[0]] + rewritten + svg[existing[1]:], nil
	}

	metadata := `<metadata data-svglide-assets="` + svglideAssetsVersion + `">` + renderSVGTransportImgs(assets) + `</metadata>`
	prefix := svg[:m[8]]
	closer := svg[m[8]:m[9]]
	after := svg[m[9]:]
	if closer == "/>" {
		return prefix + ">" + metadata + "</svg>" + after, nil
	}
	return svg[:m[9]] + metadata + after, nil
}

func metadataImgTokens(metadata string) map[string]bool {
	out := map[string]bool{}
	for _, m := range svgMetadataImgRegex.FindAllStringSubmatch(metadata, -1) {
		if len(m) >= 4 && m[1] == m[3] {
			out[m[2]] = true
		}
	}
	return out
}

func rewriteExistingSVGTransportImgs(metadata string, assets []svgAssetMeta) string {
	byToken := map[string]svgAssetMeta{}
	for _, asset := range assets {
		byToken[asset.Token] = asset
	}
	return svgMetadataImgTagRegex.ReplaceAllStringFunc(metadata, func(tag string) string {
		for _, m := range svgMetadataImgRegex.FindAllStringSubmatch(tag, -1) {
			if len(m) >= 4 && m[1] == m[3] {
				if asset, ok := byToken[m[2]]; ok {
					return renderSVGTransportImg(asset)
				}
			}
		}
		return tag
	})
}

func renderSVGTransportImgs(assets []svgAssetMeta) string {
	var b strings.Builder
	for _, asset := range assets {
		b.WriteString(renderSVGTransportImg(asset))
	}
	return b.String()
}

func renderSVGTransportImg(asset svgAssetMeta) string {
	return `<img xmlns="" src="` + xmlEscape(asset.Token) +
		`" name="` + xmlEscape(asset.Name) +
		`" mimeType="` + xmlEscape(asset.MimeType) +
		`" size="` + fmt.Sprintf("%d", asset.Size) +
		`" width="` + fmt.Sprintf("%d", asset.Width) +
		`" height="` + fmt.Sprintf("%d", asset.Height) +
		`" />`
}

func normalizeSVGAssetMeta(asset svgAssetMeta) svgAssetMeta {
	asset.Token = strings.TrimSpace(asset.Token)
	asset.Name = strings.TrimSpace(asset.Name)
	asset.MimeType = strings.TrimSpace(asset.MimeType)
	return asset
}

func validateSVGAssetMeta(asset svgAssetMeta) error {
	asset = normalizeSVGAssetMeta(asset)
	var missing []string
	if asset.Token == "" {
		missing = append(missing, "token")
	}
	if asset.Name == "" {
		missing = append(missing, "name")
	}
	if asset.MimeType == "" {
		missing = append(missing, "mimeType")
	}
	if asset.Size <= 0 {
		missing = append(missing, "size")
	}
	if asset.Width <= 0 {
		missing = append(missing, "width")
	}
	if asset.Height <= 0 {
		missing = append(missing, "height")
	}
	if len(missing) > 0 {
		token := asset.Token
		if token == "" {
			token = "<empty>"
		}
		return output.ErrValidation("incomplete SVG image asset metadata for %s: missing %s", token, strings.Join(missing, ", "))
	}
	return nil
}

func dedupeSVGAssetMeta(in []svgAssetMeta) []svgAssetMeta {
	var out []svgAssetMeta
	seen := map[string]bool{}
	for _, asset := range in {
		asset = normalizeSVGAssetMeta(asset)
		if asset.Token == "" || seen[asset.Token] {
			continue
		}
		seen[asset.Token] = true
		out = append(out, asset)
	}
	return out
}

func dedupeStrings(in []string) []string {
	var out []string
	seen := map[string]bool{}
	for _, item := range in {
		item = strings.TrimSpace(item)
		if item == "" || seen[item] {
			continue
		}
		seen[item] = true
		out = append(out, item)
	}
	return out
}

func buildCreateSVGBody(svg string) map[string]interface{} {
	return map[string]interface{}{
		"slide": map[string]interface{}{"content": svg},
	}
}

func extractSVGlideErrorJSON(err error) map[string]interface{} {
	if err == nil {
		return nil
	}
	const marker = "SVGLIDE_ERROR_JSON:"
	msg := err.Error()
	idx := strings.Index(msg, marker)
	if idx < 0 {
		return nil
	}
	raw := strings.TrimSpace(msg[idx+len(marker):])
	if end := strings.IndexAny(raw, "\r\n"); end >= 0 {
		raw = raw[:end]
	}
	var parsed map[string]interface{}
	if json.Unmarshal([]byte(raw), &parsed) != nil {
		return nil
	}
	return parsed
}

func formatSVGlideErrorSuffix(err error) string {
	parsed := extractSVGlideErrorJSON(err)
	if len(parsed) == 0 {
		return ""
	}
	data, jsonErr := json.Marshal(parsed)
	if jsonErr != nil {
		return ""
	}
	return " svglide_error=" + string(data)
}
