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
		{Name: "request-header", Type: "string_array", Desc: "internal request header for SVGlide live lanes; repeat key=value, currently only x-tt-env=ppe_pure_svg is allowed"},
	},
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if err := validateSVGFileInputs(runtime, runtime.StrArray("file")); err != nil {
			return err
		}
		if err := validateSVGAssetsPath(runtime, runtime.Str("assets")); err != nil {
			return err
		}
		if _, err := normalizeSVGFontFamily(runtime.Str("font-family")); err != nil {
			return err
		}
		_, err := parseSVGRequestHeaders(runtime.StrArray("request-header"))
		return err
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		title := effectiveTitle(runtime.Str("title"))
		fontFamily, err := normalizeSVGFontFamily(runtime.Str("font-family"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		requestHeaders, err := parseSVGRequestHeaders(runtime.StrArray("request-header"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		svgs, err := readSVGFiles(runtime, runtime.StrArray("file"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		assets, err := parseSVGAssets(runtime, runtime.Str("assets"))
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}
		pages, uploadPaths, err := dryRunRewriteSVGImagePlaceholders(runtime, svgs, assets)
		if err != nil {
			return common.NewDryRunAPI().Set("error", err.Error())
		}

		dry := common.NewDryRunAPI()
		total := 1 + len(uploadPaths) + len(pages)
		descSuffix := ""
		if len(uploadPaths) > 0 {
			descSuffix = fmt.Sprintf(" + upload %d image(s)", len(uploadPaths))
		}
		dry.Desc(fmt.Sprintf("Create presentation from %d SVG page(s)%s", len(pages), descSuffix)).
			POST("/open-apis/slides_ai/v1/xml_presentations").
			Desc(fmt.Sprintf("[1/%d] Create presentation", total)).
			Body(map[string]interface{}{
				"xml_presentation": map[string]interface{}{"content": buildPresentationXML(title)},
			})

		for i, path := range uploadPaths {
			appendSlidesUploadDryRun(dry, path, "<xml_presentation_id>", i+2)
		}

		slideStepStart := 2 + len(uploadPaths)
		for i, page := range pages {
			content := page.Content
			if fontFamily != "" {
				content = applySVGlideFontFamily(content, fontFamily)
			}
			content, injectErr := injectSVGTransportAssetMetadata(content, page.Assets)
			if injectErr != nil {
				return common.NewDryRunAPI().Set("error", injectErr.Error())
			}
			dry.POST("/open-apis/slides_ai/v1/xml_presentations/<xml_presentation_id>/slide").
				Desc(fmt.Sprintf("[%d/%d] Add SVG page %d", slideStepStart+i, total, i+1)).
				Params(map[string]interface{}{"revision_id": -1}).
				Body(buildCreateSVGBody(content))
		}

		if runtime.IsBot() {
			dry.Desc("After creation succeeds in bot mode, the CLI will also try to grant the current CLI user full_access (可管理权限) on the new presentation.")
		}
		if len(requestHeaders) > 0 {
			dry.Set("request_headers", svgRequestHeadersForOutput(requestHeaders))
		}
		if fontFamily != "" {
			dry.Set("font_family", fontFamily)
		}
		return dry.Set("title", title)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		title := effectiveTitle(runtime.Str("title"))
		fontFamily, err := normalizeSVGFontFamily(runtime.Str("font-family"))
		if err != nil {
			return err
		}
		requestHeaders, err := parseSVGRequestHeaders(runtime.StrArray("request-header"))
		if err != nil {
			return err
		}
		svgs, err := readSVGFiles(runtime, runtime.StrArray("file"))
		if err != nil {
			return err
		}
		assets, err := parseSVGAssets(runtime, runtime.Str("assets"))
		if err != nil {
			return err
		}

		presentationID, revisionID, err := createEmptyPresentationWithHeaders(runtime, title, requestHeaders)
		if err != nil {
			return err
		}
		result := map[string]interface{}{
			"xml_presentation_id": presentationID,
			"title":               title,
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
			return output.Errorf(output.ExitAPI, "api_error",
				"image upload failed: %v (presentation %s was created; %d image(s) uploaded before failure)",
				err, presentationID, uploaded)
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
				return output.Errorf(output.ExitValidation, "validation",
					"page %d/%d failed before API call: %v (presentation %s was created; %d slide(s) added; slide_ids=%s)",
					i+1, len(pages), err, presentationID, len(slideIDs), strings.Join(slideIDs, ","))
			}
			slideData, err := runtime.CallAPIWithHeaders(
				"POST",
				slideURL,
				map[string]interface{}{"revision_id": -1},
				buildCreateSVGBody(content),
				requestHeaders,
			)
			if err != nil {
				return output.Errorf(output.ExitAPI, "api_error",
					"page %d/%d failed: %v%s (presentation %s was created; %d slide(s) added; slide_ids=%s)",
					i+1, len(pages), err, formatSVGlideErrorSuffix(err), presentationID, len(slideIDs), strings.Join(slideIDs, ","))
			}
			if sid := common.GetString(slideData, "slide_id"); sid != "" {
				slideIDs = append(slideIDs, sid)
			}
			if latest := common.GetFloat(slideData, "revision_id"); latest > 0 {
				result["revision_id"] = int(latest)
			}
		}

		result["slide_ids"] = slideIDs
		result["slides_added"] = len(slideIDs)
		fillPresentationResult(runtime, presentationID, result)
		runtime.Out(result, nil)
		return nil
	},
}

func parseSVGRequestHeaders(values []string) (http.Header, error) {
	headers := http.Header{}
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
		if !strings.EqualFold(key, "x-tt-env") {
			return nil, output.ErrValidation("--request-header %q is not supported; only x-tt-env is allowed", key)
		}
		if value != "ppe_pure_svg" {
			return nil, output.ErrValidation("--request-header x-tt-env must be ppe_pure_svg")
		}
		headers.Set("x-tt-env", value)
	}
	return headers, nil
}

func svgRequestHeadersForOutput(headers http.Header) map[string]string {
	out := map[string]string{}
	if value := headers.Get("x-tt-env"); value != "" {
		out["x-tt-env"] = value
	}
	return out
}
