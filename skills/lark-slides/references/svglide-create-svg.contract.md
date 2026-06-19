# SVGlide Create SVG Contract

Read this file only after `svglide-svg` route admission. This is the command/API contract for `slides +create-svg`.

## Command

```bash
lark-cli slides +create-svg \
  --as user \
  --title "Deck title" \
  --file .lark-slides/plan/<deck-id>/04-svg/prepared/page-001.svg \
  --file .lark-slides/plan/<deck-id>/04-svg/prepared/page-002.svg
```

Flags:

| Flag | Contract |
|---|---|
| `--title` | presentation title; defaults to `Untitled` when omitted |
| `--file` | required, repeatable, ordered SVG page input |
| `--assets` | optional JSON mapping SVG `@path` placeholders to uploaded file tokens |
| `--dry-run` | common CLI dry-run mode; prints the create, upload, and per-page request chain |

The wrapper must build this command only after `06-check/quality-gate.json` has `status: "passed"`. The dry-run and live-create commands must consume the same ordered prepared SVG hash set.

Runner wrappers should pass repo-relative `--file` and `--assets` paths when the project lives under the CLI repository. The `+create-svg` shortcut rejects absolute input paths as unsafe. When validating an uninstalled worktree build, set `SVGLIDE_LARK_CLI_CMD` to the desired command prefix, for example:

```bash
SVGLIDE_LARK_CLI_CMD='env GOCACHE=/private/tmp/svglide-gocache go run .' \
python3 skills/lark-slides/scripts/svglide_project_runner.py run \
  .lark-slides/plan/<deck-id> \
  --until dry_run
```

## API Chain

`slides +create-svg` uses the existing XML presentation route:

```text
POST /open-apis/slides_ai/v1/xml_presentations
-> optional media uploads for local image placeholders
-> POST /open-apis/slides_ai/v1/xml_presentations/{xml_presentation_id}/slide?revision_id=-1
```

The per-page body is:

```json
{
  "slide": {
    "content": "<svg ...>...</svg>"
  }
}
```

The command does not add a new `/svg_slide` endpoint. Chart markers remain inside the SVG page content; the CLI does not call a separate chart API.

## SVG Input Contract

Each input file must be a complete SVGlide SVG page:

- root is non-namespaced `<svg>`.
- root declares `xmlns:slide="https://slides.bytedance.com/ns"`.
- root includes `slide:role="slide"` and `slide:contract-version="svglide-authoring-contract/v1"`.
- default canvas is `width="960" height="540" viewBox="0 0 960 540"`.
- rendered leaf elements use `slide:role="shape"` or `slide:role="image"`.
- text uses `foreignObject slide:role="shape" slide:shape-type="text"`.
- shape geometry attributes are explicit numbers or `px` values.
- supported shape tags are `rect`, `ellipse`, `circle`, `line`, `path`, and `foreignObject`.
- `path d` uses only `M/L/H/V/C/Q/Z` commands.
- images use local `@./path` placeholders or file tokens; external HTTP(S) and data hrefs are invalid command inputs.
- `slide:role="whiteboard"` and legacy whiteboard metadata are invalid.

## Asset Rewrite Contract

For `<image slide:role="image" href="@./assets/hero.jpg" ...>`, the CLI:

1. uploads the local asset to the target presentation unless `--assets` supplies a token,
2. rewrites the SVG image to canonical `href="file_token"`,
3. injects transport metadata:

```xml
<metadata data-svglide-assets="true"><img src="file_token" /></metadata>
```

The metadata is transport-only and is not a visible slide element.

## Chart Marker Contract

Native chart markers are root-level direct children:

```xml
<g slide:role="chart" slide:chart-ref="chart-001" x="80" y="96" width="420" height="260">
  <metadata
    data-svglide-chart="svglide-chart-inline/v1"
    data-format="svglide-chart-spec-v1"
    data-encoding="base64url-json"
    data-payload-hash="sha256:<64 hex>"
  >BASE64URL_PAYLOAD</metadata>
</g>
```

Payload is canonical JSON bytes encoded as unpadded base64url. The hash is calculated on decoded JSON bytes. MVP chart types are `bar` and `line`.

## Failure Contract

The command validates files before the first API call. After the presentation is created, image upload or later page creation can still fail. Error records must preserve the presentation id, created slide ids, uploaded image count, and failing page index when available so the run can be inspected or repaired without losing state.
