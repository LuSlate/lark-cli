// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
)

const (
	maxSVGFileSizeBytes int64 = 2 * 1024 * 1024

	svgContractNamespace   = "https://slides.bytedance.com/ns"
	svgContractVersion     = "svglide-authoring-contract/v1"
	svgContractVersionAttr = "slide:contract-version"
	svgRasterizerEnv       = "SVGLIDE_RASTERIZER"
	defaultSVGRenderer     = "resvg"
	defaultSVGRenderWait   = 15 * time.Second

	svgDiagSeverityError   = "error"
	svgDiagSeverityWarning = "warning"

	svgDiagRootMissing          = "root_missing"
	svgDiagRootUnsupported      = "root_unsupported"
	svgDiagMissingNamespace     = "missing_slide_namespace"
	svgDiagMissingSlideRole     = "missing_slide_role"
	svgDiagContractVersion      = "contract_version_mismatch"
	svgDiagMalformedElement     = "malformed_element"
	svgDiagDisallowedScript     = "disallowed_script"
	svgDiagDisallowedEventAttr  = "disallowed_event_attribute"
	svgDiagExternalReference    = "external_reference"
	svgDiagNativeUnsupported    = "native_unsupported"
	svgDiagMissingPageSize      = "missing_page_size"
	svgDiagRendererUnavailable  = "renderer_unavailable"
	svgDiagRendererFailed       = "renderer_failed"
	svgDiagRendererTimeout      = "renderer_timeout"
	svgDiagRasterOutputMissing  = "raster_output_missing"
	svgDiagRasterOutputEmpty    = "raster_output_empty"
	svgDiagRasterOutputTooLarge = "raster_output_too_large"
)

type svgClassifyMode string

const (
	svgClassifyNative   svgClassifyMode = "native"
	svgClassifyFallback svgClassifyMode = "fallback"
	svgClassifyReject   svgClassifyMode = "reject"
)

type RewrittenSVGPage struct {
	Content string
	Tokens  []string
}

type SVGlideDiagnostic struct {
	Code      string `json:"code"`
	Severity  string `json:"severity"`
	Path      string `json:"path,omitempty"`
	PageIndex int    `json:"page_index"`
	TagName   string `json:"tag_name,omitempty"`
	AttrName  string `json:"attr_name,omitempty"`
	Message   string `json:"message"`
}

type svgClassifiedPage struct {
	Path        string
	Content     string
	Mode        svgClassifyMode
	Diagnostics []SVGlideDiagnostic
}

type svglideDiagnosticsError struct {
	message     string
	diagnostics []SVGlideDiagnostic
}

func (e *svglideDiagnosticsError) Error() string {
	if len(e.diagnostics) == 0 {
		return e.message
	}
	return e.message + ": " + formatSVGlideDiagnostics(e.diagnostics)
}

func newSVGlideDiagnosticsError(message string, diagnostics []SVGlideDiagnostic) error {
	return &svglideDiagnosticsError{message: message, diagnostics: diagnostics}
}

func svglideDiagnosticsFromError(err error) []SVGlideDiagnostic {
	var diagErr *svglideDiagnosticsError
	if errors.As(err, &diagErr) {
		return diagErr.diagnostics
	}
	return nil
}

func formatSVGlideDiagnostics(diagnostics []SVGlideDiagnostic) string {
	data, err := json.Marshal(diagnostics)
	if err != nil {
		return fmt.Sprintf("%v", diagnostics)
	}
	return string(data)
}

func newSVGlideDiagnostic(code, severity, path string, pageIndex int, message string) SVGlideDiagnostic {
	return SVGlideDiagnostic{
		Code:      code,
		Severity:  severity,
		Path:      path,
		PageIndex: pageIndex,
		Message:   message,
	}
}

type svgRasterizer interface {
	CheckAvailable(ctx context.Context) error
	Rasterize(ctx context.Context, svgPath string) (string, int64, error)
}

var svgFallbackRasterizer svgRasterizer = newCommandSVGRasterizer()

type commandSVGRasterizer struct {
	command       string
	timeout       time.Duration
	maxOutputSize int64
	env           []string
	lookPath      func(string) (string, error)
}

func newCommandSVGRasterizer() commandSVGRasterizer {
	command := strings.TrimSpace(os.Getenv(svgRasterizerEnv))
	if command == "" {
		command = defaultSVGRenderer
	}
	return commandSVGRasterizer{
		command:       command,
		timeout:       defaultSVGRenderWait,
		maxOutputSize: common.MaxDriveMediaUploadSinglePartSize,
	}
}

func (r commandSVGRasterizer) commandName() string {
	if strings.TrimSpace(r.command) != "" {
		return strings.TrimSpace(r.command)
	}
	return defaultSVGRenderer
}

