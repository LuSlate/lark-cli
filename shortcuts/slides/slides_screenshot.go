// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"context"
	"encoding/base64"
	"fmt"
	"path/filepath"
	"regexp"
	"strings"

	larkcore "github.com/larksuite/oapi-sdk-go/v3/core"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/internal/validate"
	"github.com/larksuite/cli/internal/vfs"
	"github.com/larksuite/cli/shortcuts/common"
)

const defaultSlidesScreenshotDir = ".lark-slides/screenshots"

var unsafeScreenshotFileCharRegex = regexp.MustCompile(`[^A-Za-z0-9._-]+`)

// SlidesScreenshot fetches server-rendered slide screenshots and writes them to
// local files. The raw API returns Base64 image payloads; this shortcut keeps
// those payloads out of stdout so agents only see small file metadata.
var SlidesScreenshot = common.Shortcut{
	Service:     "slides",
	Command:     "+screenshot",
	Description: "Save slide screenshots to local files without printing Base64 image data",
	Risk:        "read",
	Scopes:      []string{"slides:presentation:screenshot"},
	// Only wiki URL inputs need wiki:node:read. Keep it conditional so plain
	// slides IDs/URLs do not require an unrelated wiki scope.
	ConditionalScopes: []string{"wiki:node:read"},
	AuthTypes:         []string{"user", "bot"},
	Flags: []common.Flag{
		{Name: "presentation", Desc: "xml_presentation_id, slides URL, or wiki URL that resolves to slides; list mode only"},
		{Name: "slide-id", Type: "string_array", Desc: "slide page identifier (repeat for multiple slides)"},
		{Name: "slide-number", Type: "int_array", Desc: "slide page number (repeat for multiple slides)"},
		{Name: "content", Desc: "slide XML content to render directly instead of fetching existing slides", Input: []string{common.File, common.Stdin}},
		{Name: "output-dir", Default: defaultSlidesScreenshotDir, Desc: "relative directory for saved screenshots"},
		{Name: "output-name", Desc: "file name stem for --content render output"},
	},
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		renderMode := runtime.Changed("content")
		if renderMode {
			if strings.TrimSpace(runtime.Str("content")) == "" {
				return common.FlagErrorf("--content cannot be empty")
			}
			if len(normalizeSlideIDs(runtime.StrArray("slide-id"))) > 0 || len(runtime.IntArray("slide-number")) > 0 {
				return common.FlagErrorf("--content cannot be used with --slide-id or --slide-number")
			}
			if runtime.Changed("presentation") {
				return common.FlagErrorf("--presentation cannot be used with --content")
			}
		} else {
			ref, err := parsePresentationRef(runtime.Str("presentation"))
			if err != nil {
				return err
			}
			if ref.Kind == "wiki" {
				if err := runtime.EnsureScopes([]string{"wiki:node:read"}); err != nil {
					return err
				}
			}
			if _, err := normalizeSlideNumbers(runtime.IntArray("slide-number")); err != nil {
				return err
			}
			if !hasSlideScreenshotSelector(runtime) {
				return common.FlagErrorf("--slide-id or --slide-number is required")
			}
		}
		if _, err := validateScreenshotOutputDir(runtime.Str("output-dir")); err != nil {
			return err
		}
		return nil
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		if runtime.Changed("content") {
			return dryRunRenderScreenshot(runtime)
		}
		ref, err := parsePresentationRef(runtime.Str("presentation"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		slideIDs := normalizeSlideIDs(runtime.StrArray("slide-id"))
		slideNumbers, err := normalizeSlideNumbers(runtime.IntArray("slide-number"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		if len(slideIDs) == 0 && len(slideNumbers) == 0 {
			return common.NewDryRunAPI().Set("error", "--slide-id or --slide-number is required")
		}

		presentationID := ref.Token
		dry := common.NewDryRunAPI()
		if ref.Kind == "wiki" {
			presentationID = "<resolved_slides_token>"
			dry.Desc("2-step orchestration: resolve wiki → fetch slide screenshot(s)").
				GET("/open-apis/wiki/v2/spaces/get_node").
				Desc("[1] Resolve wiki node to slides presentation").
				Params(map[string]interface{}{"token": ref.Token})
		} else {
			dry.Desc(fmt.Sprintf("Fetch %d slide screenshot(s) and save files under %s", len(slideIDs)+len(slideNumbers), runtime.Str("output-dir")))
		}
		body := map[string]interface{}{}
		if len(slideIDs) > 0 {
			body["slide_ids"] = slideIDs
		}
		if len(slideNumbers) > 0 {
			body["slide_numbers"] = slideNumbers
		}
		dry.POST(fmt.Sprintf(
			"/open-apis/slides_ai/v1/xml_presentations/%s/slide_images",
			validate.EncodePathSegment(presentationID),
		)).
			Body(body)
		return dry.Set("output_dir", runtime.Str("output-dir")).Set("base64_output", "suppressed; decoded to local files during execution")
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if runtime.Changed("content") {
			return executeRenderScreenshot(runtime)
		}
		ref, err := parsePresentationRef(runtime.Str("presentation"))
		if err != nil {
			return err
		}
		presentationID, err := resolvePresentationID(runtime, ref)
		if err != nil {
			return err
		}

		slideIDs := normalizeSlideIDs(runtime.StrArray("slide-id"))
		slideNumbers, err := normalizeSlideNumbers(runtime.IntArray("slide-number"))
		if err != nil {
			return err
		}
		if len(slideIDs) == 0 && len(slideNumbers) == 0 {
			return common.FlagErrorf("--slide-id or --slide-number is required")
		}
		outputDir := runtime.Str("output-dir")
		safeOutputDir, err := ensureScreenshotOutputDir(outputDir)
		if err != nil {
			return err
		}

		url := fmt.Sprintf(
			"/open-apis/slides_ai/v1/xml_presentations/%s/slide_images",
			validate.EncodePathSegment(presentationID),
		)
		query := larkcore.QueryParams{}
		body := map[string]interface{}{}
		if len(slideIDs) > 0 {
			body["slide_ids"] = slideIDs
		}
		if len(slideNumbers) > 0 {
			body["slide_numbers"] = slideNumbers
		}
		data, err := runtime.DoAPIJSONWithLogID("POST", url, query, body)
		if err != nil {
			return err
		}

		saved, err := saveSlideScreenshots(data, safeOutputDir)
		if err != nil {
			return err
		}
		runtime.Out(map[string]interface{}{
			"xml_presentation_id": presentationID,
			"output_dir":          outputDir,
			"screenshots":         saved,
		}, nil)
		return nil
	},
}

func dryRunRenderScreenshot(runtime *common.RuntimeContext) *common.DryRunAPI {
	content := runtime.Str("content")
	if strings.TrimSpace(content) == "" {
		return common.NewDryRunAPI().Set("error", "--content cannot be empty")
	}
	if len(normalizeSlideIDs(runtime.StrArray("slide-id"))) > 0 || len(runtime.IntArray("slide-number")) > 0 {
		return common.NewDryRunAPI().Set("error", "--content cannot be used with --slide-id or --slide-number")
	}
	if runtime.Changed("presentation") {
		return common.NewDryRunAPI().Set("error", "--presentation cannot be used with --content")
	}
	dry := common.NewDryRunAPI().Desc("Render slide XML content to a screenshot file")
	dry.POST("/open-apis/slides_ai/v1/slide_image/render").
		Body(map[string]interface{}{
			"content": fmt.Sprintf("<xml omitted; length=%d>", len(content)),
		})
	return dry.Set("output_dir", runtime.Str("output-dir")).Set("base64_output", "suppressed; decoded to local file during execution")
}

func executeRenderScreenshot(runtime *common.RuntimeContext) error {
	content := runtime.Str("content")
	if strings.TrimSpace(content) == "" {
		return common.FlagErrorf("--content cannot be empty")
	}
	if len(normalizeSlideIDs(runtime.StrArray("slide-id"))) > 0 || len(runtime.IntArray("slide-number")) > 0 {
		return common.FlagErrorf("--content cannot be used with --slide-id or --slide-number")
	}
	if runtime.Changed("presentation") {
		return common.FlagErrorf("--presentation cannot be used with --content")
	}
	outputDir := runtime.Str("output-dir")
	safeOutputDir, err := ensureScreenshotOutputDir(outputDir)
	if err != nil {
		return err
	}

	data, err := runtime.DoAPIJSONWithLogID("POST", "/open-apis/slides_ai/v1/slide_image/render", larkcore.QueryParams{}, map[string]interface{}{
		"content": content,
	})
	if err != nil {
		return err
	}
	saved, err := saveRenderedSlideScreenshot(data, safeOutputDir, runtime.Str("output-name"))
	if err != nil {
		return err
	}
	runtime.Out(map[string]interface{}{
		"output_dir":  outputDir,
		"screenshots": saved,
	}, nil)
	return nil
}

func normalizeSlideIDs(values []string) []string {
	out := make([]string, 0, len(values))
	seen := map[string]struct{}{}
	for _, v := range values {
		s := strings.TrimSpace(v)
		if s == "" {
			continue
		}
		if _, ok := seen[s]; ok {
			continue
		}
		seen[s] = struct{}{}
		out = append(out, s)
	}
	return out
}

func normalizeSlideNumbers(values []int) ([]int, error) {
	out := make([]int, 0, len(values))
	seen := map[int]struct{}{}
	for _, n := range values {
		if n < 1 {
			return nil, common.FlagErrorf("--slide-number must be a positive integer")
		}
		if _, ok := seen[n]; ok {
			continue
		}
		seen[n] = struct{}{}
		out = append(out, n)
	}
	return out, nil
}

func hasSlideScreenshotSelector(runtime *common.RuntimeContext) bool {
	return len(normalizeSlideIDs(runtime.StrArray("slide-id"))) > 0 || len(runtime.IntArray("slide-number")) > 0
}

func validateScreenshotOutputDir(outputDir string) (string, error) {
	safeProbe, err := validate.SafeOutputPath(filepath.Join(outputDir, "probe.png"))
	if err != nil {
		return "", common.FlagErrorf("--output-dir invalid: %v", err)
	}
	return filepath.Dir(safeProbe), nil
}

func ensureScreenshotOutputDir(outputDir string) (string, error) {
	safeOutputDir, err := validateScreenshotOutputDir(outputDir)
	if err != nil {
		return "", err
	}
	if err := vfs.MkdirAll(safeOutputDir, 0o755); err != nil {
		return "", output.Errorf(output.ExitAPI, "io_error", "create output directory %s: %v", outputDir, err)
	}
	return safeOutputDir, nil
}

func saveSlideScreenshots(data map[string]interface{}, outputDir string) ([]map[string]interface{}, error) {
	items := common.GetSlice(data, "slide_images")
	if len(items) == 0 {
		return nil, slidesScreenshotAPIDataError(data, "slides screenshot returned no slide_images")
	}
	saved := make([]map[string]interface{}, 0, len(items))
	for i, item := range items {
		m, ok := item.(map[string]interface{})
		if !ok {
			return nil, slidesScreenshotAPIDataError(data, "slides screenshot returned invalid slide_images[%d]", i)
		}
		item, err := saveSlideScreenshotImage(m, outputDir, "", slideScreenshotFallbackName(m, i))
		if err != nil {
			if _, ok := err.(*output.ExitError); ok {
				return nil, err
			}
			return nil, slidesScreenshotAPIDataError(data, "slides screenshot returned invalid slide_images[%d]: %v", i, err)
		}
		saved = append(saved, item)
	}
	return saved, nil
}

func saveRenderedSlideScreenshot(data map[string]interface{}, outputDir string, outputName string) ([]map[string]interface{}, error) {
	item := common.GetMap(data, "slide_image")
	if item == nil {
		return nil, slidesScreenshotAPIDataError(data, "slides render screenshot returned no slide_image")
	}
	saved, err := saveSlideScreenshotImage(item, outputDir, outputName, "rendered-slide")
	if err != nil {
		if _, ok := err.(*output.ExitError); ok {
			return nil, err
		}
		return nil, slidesScreenshotAPIDataError(data, "slides render screenshot returned invalid slide_image: %v", err)
	}
	return []map[string]interface{}{saved}, nil
}

func saveSlideScreenshotImage(item map[string]interface{}, outputDir string, outputName string, fallbackName string) (map[string]interface{}, error) {
	slideID := strings.TrimSpace(common.GetString(item, "slide_id"))
	ext, label, err := slideScreenshotFormat(item)
	if err != nil {
		if slideID != "" {
			return nil, fmt.Errorf("%v for slide %s", err, slideID)
		}
		return nil, err
	}
	encoded := strings.TrimSpace(common.GetString(item, "data"))
	if encoded == "" {
		if slideID != "" {
			return nil, fmt.Errorf("empty image data for slide %s", slideID)
		}
		return nil, fmt.Errorf("empty image data")
	}
	imageBytes, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		if slideID != "" {
			return nil, fmt.Errorf("decode screenshot for slide %s: %v", slideID, err)
		}
		return nil, fmt.Errorf("decode screenshot: %v", err)
	}
	fileBase := strings.TrimSpace(outputName)
	if fileBase == "" {
		fileBase = slideID
	}
	if fileBase == "" {
		fileBase = fallbackName
	}
	path := filepath.Join(outputDir, safeScreenshotFileName(fileBase, ext))
	if err := vfs.WriteFile(path, imageBytes, 0o644); err != nil {
		return nil, output.Errorf(output.ExitAPI, "io_error", "write screenshot %s: %v", path, err)
	}
	return map[string]interface{}{
		"slide_id":     slideID,
		"slide_number": common.GetInt(item, "slide_number"),
		"format":       label,
		"path":         path,
		"size":         len(imageBytes),
	}, nil
}

func slideScreenshotFallbackName(item map[string]interface{}, index int) string {
	if slideNumber := common.GetInt(item, "slide_number"); slideNumber > 0 {
		return fmt.Sprintf("slide-%d", slideNumber)
	}
	return fmt.Sprintf("slide-%d", index+1)
}

func slideScreenshotFormat(item map[string]interface{}) (string, string, error) {
	format := common.GetInt(item, "format")
	switch format {
	case 1:
		return "png", "png", nil
	case 2:
		return "jpg", "jpeg", nil
	default:
		return "", "", fmt.Errorf("unsupported screenshot format %d", format)
	}
}

func slidesScreenshotAPIDataError(data map[string]interface{}, format string, args ...interface{}) error {
	msg := fmt.Sprintf(format, args...)
	detail := map[string]interface{}{
		"raw_data": summarizeScreenshotAPIData(data),
	}
	if logID := strings.TrimSpace(common.GetString(data, "log_id")); logID != "" {
		detail["log_id"] = logID
	}
	return &output.ExitError{
		Code: output.ExitAPI,
		Detail: &output.ErrDetail{
			Type:    "api_error",
			Message: msg,
			Detail:  detail,
		},
	}
}

func summarizeScreenshotAPIData(v interface{}) interface{} {
	switch x := v.(type) {
	case map[string]interface{}:
		out := make(map[string]interface{}, len(x))
		for k, val := range x {
			out[k] = summarizeScreenshotAPIData(val)
		}
		return out
	case []interface{}:
		out := make([]interface{}, 0, len(x))
		for i, val := range x {
			if i >= 20 {
				out = append(out, fmt.Sprintf("<omitted %d more items>", len(x)-i))
				break
			}
			out = append(out, summarizeScreenshotAPIData(val))
		}
		return out
	case string:
		if len(x) > 512 {
			return fmt.Sprintf("<omitted string length=%d prefix=%q>", len(x), x[:64])
		}
		return x
	default:
		return x
	}
}

func safeScreenshotFileName(base string, ext string) string {
	name := unsafeScreenshotFileCharRegex.ReplaceAllString(base, "_")
	name = strings.Trim(name, "._-")
	if name == "" {
		name = "slide"
	}
	return name + "." + ext
}
