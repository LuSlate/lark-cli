// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	clie2e "github.com/larksuite/cli/tests/cli_e2e"
	"github.com/stretchr/testify/require"
	"github.com/tidwall/gjson"
)

func TestSlidesCreateSVGWorkflowAsUser(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	t.Cleanup(cancel)

	if os.Getenv("LARKSUITE_CLI_RUN_SVGLIDE_LIVE") != "1" {
		t.Skip("set LARKSUITE_CLI_RUN_SVGLIDE_LIVE=1 to run the live SVGlide service contract test")
	}
	clie2e.SkipWithoutUserToken(t)

	dir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dir, "page1.svg"), []byte(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" width="1280" height="720" viewBox="0 0 1280 720"><g fill="#E8EEF8" transform="translate(80 80)"><rect slide:role="shape" x="0" y="0" width="360" height="180"/></g></svg>`), 0o644))
	require.NoError(t, os.WriteFile(filepath.Join(dir, "page2.svg"), []byte(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><foreignObject slide:role="shape" slide:shape-type="text" x="120" y="120" width="420" height="100"><p xmlns="http://www.w3.org/1999/xhtml">SVGlide live E2E</p></foreignObject></svg>`), 0o644))

	parentT := t
	title := "svglide-e2e-" + clie2e.GenerateSuffix()
	var presentationID string

	t.Run("create SVG deck as user", func(t *testing.T) {
		result, err := clie2e.RunCmd(ctx, clie2e.Request{
			Args: []string{
				"slides", "+create-svg",
				"--file", "page1.svg",
				"--file", "page2.svg",
				"--title", title,
			},
			DefaultAs: "user",
			WorkDir:   dir,
		})
		require.NoError(t, err)
		if result.ExitCode != 0 {
			if created := extractSVGlideFailurePresentationID(result.Stderr); created != "" {
				presentationID = created
				registerSlidesCleanup(parentT, presentationID)
			}
		}
		result.AssertExitCode(t, 0)
		result.AssertStdoutStatus(t, true)

		presentationID = gjson.Get(result.Stdout, "data.xml_presentation_id").String()
		require.NotEmpty(t, presentationID, "stdout:\n%s", result.Stdout)
		require.Equal(t, title, gjson.Get(result.Stdout, "data.title").String(), "stdout:\n%s", result.Stdout)
		require.Equal(t, int64(2), gjson.Get(result.Stdout, "data.slides_added").Int(), "stdout:\n%s", result.Stdout)
		require.Len(t, gjson.Get(result.Stdout, "data.slide_ids").Array(), 2, "stdout:\n%s", result.Stdout)

		registerSlidesCleanup(parentT, presentationID)
	})

	t.Run("read back SVG-created presentation as user", func(t *testing.T) {
		require.NotEmpty(t, presentationID, "presentation should be created before readback")

		result, err := clie2e.RunCmd(ctx, clie2e.Request{
			Args:      []string{"api", "get", "/open-apis/slides_ai/v1/xml_presentations/" + presentationID},
			DefaultAs: "user",
			Params:    map[string]any{"revision_id": -1},
		})
		require.NoError(t, err)
		result.AssertExitCode(t, 0)
		result.AssertStdoutStatus(t, 0)

		require.Equal(t, presentationID, gjson.Get(result.Stdout, "data.xml_presentation.presentation_id").String(), "stdout:\n%s", result.Stdout)
		content := gjson.Get(result.Stdout, "data.xml_presentation.content").String()
		require.Contains(t, content, "<title>"+title+"</title>", "stdout:\n%s", result.Stdout)
	})
}

func registerSlidesCleanup(t *testing.T, presentationID string) {
	t.Helper()
	t.Cleanup(func() {
		cleanupCtx, cancel := clie2e.CleanupContext()
		defer cancel()

		deleteResult, deleteErr := clie2e.RunCmd(cleanupCtx, clie2e.Request{
			Args: []string{
				"drive", "+delete",
				"--file-token", presentationID,
				"--type", "slides",
				"--yes",
			},
			DefaultAs: "user",
		})
		clie2e.ReportCleanupFailure(t, "delete presentation "+presentationID, deleteResult, deleteErr)
	})
}

func extractSVGlideFailurePresentationID(stderr string) string {
	const marker = "presentation "
	idx := strings.Index(stderr, marker)
	if idx < 0 {
		return ""
	}
	rest := stderr[idx+len(marker):]
	end := strings.IndexByte(rest, ' ')
	if end < 0 {
		return ""
	}
	return strings.Trim(rest[:end], ".,;:)")
}