func (r commandSVGRasterizer) renderTimeout() time.Duration {
	if r.timeout > 0 {
		return r.timeout
	}
	return defaultSVGRenderWait
}

func (r commandSVGRasterizer) outputLimit() int64 {
	if r.maxOutputSize > 0 {
		return r.maxOutputSize
	}
	return common.MaxDriveMediaUploadSinglePartSize
}

func (r commandSVGRasterizer) resolveCommand() (string, error) {
	lookPath := r.lookPath
	if lookPath == nil {
		lookPath = exec.LookPath
	}
	command := r.commandName()
	resolved, err := lookPath(command)
	if err != nil {
		return "", newSVGlideDiagnosticsError("SVGlide fallback renderer unavailable", []SVGlideDiagnostic{{
			Code:     svgDiagRendererUnavailable,
			Severity: svgDiagSeverityError,
			Message:  fmt.Sprintf("renderer %q was not found; install resvg or set %s", command, svgRasterizerEnv),
		}})
	}
	return resolved, nil
}

func (r commandSVGRasterizer) CheckAvailable(context.Context) error {
	_, err := r.resolveCommand()
	return err
}

func (r commandSVGRasterizer) Rasterize(ctx context.Context, svgPath string) (string, int64, error) {
	command, err := r.resolveCommand()
	if err != nil {
		return "", 0, err
	}
	out, err := os.CreateTemp("", "lark-cli-svglide-*.png")
	if err != nil {
		return "", 0, newSVGlideDiagnosticsError("SVGlide fallback raster output unavailable", []SVGlideDiagnostic{{
			Code:     svgDiagRasterOutputMissing,
			Severity: svgDiagSeverityError,
			Path:     svgPath,
			Message:  err.Error(),
		}})
	}
	outPath := out.Name()
	if closeErr := out.Close(); closeErr != nil {
		_ = os.Remove(outPath)
		return "", 0, closeErr
	}

	renderCtx, cancel := context.WithTimeout(ctx, r.renderTimeout())
	defer cancel()

	cmd := exec.CommandContext(renderCtx, command, svgPath, outPath)
	if len(r.env) > 0 {
		cmd.Env = append(os.Environ(), r.env...)
	}
	var stderr strings.Builder
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		_ = os.Remove(outPath)
		code := svgDiagRendererFailed
		if renderCtx.Err() == context.DeadlineExceeded {
			code = svgDiagRendererTimeout
		}
		message := strings.TrimSpace(stderr.String())
		if message == "" {
			message = err.Error()
		}
		return "", 0, newSVGlideDiagnosticsError("SVGlide fallback rasterization failed", []SVGlideDiagnostic{{
			Code:     code,
			Severity: svgDiagSeverityError,
			Path:     svgPath,
			Message:  message,
		}})
	}

	stat, err := os.Stat(outPath)
	if err != nil {
		_ = os.Remove(outPath)
		return "", 0, newSVGlideDiagnosticsError("SVGlide fallback raster output missing", []SVGlideDiagnostic{{
			Code:     svgDiagRasterOutputMissing,
			Severity: svgDiagSeverityError,
			Path:     svgPath,
			Message:  err.Error(),
		}})
	}
	if stat.Size() == 0 {
		_ = os.Remove(outPath)
		return "", 0, newSVGlideDiagnosticsError("SVGlide fallback raster output is empty", []SVGlideDiagnostic{{
			Code:     svgDiagRasterOutputEmpty,
			Severity: svgDiagSeverityError,
			Path:     svgPath,
			Message:  "renderer produced an empty PNG",
		}})
	}
	if limit := r.outputLimit(); stat.Size() > limit {
		_ = os.Remove(outPath)
		return "", 0, newSVGlideDiagnosticsError("SVGlide fallback raster output is too large", []SVGlideDiagnostic{{
			Code:     svgDiagRasterOutputTooLarge,
			Severity: svgDiagSeverityError,
			Path:     svgPath,
			Message:  fmt.Sprintf("renderer output %s exceeds %s limit", common.FormatSize(stat.Size()), common.FormatSize(limit)),
		}})
	}
	return outPath, stat.Size(), nil
}

