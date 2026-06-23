// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/internal/validate"
	"github.com/larksuite/cli/shortcuts/common"
)

// SlidesCreateSVG creates a new Lark Slides presentation from one or more
// SVGlide SVG files by adding each page through the existing XML slide route.
var SlidesCreateSVG = common.Shortcut{
	Service:     "slides",
	Command:     "+create-svg",
	Description: "Create a Lark Slides presentation from SVG",
	Risk:        "write",
	AuthTypes:   []string{"user", "bot"},
	Scopes: []string{
		"slides:presentation:create",
		"slides:presentation:write_only",
		"docs:document.media:upload",
	},
	Flags: []common.Flag{
		{Name: "title", Desc: "presentation title"},
		{
			Name:     "file",
			Type:     "string_array",
			Required: true,
			Desc:     "SVG file path; repeat for multiple pages",
		},
		{Name: "assets", Desc: "optional assets.json path mapping SVG @path placeholders to uploaded file tokens"},
		{Name: "font-family", Desc: "optional supported font family to apply to SVGlide text; custom slide-font-* fonts are not supported"},
		{
			Name:    "svg-rasterize-effects",
			Default: "off",
			Enum:    []string{"off", "auto", "strict", "force-page"},
			Desc:    "Rasterize unsupported rich SVG effects before upload: off|auto|strict|force-page",
		},
		{
			Name:    "svg-rasterize-scale",
			Type:    "int",
			Default: "2",
			Desc:    "PNG raster scale; default 2",
		},
		{Name: "svg-rasterize-report", Desc: "optional raster report output path"},
		{Name: "ppe-profile", Default: "none", Enum: []string{"none", "ppe_pure_svg"}, Desc: "internal SVGlide PPE profile"},
		{Name: "request-header", Type: "string_array", Desc: "internal request header for SVGlide live lanes; repeat key=value, only Env=Pre_release, x-tt-env=ppe_pure_svg, x-use-ppe=1 are allowed"},
		{Name: "append-to-presentation", Desc: "existing xml_presentation_id or /slides/ URL to append SVG pages into instead of creating a new presentation"},
		{Name: "revision-id", Type: "int", Default: "-1", Desc: "presentation revision for append/add-slide calls (-1 = latest)"},
	},
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if err := validateSVGFileInputs(runtime, runtime.StrArray("file")); err != nil {
			return err
		}
		if err := validateSVGRasterizeFlags(runtime); err != nil {
			return err
		}
		if err := validateSVGAssetsPath(runtime, runtime.Str("assets")); err != nil {
			return err
		}
		if _, err := normalizeSVGFontFamily(runtime.Str("font-family")); err != nil {
			return err
		}
		if _, err := parseSVGRequestHeaders(runtime.Str("ppe-profile"), runtime.StrArray("request-header")); err != nil {
			return err
		}
		_, err := appendPresentationID(runtime.Str("append-to-presentation"))
		return err
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		title := effectiveTitle(runtime.Str("title"))
		fontFamily, err := normalizeSVGFontFamily(runtime.Str("font-family"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		requestHeaders, err := parseSVGRequestHeaders(runtime.Str("ppe-profile"), runtime.StrArray("request-header"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		appendID, err := appendPresentationID(runtime.Str("append-to-presentation"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		svgs, prepareReport, err := prepareSVGFilesForCreate(
			runtime,
			runtime.StrArray("file"),
			svgPrepareOptionsFromRuntime(runtime, true),
		)
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		assets, err := parseSVGAssets(runtime, runtime.Str("assets"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		if err := validateSVGRasterAssetConflicts(assets, prepareReport); err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		pages, uploadPaths, err := dryRunRewriteSVGImagePlaceholders(runtime, svgs, assets)
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}

		dry := common.NewDryRunAPI()
		createSteps := 1
		presentationID := "<xml_presentation_id>"
		if appendID != "" {
			createSteps = 0
			presentationID = appendID
		}
		total := createSteps + len(uploadPaths) + len(pages)
		descSuffix := ""
		if len(uploadPaths) > 0 {
			descSuffix = fmt.Sprintf(" + upload %d image(s)", len(uploadPaths))
		}
		if appendID == "" {
			dry.Desc(fmt.Sprintf("Create presentation from %d SVG page(s)%s", len(pages), descSuffix)).
				POST("/open-apis/slides_ai/v1/xml_presentations").
				Desc(fmt.Sprintf("[1/%d] Create presentation", total)).
				Body(map[string]interface{}{
					"xml_presentation": map[string]interface{}{"content": buildPresentationXML(title)},
				})
		} else {
			dry.Desc(fmt.Sprintf("Append %d SVG page(s) to presentation %s%s", len(pages), appendID, descSuffix))
		}

		for i, path := range uploadPaths {
			appendSlidesUploadDryRun(dry, path, presentationID, createSteps+i+1)
		}

		slideStepStart := createSteps + len(uploadPaths) + 1
		for i, page := range pages {
			content := page.Content
			if fontFamily != "" {
				content = applySVGlideFontFamily(content, fontFamily)
			}
			content, injectErr := injectSVGTransportAssetMetadata(content, page.Assets)
			if injectErr != nil {
				return common.NewDryRunAPI().Set("error", injectErr.Error())
			}
			dry.POST(fmt.Sprintf("/open-apis/slides_ai/v1/xml_presentations/%s/slide", presentationID)).
				Desc(fmt.Sprintf("[%d/%d] Add SVG page %d", slideStepStart+i, total, i+1)).
				Params(map[string]interface{}{"revision_id": runtime.Int("revision-id")}).
				Body(buildCreateSVGBody(content))
		}

		if appendID == "" && runtime.IsBot() {
			dry.Desc("After creation succeeds in bot mode, the CLI will also try to grant the current CLI user full_access (可管理权限) on the new presentation.")
		}
		if prepareReport != nil {
			dry.Set("svg_rasterize_report", prepareReport)
		}
		if len(requestHeaders) > 0 {
			dry.Set("request_headers", svgRequestHeadersForOutput(requestHeaders))
		}
		if fontFamily != "" {
			dry.Set("font_family", fontFamily)
		}
		if appendID != "" {
			dry.Set("append_to_presentation", appendID)
		}
		return dry.Set("title", title)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		title := effectiveTitle(runtime.Str("title"))
		fontFamily, err := normalizeSVGFontFamily(runtime.Str("font-family"))
		if err != nil {
			return err
		}
		requestHeaders, err := parseSVGRequestHeaders(runtime.Str("ppe-profile"), runtime.StrArray("request-header"))
		if err != nil {
			return err
		}
		appendID, err := appendPresentationID(runtime.Str("append-to-presentation"))
		if err != nil {
			return err
		}
		svgs, prepareReport, err := prepareSVGFilesForCreate(
			runtime,
			runtime.StrArray("file"),
			svgPrepareOptionsFromRuntime(runtime, false),
		)
		if err != nil {
			return err
		}
		assets, err := parseSVGAssets(runtime, runtime.Str("assets"))
		if err != nil {
			return err
		}
		if err := validateSVGRasterAssetConflicts(assets, prepareReport); err != nil {
			return err
		}

		presentationID := appendID
		revisionID := runtime.Int("revision-id")
		created := appendID == ""
		if created {
			presentationID, revisionID, err = createEmptyPresentationWithHeaders(runtime, title, requestHeaders)
			if err != nil {
				return err
			}
		}
		result := map[string]interface{}{
			"xml_presentation_id": presentationID,
			"title":               title,
		}
		if !created {
			result["append_to_presentation"] = presentationID
		}
		if prepareReport != nil {
			result["svg_rasterize_report"] = prepareReport
		}
		if revisionID > 0 {
			result["revision_id"] = revisionID
		}
		if len(requestHeaders) > 0 {
			result["request_headers"] = svgRequestHeadersForOutput(requestHeaders)
		}
		if fontFamily != "" {
			result["font_family"] = fontFamily
		}

		pages, uploaded, err := rewriteSVGImagePlaceholders(runtime, presentationID, svgs, assets)
		if err != nil {
			action := "was created"
			if !created {
				action = "was selected for append"
			}
			return output.Errorf(output.ExitAPI, "api_error",
				"image upload failed: %v (presentation %s %s; %d image(s) uploaded before failure)",
				err, presentationID, action, uploaded)
		}
		if uploaded > 0 {
			result["images_uploaded"] = uploaded
		}

		slideURL := fmt.Sprintf(
			"/open-apis/slides_ai/v1/xml_presentations/%s/slide",
			validate.EncodePathSegment(presentationID),
		)
		var slideIDs []string
		for i, page := range pages {
			content := page.Content
			if fontFamily != "" {
				content = applySVGlideFontFamily(content, fontFamily)
			}
			content, err := injectSVGTransportAssetMetadata(content, page.Assets)
			if err != nil {
				action := "was created"
				if !created {
					action = "was selected for append"
				}
				return output.Errorf(output.ExitValidation, "validation",
					"page %d/%d failed before API call: %v (presentation %s %s; %d slide(s) added; slide_ids=%s)",
					i+1, len(pages), err, presentationID, action, len(slideIDs), strings.Join(slideIDs, ","))
			}
			slideData, err := runtime.CallAPIWithHeaders(
				"POST",
				slideURL,
				map[string]interface{}{"revision_id": revisionID},
				buildCreateSVGBody(content),
				requestHeaders,
			)
			if err != nil {
				action := "was created"
				if !created {
					action = "was selected for append"
				}
				return output.Errorf(output.ExitAPI, "api_error",
					"page %d/%d failed: %v%s (presentation %s %s; %d slide(s) added; slide_ids=%s)",
					i+1, len(pages), err, formatSVGlideErrorSuffix(err), presentationID, action, len(slideIDs), strings.Join(slideIDs, ","))
			}
			if sid := common.GetString(slideData, "slide_id"); sid != "" {
				slideIDs = append(slideIDs, sid)
			}
			if latest := common.GetFloat(slideData, "revision_id"); latest > 0 {
				revisionID = int(latest)
				result["revision_id"] = revisionID
			}
		}

		result["slide_ids"] = slideIDs
		result["slides_added"] = len(slideIDs)
		fillPresentationResult(runtime, presentationID, result)
		runtime.Out(result, nil)
		return nil
	},
}

func appendPresentationID(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", nil
	}
	ref, err := parsePresentationRef(raw)
	if err != nil {
		return "", err
	}
	if ref.Kind != "slides" {
		return "", output.ErrValidation("--append-to-presentation must be an xml_presentation_id or /slides/ URL")
	}
	return ref.Token, nil
}

func parseSVGRequestHeaders(profile string, values []string) (http.Header, error) {
	headers := http.Header{}
	switch strings.TrimSpace(profile) {
	case "", "none":
	case "ppe_pure_svg":
		headers.Set("Env", "Pre_release")
		headers.Set("x-tt-env", "ppe_pure_svg")
		headers.Set("x-use-ppe", "1")
	default:
		return nil, output.ErrValidation("--ppe-profile must be one of none, ppe_pure_svg")
	}
	for _, raw := range values {
		item := strings.TrimSpace(raw)
		if item == "" {
			return nil, output.ErrValidation("--request-header cannot be empty")
		}
		key, value, ok := strings.Cut(item, "=")
		if !ok {
			return nil, output.ErrValidation("--request-header %q must use key=value", item)
		}
		key = strings.TrimSpace(key)
		value = strings.TrimSpace(value)
		canonicalKey, canonicalValue, ok := allowedSVGPPEHeader(key)
		if !ok || value != canonicalValue {
			return nil, output.ErrValidation("--request-header %q is not supported; allowed SVGlide PPE headers are Env=Pre_release, x-tt-env=ppe_pure_svg, x-use-ppe=1", item)
		}
		if existing := headers.Get(canonicalKey); existing != "" && existing != value {
			return nil, output.ErrValidation("--request-header %s conflicts with --ppe-profile", canonicalKey)
		}
		headers.Set(canonicalKey, value)
	}
	return headers, nil
}

func allowedSVGPPEHeader(key string) (string, string, bool) {
	switch {
	case strings.EqualFold(key, "Env"):
		return "Env", "Pre_release", true
	case strings.EqualFold(key, "x-tt-env"):
		return "x-tt-env", "ppe_pure_svg", true
	case strings.EqualFold(key, "x-use-ppe"):
		return "x-use-ppe", "1", true
	default:
		return "", "", false
	}
}

func svgRequestHeadersForOutput(headers http.Header) map[string]string {
	out := map[string]string{}
	if value := headers.Get("Env"); value != "" {
		out["Env"] = value
	}
	if value := headers.Get("x-tt-env"); value != "" {
		out["x-tt-env"] = value
	}
	if value := headers.Get("x-use-ppe"); value != "" {
		out["x-use-ppe"] = value
	}
	return out
}
