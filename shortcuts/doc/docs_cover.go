// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package doc

import (
	"context"
	"fmt"
	"io"
	"math"
	"strconv"
	"strings"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/shortcuts/common"
)

// docxDocumentAPIPath is the docx v1 document endpoint used for cover GET/PATCH.
const docxDocumentAPIPath = "/open-apis/docx/v1/documents/%s"

// resolveCoverDocumentID returns the docx document_id for cover operations.
// The cover OpenAPI (GET/PATCH /open-apis/docx/v1/documents/:document_id) only
// accepts a docx document_id. wiki/doc refs are rejected with a structured,
// actionable error — this iteration does not resolve wiki → docx.
func resolveCoverDocumentID(runtime *common.RuntimeContext) (string, error) {
	ref, err := parseDocumentRef(runtime.Str("doc"))
	if err != nil {
		return "", err
	}
	if ref.Kind != "docx" {
		return "", errs.NewValidationError(errs.SubtypeInvalidArgument,
			"--doc kind %q is not supported for cover operations; pass a docx document URL or token (the cover API needs a docx document_id)", ref.Kind).WithParam("--doc")
	}
	return ref.Token, nil
}

// parseOptionalOffset reads an optional float flag. Returns (value, present, error).
// Not provided (empty) → present=false so the caller omits the field entirely
// (no default is injected). Provided → only finite numbers pass; NaN/Inf/non-numeric
// are rejected client-side. The accepted numeric range is left to the server.
func parseOptionalOffset(runtime *common.RuntimeContext, name string) (float64, bool, error) {
	raw := strings.TrimSpace(runtime.Str(name))
	if raw == "" {
		return 0, false, nil
	}
	v, err := strconv.ParseFloat(raw, 64)
	if err != nil || math.IsNaN(v) || math.IsInf(v, 0) {
		return 0, false, errs.NewValidationError(errs.SubtypeInvalidArgument,
			"--%s must be a finite number, got %q", name, raw).WithParam("--" + name)
	}
	return v, true, nil
}

// extractCover pulls data.document.cover out of the docx document response envelope.
func extractCover(data map[string]interface{}) interface{} {
	doc, ok := data["document"].(map[string]interface{})
	if !ok {
		return nil
	}
	return doc["cover"]
}

// ---------------- cover-get ----------------

func validateCoverDoc(_ context.Context, runtime *common.RuntimeContext) error {
	_, err := resolveCoverDocumentID(runtime)
	return err
}

func dryRunCoverGet(_ context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
	id, _ := resolveCoverDocumentID(runtime)
	return common.NewDryRunAPI().
		GET(fmt.Sprintf(docxDocumentAPIPath, id)).
		Desc("OpenAPI: get document (cover in data.document.cover)").
		Set("document_id", id)
}

func executeCoverGet(_ context.Context, runtime *common.RuntimeContext) error {
	id, _ := resolveCoverDocumentID(runtime)
	data, err := doDocAPI(runtime, "GET", fmt.Sprintf(docxDocumentAPIPath, id), nil)
	if err != nil {
		return err
	}
	cover := extractCover(data)
	runtime.OutFormatRaw(map[string]interface{}{"cover": cover}, nil, func(w io.Writer) {
		if cover == nil {
			fmt.Fprintln(w, "(no cover)")
			return
		}
		if m, ok := cover.(map[string]interface{}); ok {
			fmt.Fprintf(w, "token=%v offset_ratio_x=%v offset_ratio_y=%v\n", m["token"], m["offset_ratio_x"], m["offset_ratio_y"])
		}
	})
	return nil
}