var (
	svgRootOpenTagRegex = regexp.MustCompile(`(?s)\A(\s*(?:<\?[^?]*(?:\?[^>][^?]*)*\?>\s*)?(?:<!DOCTYPE[^>]*>\s*)?(?:<!--.*?-->\s*)*)<([A-Za-z_][\w.:-]*)((?:\s[^>]*?)?)(/?>)`)
	svgAttrRegex        = regexp.MustCompile(`(?is)(?:^|\s)([A-Za-z_:][\w.:-]*)\s*=\s*(["'])([^"']*)(["'])`)
	svgImageTagRegex    = regexp.MustCompile(`(?is)<image\b[^>]*>`)
	svgImageHrefRegex   = regexp.MustCompile(`(?is)(^|\s)(xlink:href|href)\s*=\s*(["'])([^"']*)(["'])`)
	svgMetadataRegex    = regexp.MustCompile(`(?is)<metadata\b[^>]*\bdata-svglide-assets\s*=\s*(["'])true(["'])[^>]*>.*?</metadata>`)
	svgMetadataEndRegex = regexp.MustCompile(`(?is)</metadata\s*>`)
	svgMetadataImgRegex = regexp.MustCompile(`(?is)<img\b[^>]*\bsrc\s*=\s*(["'])([^"']+)(["'])`)
	svgNumberRegex      = regexp.MustCompile(`^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?(?:px)?$`)
	svgPathNumberRegex  = regexp.MustCompile(`[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?`)
	svgTransformRegex   = regexp.MustCompile(`(?is)([a-zA-Z]+)\(([^)]*)\)`)
	svgExternalURLRegex = regexp.MustCompile(`(?is)url\(\s*['"]?https?://`)
	svgShapeTags        = map[string]bool{
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
		svgs = append(svgs, string(data))
	}
	return svgs, nil
}

func classifySVGlideSVGPages(paths, svgs []string) ([]svgClassifiedPage, error) {
	pages := make([]svgClassifiedPage, 0, len(svgs))
	var rejected []SVGlideDiagnostic
	for i, svg := range svgs {
		path := ""
		if i < len(paths) {
			path = paths[i]
		}
		page := classifySVGlideSVGPage(svg, path, i)
		pages = append(pages, page)
		if page.Mode == svgClassifyReject {
			rejected = append(rejected, page.Diagnostics...)
		}
	}
	if len(rejected) > 0 {
		return nil, newSVGlideDiagnosticsError("SVGlide preflight rejected SVG input", rejected)
	}
	return pages, nil
}

func classifySVGlideSVGPage(svg, path string, pageIndex int) svgClassifiedPage {
	page := svgClassifiedPage{
		Path:    path,
		Content: svg,
		Mode:    svgClassifyNative,
	}

	if diagnostics := preflightSVGlideStaticDiagnostics(svg, path, pageIndex); len(diagnostics) > 0 {
		page.Diagnostics = diagnostics
		page.Mode = svgClassifyReject
		return page
	}

	if version := rootSVGlideContractVersion(svg); version != "" && version != svgContractVersion && declaresNativeSVGlideContent(svg) {
		diag := newSVGlideDiagnostic(
			svgDiagContractVersion,
			svgDiagSeverityError,
			path,
			pageIndex,
			fmt.Sprintf("root <svg> has unsupported %s=%q; expected %q", svgContractVersionAttr, version, svgContractVersion),
		)
		diag.AttrName = svgContractVersionAttr
		page.Diagnostics = []SVGlideDiagnostic{diag}
		page.Mode = svgClassifyReject
		return page
	}

	if err := validateSVGlideSVG(svg, path); err == nil {
		return page
	} else {
		page.Diagnostics = []SVGlideDiagnostic{{
			Code:      svgDiagNativeUnsupported,
			Severity:  svgDiagSeverityWarning,
			Path:      path,
			PageIndex: pageIndex,
			Message:   err.Error(),
		}}
	}

	if _, err := svgFallbackPageBox(svg, path, pageIndex); err != nil {
		page.Mode = svgClassifyReject
		page.Diagnostics = svglideDiagnosticsFromError(err)
		if len(page.Diagnostics) == 0 {
			page.Diagnostics = []SVGlideDiagnostic{
				newSVGlideDiagnostic(svgDiagMissingPageSize, svgDiagSeverityError, path, pageIndex, err.Error()),
			}
		}
		return page
	}

	page.Mode = svgClassifyFallback
	return page
}

func rootSVGlideContractVersion(svg string) string {
	m := svgRootOpenTagRegex.FindStringSubmatchIndex(svg)
	if m == nil {
		return ""
	}
	return xmlAttrValue(svg[m[6]:m[7]], svgContractVersionAttr)
}

func declaresNativeSVGlideContent(svg string) bool {
	for _, m := range regexp.MustCompile(`(?is)<([A-Za-z_][\w.:-]*)((?:\s[^>]*?)?)>`).FindAllStringSubmatch(svg, -1) {
		if len(m) < 3 {
			continue
		}
		tagName := m[1]
		attrs := m[2]
		switch xmlAttrValue(attrs, "slide:role") {
		case "shape":
			if svgShapeTags[tagName] {
				return true
			}
		case "image":
			if tagName == "image" {
				return true
			}
		}
	}
	return false
}

