// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"context"
	"fmt"
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
	},
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if err := validateSVGFileInputs(runtime, runtime.StrArray("file")); err != nil {
			return err
		}
		if err := validateSVGRasterizeFlags(runtime); err != nil {
			return err
		}
		return validateSVGAssetsPath(runtime, runtime.Str("assets"))
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		title := effectiveTitle(runtime.Str("title"))
		dry := common.NewDryRunAPI()
		svgs, prepareReport, err := prepareSVGFilesForCreate(
			runtime,
			runtime.StrArray("file"),
			svgPrepareOptionsFromRuntime(runtime, true),
		)
		if err != nil {
			return dry.Set("error", err.Error())
		}
		assets, err := parseSVGAssets(runtime, runtime.Str("assets"))
		if err != nil {
			return dry.Set("error", err.Error())
		}
		if err := validateSVGRasterAssetConflicts(assets, prepareReport); err != nil {
			return dry.Set("error", err.Error())
		}
		pages, uploadPaths := dryRunRewriteSVGImagePlaceholders(svgs, assets)
		if prepareReport != nil {
			dry.Set("svg_rasterize_report", prepareReport)
		}

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
			content, injectErr := injectSVGTransportAssetMetadata(page.Content, page.Tokens)
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
		return dry.Set("title", title)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		title := effectiveTitle(runtime.Str("title"))
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

		presentationID, revisionID, err := createEmptyPresentation(runtime, title)
		if err != nil {
			return err
		}
		result := map[string]interface{}{
			"xml_presentation_id": presentationID,
			"title":               title,
		}
		if prepareReport != nil {
			result["svg_rasterize_report"] = prepareReport
		}
		if revisionID > 0 {
			result["revision_id"] = revisionID
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
			content, err := injectSVGTransportAssetMetadata(page.Content, page.Tokens)
			if err != nil {
				return output.Errorf(output.ExitValidation, "validation",
					"page %d/%d failed before API call: %v (presentation %s was created; %d slide(s) added; slide_ids=%s)",
					i+1, len(pages), err, presentationID, len(slideIDs), strings.Join(slideIDs, ","))
			}
			slideData, err := runtime.CallAPI(
				"POST",
				slideURL,
				map[string]interface{}{"revision_id": -1},
				buildCreateSVGBody(content),
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
