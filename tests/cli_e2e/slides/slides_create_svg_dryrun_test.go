// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package slides

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	clie2e "github.com/larksuite/cli/tests/cli_e2e"
	"github.com/stretchr/testify/require"
	"github.com/tidwall/gjson"
)

func setSlidesDryRunEnv(t *testing.T) {
	t.Helper()
	t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())
	t.Setenv("LARKSUITE_CLI_APP_ID", "app")
	t.Setenv("LARKSUITE_CLI_APP_SECRET", "secret")
	t.Setenv("LARKSUITE_CLI_BRAND", "feishu")
}

func TestSlidesCreateSVGDryRunRequestShape(t *testing.T) {
	setSlidesDryRunEnv(t)

	dir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dir, "page1.svg"), []byte(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" width="1280" height="720" viewBox="0 0 1280 720"><style>.primary{fill:#123456;stroke:#654321;stroke-width:2px;filter:drop-shadow(2px 4px 8px rgba(0,0,0,.2))}</style><g><defs><filter id="shadow"><feDropShadow dx="2" dy="3" stdDeviation="5" flood-color="#000" flood-opacity=".25"/></filter></defs></g><g transform="translate(20 30)"><rect slide:role="shape" class="primary" x="0" y="0" width="320px" height="180px" filter="url(#shadow)"/></g></svg>`), 0o644))
	require.NoError(t, os.WriteFile(filepath.Join(dir, "page2.svg"), []byte(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><foreignObject slide:role="shape" slide:shape-type="text" x="80" y="80" width="320" height="80"><div xmlns="http://www.w3.org/1999/xhtml">two<br />lines</div></foreignObject></svg>`), 0o644))

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	t.Cleanup(cancel)

	result, err := clie2e.RunCmd(ctx, clie2e.Request{
		Args: []string{
			"slides", "+create-svg",
			"--file", "page1.svg",
			"--file", "page2.svg",
			"--title", "Dry SVG",
			"--dry-run",
		},
		DefaultAs: "user",
		WorkDir:   dir,
	})
	require.NoError(t, err)
	result.AssertExitCode(t, 0)

	out := result.Stdout
	require.Equal(t, "POST", gjson.Get(out, "api.0.method").String(), "stdout:\n%s", out)
	require.Equal(t, "/open-apis/slides_ai/v1/xml_presentations", gjson.Get(out, "api.0.url").String(), "stdout:\n%s", out)
	require.Equal(t, "POST", gjson.Get(out, "api.1.method").String(), "stdout:\n%s", out)
	require.Equal(t, "/open-apis/slides_ai/v1/xml_presentations/<xml_presentation_id>/slide", gjson.Get(out, "api.1.url").String(), "stdout:\n%s", out)
	require.Equal(t, "POST", gjson.Get(out, "api.2.method").String(), "stdout:\n%s", out)
	require.Equal(t, "/open-apis/slides_ai/v1/xml_presentations/<xml_presentation_id>/slide", gjson.Get(out, "api.2.url").String(), "stdout:\n%s", out)
	require.Contains(t, gjson.Get(out, "api.1.body.slide.content").String(), `<rect slide:role="shape"`, "stdout:\n%s", out)
	require.Contains(t, gjson.Get(out, "api.1.body.slide.content").String(), `<g transform="translate(20 30)">`, "stdout:\n%s", out)
	require.Contains(t, gjson.Get(out, "api.1.body.slide.content").String(), `<style>.primary`, "stdout:\n%s", out)
	require.Contains(t, gjson.Get(out, "api.1.body.slide.content").String(), `<feDropShadow`, "stdout:\n%s", out)
	require.Contains(t, gjson.Get(out, "api.2.body.slide.content").String(), `slide:shape-type="text"`, "stdout:\n%s", out)
	require.Contains(t, gjson.Get(out, "api.2.body.slide.content").String(), `<br />`, "stdout:\n%s", out)
}

func TestSlidesCreateSVGDryRunRejectsMissingChildRole(t *testing.T) {
	setSlidesDryRunEnv(t)

	dir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dir, "bad.svg"), []byte(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><rect x="80" y="80" width="320" height="180"/></svg>`), 0o644))

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	t.Cleanup(cancel)

	result, err := clie2e.RunCmd(ctx, clie2e.Request{
		Args: []string{
			"slides", "+create-svg",
			"--file", "bad.svg",
			"--dry-run",
		},
		DefaultAs: "user",
		WorkDir:   dir,
	})
	require.NoError(t, err)
	result.AssertExitCode(t, 0)
	require.Empty(t, gjson.Get(result.Stdout, "api").Array(), "stdout:\n%s", result.Stdout)
	require.Contains(t, gjson.Get(result.Stdout, "error").String(), `<rect> must include slide:role="shape" or slide:role="image"`)
}

func TestSlidesCreateSVGDryRunRejectsMissingRequiredAttribute(t *testing.T) {
	setSlidesDryRunEnv(t)

	dir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dir, "bad.svg"), []byte(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><rect slide:role="shape" x="80" y="80" height="180"/></svg>`), 0o644))

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	t.Cleanup(cancel)

	result, err := clie2e.RunCmd(ctx, clie2e.Request{
		Args: []string{
			"slides", "+create-svg",
			"--file", "bad.svg",
			"--dry-run",
		},
		DefaultAs: "user",
		WorkDir:   dir,
	})
	require.NoError(t, err)
	result.AssertExitCode(t, 0)
	require.Empty(t, gjson.Get(result.Stdout, "api").Array(), "stdout:\n%s", result.Stdout)
	require.Contains(t, gjson.Get(result.Stdout, "error").String(), `<rect slide:role="shape"> missing required attribute "width"`)
}

func TestSlidesCreateSVGDryRunRejectsInvalidNumericGeometry(t *testing.T) {
	setSlidesDryRunEnv(t)

	dir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dir, "bad.svg"), []byte(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><rect slide:role="shape" x="80" y="80" width="50%" height="180"/></svg>`), 0o644))

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	t.Cleanup(cancel)

	result, err := clie2e.RunCmd(ctx, clie2e.Request{
		Args: []string{
			"slides", "+create-svg",
			"--file", "bad.svg",
			"--dry-run",
		},
		DefaultAs: "user",
		WorkDir:   dir,
	})
	require.NoError(t, err)
	result.AssertExitCode(t, 0)
	require.Empty(t, gjson.Get(result.Stdout, "api").Array(), "stdout:\n%s", result.Stdout)
	require.Contains(t, gjson.Get(result.Stdout, "error").String(), `attribute "width" must be a number or px length`)
}

func TestSlidesCreateSVGDryRunRejectsUnsupportedPathCommand(t *testing.T) {
	setSlidesDryRunEnv(t)

	dir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dir, "bad.svg"), []byte(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" viewBox="0 0 1280 720"><path slide:role="shape" d="M0 0 A10 10 0 0 1 20 20"/></svg>`), 0o644))

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	t.Cleanup(cancel)

	result, err := clie2e.RunCmd(ctx, clie2e.Request{
		Args: []string{
			"slides", "+create-svg",
			"--file", "bad.svg",
			"--dry-run",
		},
		DefaultAs: "user",
		WorkDir:   dir,
	})
	require.NoError(t, err)
	result.AssertExitCode(t, 0)
	require.Empty(t, gjson.Get(result.Stdout, "api").Array(), "stdout:\n%s", result.Stdout)
	require.Contains(t, gjson.Get(result.Stdout, "error").String(), `unsupported path command or character "A"`)
}