func preflightSVGlideStaticDiagnostics(svg, path string, pageIndex int) []SVGlideDiagnostic {
	m := svgRootOpenTagRegex.FindStringSubmatchIndex(svg)
	if m == nil {
		return []SVGlideDiagnostic{
			newSVGlideDiagnostic(svgDiagRootMissing, svgDiagSeverityError, path, pageIndex, "SVG root element not found"),
		}
	}
	tagName := svg[m[4]:m[5]]
	if tagName != "svg" {
		diag := newSVGlideDiagnostic(svgDiagRootUnsupported, svgDiagSeverityError, path, pageIndex, "root element must be non-namespaced <svg>")
		diag.TagName = tagName
		return []SVGlideDiagnostic{diag}
	}
	attrs := svg[m[6]:m[7]]
	var diagnostics []SVGlideDiagnostic
	if !hasXMLAttr(attrs, "xmlns:slide", svgContractNamespace) {
		diagnostics = append(diagnostics, newSVGlideDiagnostic(
			svgDiagMissingNamespace,
			svgDiagSeverityError,
			path,
			pageIndex,
			fmt.Sprintf("root <svg> must declare xmlns:slide=%q", svgContractNamespace),
		))
	}
	if !hasXMLAttr(attrs, "slide:role", "slide") {
		diagnostics = append(diagnostics, newSVGlideDiagnostic(
			svgDiagMissingSlideRole,
			svgDiagSeverityError,
			path,
			pageIndex,
			`root <svg> must include slide:role="slide"`,
		))
	}
	diagnostics = append(diagnostics, inspectSVGStaticRejectRules(svg[m[9]:], path, pageIndex)...)
	return diagnostics
}

func inspectSVGStaticRejectRules(svgAfterRootOpen, path string, pageIndex int) []SVGlideDiagnostic {
	var diagnostics []SVGlideDiagnostic
	for i := 0; i < len(svgAfterRootOpen); {
		rel := strings.IndexByte(svgAfterRootOpen[i:], '<')
		if rel < 0 {
			return diagnostics
		}
		i += rel

		switch {
		case strings.HasPrefix(svgAfterRootOpen[i:], "<!--"):
			end := strings.Index(svgAfterRootOpen[i+4:], "-->")
			if end < 0 {
				return append(diagnostics, newSVGlideDiagnostic(svgDiagMalformedElement, svgDiagSeverityError, path, pageIndex, "malformed SVG comment"))
			}
			i += 4 + end + 3
			continue
		case strings.HasPrefix(svgAfterRootOpen[i:], "<![CDATA["):
			end := strings.Index(svgAfterRootOpen[i+9:], "]]>")
			if end < 0 {
				return append(diagnostics, newSVGlideDiagnostic(svgDiagMalformedElement, svgDiagSeverityError, path, pageIndex, "malformed SVG CDATA"))
			}
			i += 9 + end + 3
			continue
		case strings.HasPrefix(svgAfterRootOpen[i:], "<?"):
			end := strings.Index(svgAfterRootOpen[i+2:], "?>")
			if end < 0 {
				return append(diagnostics, newSVGlideDiagnostic(svgDiagMalformedElement, svgDiagSeverityError, path, pageIndex, "malformed SVG processing instruction"))
			}
			i += 2 + end + 2
			continue
		case strings.HasPrefix(svgAfterRootOpen[i:], "</"):
			end := findSVGTagEnd(svgAfterRootOpen, i)
			if end < 0 {
				return append(diagnostics, newSVGlideDiagnostic(svgDiagMalformedElement, svgDiagSeverityError, path, pageIndex, "malformed SVG closing tag"))
			}
			i = end + 1
			continue
		case strings.HasPrefix(svgAfterRootOpen[i:], "<!"):
			end := findSVGTagEnd(svgAfterRootOpen, i)
			if end < 0 {
				return append(diagnostics, newSVGlideDiagnostic(svgDiagMalformedElement, svgDiagSeverityError, path, pageIndex, "malformed SVG declaration"))
			}
			i = end + 1
			continue
		}

		end := findSVGTagEnd(svgAfterRootOpen, i)
		if end < 0 {
			return append(diagnostics, newSVGlideDiagnostic(svgDiagMalformedElement, svgDiagSeverityError, path, pageIndex, "malformed SVG element"))
		}
		name, attrs, _ := parseSVGStartTag(svgAfterRootOpen[i+1 : end])
		if name == "" {
			i = end + 1
			continue
		}
		diagnostics = append(diagnostics, inspectSVGElementStaticRejectRules(path, pageIndex, name, attrs)...)
		i = end + 1
	}
	return diagnostics
}