var DocsCoverGet = common.Shortcut{
	Service:     "docs",
	Command:     "+cover-get",
	Description: "Get a docx document cover image (token + offset ratios)",
	Risk:        "read",
	Scopes:      []string{"docx:document:readonly"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags: []common.Flag{
		{Name: "doc", Desc: "docx document URL or token", Required: true},
	},
	Validate: validateCoverDoc,
	DryRun:   dryRunCoverGet,
	Execute:  executeCoverGet,
}

// ---------------- cover-update ----------------

func validateCoverUpdate(_ context.Context, runtime *common.RuntimeContext) error {
	if _, err := resolveCoverDocumentID(runtime); err != nil {
		return err
	}
	if strings.TrimSpace(runtime.Str("token")) == "" {
		return errs.NewValidationError(errs.SubtypeInvalidArgument, "--token is required").WithParam("--token")
	}
	if _, _, err := parseOptionalOffset(runtime, "offset-ratio-x"); err != nil {
		return err
	}
	if _, _, err := parseOptionalOffset(runtime, "offset-ratio-y"); err != nil {
		return err
	}
	return nil
}

// buildCoverUpdateBody assembles {update_cover:{cover:{token, offset_ratio_x?, offset_ratio_y?}}}.
// Offsets are written only when explicitly provided; no default is injected so the
// server applies its existing default crop behavior when omitted.
func buildCoverUpdateBody(runtime *common.RuntimeContext) map[string]interface{} {
	cover := map[string]interface{}{"token": strings.TrimSpace(runtime.Str("token"))}
	if v, ok, _ := parseOptionalOffset(runtime, "offset-ratio-x"); ok {
		cover["offset_ratio_x"] = v
	}
	if v, ok, _ := parseOptionalOffset(runtime, "offset-ratio-y"); ok {
		cover["offset_ratio_y"] = v
	}
	return map[string]interface{}{"update_cover": map[string]interface{}{"cover": cover}}
}

func dryRunCoverUpdate(_ context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
	id, _ := resolveCoverDocumentID(runtime)
	return common.NewDryRunAPI().
		PATCH(fmt.Sprintf(docxDocumentAPIPath, id)).
		Desc("OpenAPI: update document cover").
		Body(buildCoverUpdateBody(runtime)).
		Set("document_id", id)
}

func executeCoverUpdate(_ context.Context, runtime *common.RuntimeContext) error {
	id, _ := resolveCoverDocumentID(runtime)
	data, err := doDocAPI(runtime, "PATCH", fmt.Sprintf(docxDocumentAPIPath, id), buildCoverUpdateBody(runtime))
	if err != nil {
		return err
	}
	runtime.OutFormatRaw(map[string]interface{}{"cover": extractCover(data)}, nil, func(w io.Writer) {
		fmt.Fprintln(w, "cover updated")
	})
	return nil
}

var DocsCoverUpdate = common.Shortcut{
	Service:     "docs",
	Command:     "+cover-update",
	Description: "Update a docx document cover image (token must have docx_image relation to the doc)",
	Risk:        "write",
	Scopes:      []string{"docx:document"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags: []common.Flag{
		{Name: "doc", Desc: "docx document URL or token", Required: true},
		{Name: "token", Desc: "cover image file_token; must be uploaded with docx_image relation to this doc (use `docs +media-upload --parent-type docx_image --parent-node <doc-id> --doc-id <doc-id>`); a `docs +media-insert` body image token will be rejected with a relation mismatch", Required: true},
		{Name: "offset-ratio-x", Type: "float64", Desc: "optional horizontal cover offset ratio (aligns with Docx OpenAPI document.cover.offset_ratio_x); omit to keep server default; only finite numbers accepted, range validated server-side"},
		{Name: "offset-ratio-y", Type: "float64", Desc: "optional vertical cover offset ratio (aligns with Docx OpenAPI document.cover.offset_ratio_y); omit to keep server default; only finite numbers accepted, range validated server-side"},
	},
	Validate: validateCoverUpdate,
	DryRun:   dryRunCoverUpdate,
	Execute:  executeCoverUpdate,
}

// ---------------- cover-delete ----------------

// buildCoverDeleteBody assembles {update_cover:{cover:null}} per the OpenAPI delete convention.
func buildCoverDeleteBody() map[string]interface{} {
	return map[string]interface{}{"update_cover": map[string]interface{}{"cover": nil}}
}

func dryRunCoverDelete(_ context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
	id, _ := resolveCoverDocumentID(runtime)
	return common.NewDryRunAPI().
		PATCH(fmt.Sprintf(docxDocumentAPIPath, id)).
		Desc("OpenAPI: delete document cover (cover:null)").
		Body(buildCoverDeleteBody()).
		Set("document_id", id)
}

func executeCoverDelete(_ context.Context, runtime *common.RuntimeContext) error {
	id, _ := resolveCoverDocumentID(runtime)
	data, err := doDocAPI(runtime, "PATCH", fmt.Sprintf(docxDocumentAPIPath, id), buildCoverDeleteBody())
	if err != nil {
		return err
	}
	runtime.OutFormatRaw(map[string]interface{}{"cover": extractCover(data)}, nil, func(w io.Writer) {
		fmt.Fprintln(w, "cover deleted")
	})
	return nil
}

var DocsCoverDelete = common.Shortcut{
	Service:     "docs",
	Command:     "+cover-delete",
	Description: "Delete a docx document cover image (sends cover:null)",
	Risk:        "write",
	Scopes:      []string{"docx:document"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags: []common.Flag{
		{Name: "doc", Desc: "docx document URL or token", Required: true},
	},
	Validate: validateCoverDoc,
	DryRun:   dryRunCoverDelete,
	Execute:  executeCoverDelete,
}