func inspectSVGElementStaticRejectRules(path string, pageIndex int, tagName, attrs string) []SVGlideDiagnostic {
	var diagnostics []SVGlideDiagnostic
	lowerTag := strings.ToLower(tagName)
	if lowerTag == "script" {
		diag := newSVGlideDiagnostic(svgDiagDisallowedScript, svgDiagSeverityError, path, pageIndex, "<script> is not allowed in SVGlide SVG")
		diag.TagName = tagName
		diagnostics = append(diagnostics, diag)
	}
	for _, attr := range svgAttrRegex.FindAllStringSubmatch(attrs, -1) {
		if len(attr) < 5 || attr[2] != attr[4] {
			continue
		}
		name := attr[1]
		value := strings.TrimSpace(attr[3])
		lowerName := strings.ToLower(name)
		switch {
		case strings.HasPrefix(lowerName, "on"):
			diag := newSVGlideDiagnostic(svgDiagDisallowedEventAttr, svgDiagSeverityError, path, pageIndex, "event handler attributes are not allowed in SVGlide SVG")
			diag.TagName = tagName
			diag.AttrName = name
			diagnostics = append(diagnostics, diag)
		case lowerName == "href" || lowerName == "xlink:href" || lowerName == "src":
			if isHTTPURL(value) {
				diag := newSVGlideDiagnostic(svgDiagExternalReference, svgDiagSeverityError, path, pageIndex, "external http(s) references are not allowed in SVGlide SVG")
				diag.TagName = tagName
				diag.AttrName = name
				diagnostics = append(diagnostics, diag)
			}
		case lowerName == "style":
			if svgExternalURLRegex.MatchString(value) {
				diag := newSVGlideDiagnostic(svgDiagExternalReference, svgDiagSeverityError, path, pageIndex, "external http(s) style references are not allowed in SVGlide SVG")
				diag.TagName = tagName
				diag.AttrName = name
				diagnostics = append(diagnostics, diag)
			}
		}
	}
	return diagnostics
}

func hasFallbackPages(pages []svgClassifiedPage) bool {
	for _, page := range pages {
		if page.Mode == svgClassifyFallback {
			return true
		}
	}
	return false
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
	if !hasXMLAttr(attrs, "xmlns:slide", svgContractNamespace) {
		return output.ErrValidation("--file %s: root <svg> must declare xmlns:slide=\"%s\"", path, svgContractNamespace)
	}
	if !hasXMLAttr(attrs, "slide:role", "slide") {
		return output.ErrValidation("--file %s: root <svg> must include slide:role=\"slide\"", path)
	}
	if version := xmlAttrValue(attrs, svgContractVersionAttr); version != "" && version != svgContractVersion {
		return output.ErrValidation("--file %s: root <svg> has unsupported %s=%q; expected %q", path, svgContractVersionAttr, version, svgContractVersion)
	}
	if svg[m[8]:m[9]] == "/>" {
		return nil
	}
	return validateSVGlideChildren(svg[m[9]:], path)
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

func ensureSVGlideContractRootAttrs(svg string) (string, error) {
	m := svgRootOpenTagRegex.FindStringSubmatchIndex(svg)
	if m == nil {
		return "", output.ErrValidation("SVG root element not found")
	}
	attrs := svg[m[6]:m[7]]
	version := xmlAttrValue(attrs, svgContractVersionAttr)
	if version != "" && version != svgContractVersion {
		return "", output.ErrValidation("root <svg> has unsupported %s=%q; expected %q", svgContractVersionAttr, version, svgContractVersion)
	}
	if version == svgContractVersion {
		return svg, nil
	}
	insertAt := m[8]
	return svg[:insertAt] + fmt.Sprintf(` %s="%s"`, svgContractVersionAttr, svgContractVersion) + svg[insertAt:], nil
}

func validateSVGlideChildren(svgAfterRootOpen, path string) error {
	depth := 0
	skipDepth := -1
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

func validateSVGlideElement(path, tagName, attrs string) (svgValidationMode, error) {
	if svgIgnoredSubtreeTags[tagName] {
		return svgValidationSkipSubtree, nil
	}
	if tagName == "metadata" && hasXMLAttr(attrs, "data-svglide-assets", "true") {
		return svgValidationSkipSubtree, nil
	}
	if err := validateSVGlideTransform(path, tagName, attrs); err != nil {
		return svgValidationStop, err
	}
	if svgContainerTags[tagName] {
		return svgValidationDescend, nil
	}

	role := xmlAttrValue(attrs, "slide:role")
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
	return isHTTPURL(lower) ||
		strings.HasPrefix(lower, "data:")
}

func isHTTPURL(value string) bool {
	lower := strings.ToLower(strings.TrimSpace(value))
	return strings.HasPrefix(lower, "http://") || strings.HasPrefix(lower, "https://")
}

type svgFallbackBox struct {
	ViewBox string
	Width   string
	Height  string
}

func svgFallbackPageBox(svg, path string, pageIndex int) (svgFallbackBox, error) {
	m := svgRootOpenTagRegex.FindStringSubmatchIndex(svg)
	if m == nil {
		return svgFallbackBox{}, newSVGlideDiagnosticsError("SVGlide fallback page size unavailable", []SVGlideDiagnostic{
			newSVGlideDiagnostic(svgDiagRootMissing, svgDiagSeverityError, path, pageIndex, "SVG root element not found"),
		})
	}
	attrs := svg[m[6]:m[7]]
	viewBox := strings.TrimSpace(xmlAttrValue(attrs, "viewBox"))
	if viewBox != "" {
		parts := splitSVGNumberList(viewBox)
		if len(parts) == 4 && isSVGlideNumber(parts[2]) && isSVGlideNumber(parts[3]) {
			return svgFallbackBox{ViewBox: strings.Join(parts, " "), Width: stripSVGNumberUnit(parts[2]), Height: stripSVGNumberUnit(parts[3])}, nil
		}
	}

	width := strings.TrimSpace(xmlAttrValue(attrs, "width"))
	height := strings.TrimSpace(xmlAttrValue(attrs, "height"))
	if isSVGlideNumber(width) && isSVGlideNumber(height) {
		width = stripSVGNumberUnit(width)
		height = stripSVGNumberUnit(height)
		return svgFallbackBox{ViewBox: fmt.Sprintf("0 0 %s %s", width, height), Width: width, Height: height}, nil
	}

	return svgFallbackBox{}, newSVGlideDiagnosticsError("SVGlide fallback page size unavailable", []SVGlideDiagnostic{
		newSVGlideDiagnostic(svgDiagMissingPageSize, svgDiagSeverityError, path, pageIndex, "fallback SVG must include a numeric viewBox or width/height"),
	})
}

func splitSVGNumberList(value string) []string {
	raw := strings.FieldsFunc(value, func(r rune) bool {
		return r == ',' || isXMLSpace(r)
	})
	var out []string
	for _, part := range raw {
		part = strings.TrimSpace(part)
		if part != "" {
			out = append(out, part)
		}
	}
	return out
}

func stripSVGNumberUnit(value string) string {
	value = strings.TrimSpace(value)
	if strings.HasSuffix(strings.ToLower(value), "px") {
		return strings.TrimSpace(value[:len(value)-2])
	}
	return value
}

func buildSVGFallbackImageOnlyPage(svg, fileToken string) (string, error) {
	box, err := svgFallbackPageBox(svg, "", 0)
	if err != nil {
		return "", err
	}
	token := xmlEscape(fileToken)
	viewBox := xmlEscape(box.ViewBox)
	width := xmlEscape(box.Width)
	height := xmlEscape(box.Height)
	return fmt.Sprintf(
		`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="%s" slide:role="slide" %s="%s" viewBox="%s"><image slide:role="image" href="%s" x="0" y="0" width="%s" height="%s" preserveAspectRatio="none"/></svg>`,
		svgContractNamespace,
		svgContractVersionAttr,
		svgContractVersion,
		viewBox,
		token,
		width,
		height,
	), nil
}

type classifiedSVGRewriteResult struct {
	Pages          []RewrittenSVGPage
	ImagesUploaded int
	FallbackPages  int
}

type renderedSVGFallback struct {
	PNGPath string
	PNGSize int64
}

func renderSVGFallbackPages(ctx context.Context, pages []svgClassifiedPage, rasterizer svgRasterizer) (map[int]renderedSVGFallback, error) {
	rendered := map[int]renderedSVGFallback{}
	for i, page := range pages {
		if page.Mode != svgClassifyFallback {
			continue
		}
		pngPath, pngSize, err := rasterizer.Rasterize(ctx, page.Path)
		if err != nil {
			cleanupRenderedSVGFallbacks(rendered)
			return nil, err
		}
		rendered[i] = renderedSVGFallback{PNGPath: pngPath, PNGSize: pngSize}
	}
	return rendered, nil
}

func cleanupRenderedSVGFallbacks(rendered map[int]renderedSVGFallback) {
	for _, item := range rendered {
		if item.PNGPath != "" {
			_ = os.Remove(item.PNGPath)
		}
	}
}

func dryRunRewriteClassifiedSVGPages(pages []svgClassifiedPage, assets map[string]string) (classifiedSVGRewriteResult, []string, error) {
	nativeSVGs := make([]string, 0, len(pages))
	for _, page := range pages {
		if page.Mode == svgClassifyNative {
			nativeSVGs = append(nativeSVGs, page.Content)
		}
	}
	paths := extractSVGImagePlaceholderPaths(nativeSVGs, assets)
	localTokens := make(map[string]string, len(paths))
	for _, path := range paths {
		localTokens[path] = "<uploaded_file_token:" + filepath.Base(path) + ">"
	}
	tokens := mergedSVGAssetTokens(assets, localTokens)

	out := classifiedSVGRewriteResult{Pages: make([]RewrittenSVGPage, 0, len(pages))}
	uploadPaths := append([]string(nil), paths...)
	for i, page := range pages {
		switch page.Mode {
		case svgClassifyNative:
			content, usedTokens := rewriteSVGImagePlaceholdersWithTokens(page.Content, tokens)
			content, err := ensureSVGlideContractRootAttrs(content)
			if err != nil {
				return classifiedSVGRewriteResult{}, nil, err
			}
			out.Pages = append(out.Pages, RewrittenSVGPage{Content: content, Tokens: usedTokens})
		case svgClassifyFallback:
			out.FallbackPages++
			placeholder := fmt.Sprintf("<uploaded_fallback_png:page_%d>", i+1)
			content, err := buildSVGFallbackImageOnlyPage(page.Content, placeholder)
			if err != nil {
				return classifiedSVGRewriteResult{}, nil, err
			}
			out.Pages = append(out.Pages, RewrittenSVGPage{Content: content, Tokens: []string{placeholder}})
			uploadPaths = append(uploadPaths, fmt.Sprintf("<rendered_png:page_%d>", i+1))
		default:
			return classifiedSVGRewriteResult{}, nil, newSVGlideDiagnosticsError("SVGlide rejected page cannot be rewritten", page.Diagnostics)
		}
	}
	out.ImagesUploaded = len(uploadPaths)
	return out, uploadPaths, nil
}

func rewriteClassifiedSVGPages(runtime *common.RuntimeContext, presentationID string, pages []svgClassifiedPage, assets map[string]string, renderedFallbacks map[int]renderedSVGFallback) (classifiedSVGRewriteResult, error) {
	nativeSVGs := make([]string, 0, len(pages))
	for _, page := range pages {
		if page.Mode == svgClassifyNative {
			nativeSVGs = append(nativeSVGs, page.Content)
		}
	}

	paths := extractSVGImagePlaceholderPaths(nativeSVGs, assets)
	localTokens, uploaded, err := uploadSlidesPlaceholders(runtime, presentationID, paths)
	if err != nil {
		return classifiedSVGRewriteResult{ImagesUploaded: uploaded}, err
	}
	tokens := mergedSVGAssetTokens(assets, localTokens)

	out := classifiedSVGRewriteResult{
		Pages:          make([]RewrittenSVGPage, 0, len(pages)),
		ImagesUploaded: uploaded,
	}
	for i, page := range pages {
		switch page.Mode {
		case svgClassifyNative:
			content, usedTokens := rewriteSVGImagePlaceholdersWithTokens(page.Content, tokens)
			content, err := ensureSVGlideContractRootAttrs(content)
			if err != nil {
				return out, err
			}
			out.Pages = append(out.Pages, RewrittenSVGPage{Content: content, Tokens: usedTokens})
		case svgClassifyFallback:
			out.FallbackPages++
			rendered, ok := renderedFallbacks[i]
			if !ok {
				return out, newSVGlideDiagnosticsError("SVGlide fallback raster output missing", []SVGlideDiagnostic{{
					Code:      svgDiagRasterOutputMissing,
					Severity:  svgDiagSeverityError,
					Path:      page.Path,
					PageIndex: i,
					Message:   "fallback page was not pre-rendered",
				}})
			}
			fileName := filepath.Base(rendered.PNGPath)
			token, err := uploadSlidesMedia(runtime, rendered.PNGPath, fileName, rendered.PNGSize, presentationID)
			if err != nil {
				return out, err
			}
			out.ImagesUploaded++
			content, err := buildSVGFallbackImageOnlyPage(page.Content, token)
			if err != nil {
				return out, err
			}
			out.Pages = append(out.Pages, RewrittenSVGPage{Content: content, Tokens: []string{token}})
		default:
			return out, newSVGlideDiagnosticsError("SVGlide rejected page cannot be rewritten", page.Diagnostics)
		}
	}
	return out, nil
}

func parseSVGAssets(runtime *common.RuntimeContext, path string) (map[string]string, error) {
	if strings.TrimSpace(path) == "" {
		return nil, nil
	}
	data, err := cmdutil.ReadInputFile(runtime.FileIO(), path)
	if err != nil {
		return nil, common.WrapInputStatError(err, fmt.Sprintf("--assets %s", path))
	}
	var assets map[string]string
	if err := json.Unmarshal(data, &assets); err != nil {
		return nil, output.ErrValidation("--assets %s: invalid JSON object: %v", path, err)
	}
	for k, v := range assets {
		if strings.TrimSpace(k) == "" || strings.TrimSpace(v) == "" {
			return nil, output.ErrValidation("--assets %s: keys and file tokens must be non-empty strings", path)
		}
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

func rewriteSVGImagePlaceholders(runtime *common.RuntimeContext, presentationID string, svgs []string, assets map[string]string) ([]RewrittenSVGPage, int, error) {
	paths := extractSVGImagePlaceholderPaths(svgs, assets)
	localTokens, uploaded, err := uploadSlidesPlaceholders(runtime, presentationID, paths)
	if err != nil {
		return nil, uploaded, err
	}
	tokens := mergedSVGAssetTokens(assets, localTokens)
	pages := make([]RewrittenSVGPage, 0, len(svgs))
	for _, svg := range svgs {
		content, usedTokens := rewriteSVGImagePlaceholdersWithTokens(svg, tokens)
		pages = append(pages, RewrittenSVGPage{Content: content, Tokens: usedTokens})
	}
	return pages, uploaded, nil
}

func dryRunRewriteSVGImagePlaceholders(svgs []string, assets map[string]string) ([]RewrittenSVGPage, []string) {
	paths := extractSVGImagePlaceholderPaths(svgs, assets)
	localTokens := make(map[string]string, len(paths))
	for _, path := range paths {
		localTokens[path] = "<uploaded_file_token:" + filepath.Base(path) + ">"
	}
	tokens := mergedSVGAssetTokens(assets, localTokens)
	pages := make([]RewrittenSVGPage, 0, len(svgs))
	for _, svg := range svgs {
		content, usedTokens := rewriteSVGImagePlaceholdersWithTokens(svg, tokens)
		pages = append(pages, RewrittenSVGPage{Content: content, Tokens: usedTokens})
	}
	return pages, paths
}

func mergedSVGAssetTokens(assets, localTokens map[string]string) map[string]string {
	tokens := map[string]string{}
	for k, v := range assets {
		key := strings.TrimSpace(k)
		token := strings.TrimSpace(v)
		if strings.HasPrefix(key, "@") {
			key = strings.TrimSpace(strings.TrimPrefix(key, "@"))
		}
		if key != "" && token != "" {
			tokens[key] = token
		}
	}
	for k, v := range localTokens {
		tokens[k] = v
	}
	return tokens
}

func extractSVGImagePlaceholderPaths(svgs []string, assets map[string]string) []string {
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

func rewriteSVGImagePlaceholdersWithTokens(svg string, tokens map[string]string) (string, []string) {
	var used []string
	seen := map[string]bool{}
	remember := func(token string) {
		if token == "" || seen[token] {
			return
		}
		seen[token] = true
		used = append(used, token)
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
				token := tokens[path]
				if token == "" {
					return attr
				}
				remember(token)
				return fmt.Sprintf(`%shref="%s"`, prefix, xmlEscape(token))
			}
			if strings.EqualFold(name, "xlink:href") {
				if shouldTreatAsFileToken(value) {
					remember(value)
				}
				return fmt.Sprintf(`%shref="%s"`, prefix, xmlEscape(value))
			}
			if shouldTreatAsFileToken(value) {
				remember(value)
			}
			return attr
		})
	})
	return out, used
}

func svgAssetTokenForPath(assets map[string]string, path string) string {
	if len(assets) == 0 {
		return ""
	}
	if token := strings.TrimSpace(assets["@"+path]); token != "" {
		return token
	}
	return strings.TrimSpace(assets[path])
}

func shouldTreatAsFileToken(value string) bool {
	value = strings.TrimSpace(value)
	if value == "" || strings.HasPrefix(value, "@") || strings.HasPrefix(value, "#") {
		return false
	}
	lower := strings.ToLower(value)
	return !strings.HasPrefix(lower, "http://") && !strings.HasPrefix(lower, "https://") && !strings.HasPrefix(lower, "data:")
}

func injectSVGTransportAssetMetadata(svg string, tokens []string) (string, error) {
	tokens = dedupeStrings(tokens)
	if len(tokens) == 0 {
		return svg, nil
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
		var missing []string
		for _, token := range tokens {
			if !existingTokens[token] {
				missing = append(missing, token)
			}
		}
		if len(missing) == 0 {
			return svg, nil
		}
		addition := renderSVGTransportImgs(missing)
		rewritten := svgMetadataEndRegex.ReplaceAllStringFunc(block, func(end string) string {
			return addition + end
		})
		return svg[:existing[0]] + rewritten + svg[existing[1]:], nil
	}

	metadata := `<metadata data-svglide-assets="true">` + renderSVGTransportImgs(tokens) + `</metadata>`
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

func renderSVGTransportImgs(tokens []string) string {
	var b strings.Builder
	for _, token := range tokens {
		b.WriteString(`<img src="`)
		b.WriteString(xmlEscape(token))
		b.WriteString(`" />`)
	}
	return b.String()
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
