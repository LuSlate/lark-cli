# SVGlide Asset Planning

Read this file only after `svglide-svg` route admission. Shared asset metadata guidance remains in `asset-planning.md`.

## Image Policy

SVG preview work should plan rich, relevant images when the topic benefits from them. Preview image licensing uncertainty is a warning and replacement obligation, not a reason to downgrade to blank or purely decorative pages.

Record image metadata in `asset_contract`:

- `mode`: `preview` or `production`.
- `retrieval_query`: the query used or planned.
- `source_type`: public URL, local asset, generated image, screenshot, or user-provided asset.
- `source_url` or `local_path_or_href`.
- `license`: use `preview_unverified` when not confirmed.
- `usage_page`.
- `replacement_required`: true when preview rights are not confirmed.

## Source Forms

Use local placeholders when possible:

```xml
<image slide:role="image" href="@./assets/hero.jpg" x="0" y="0" width="960" height="540" />
```

`slides +create-svg` uploads local placeholders and rewrites them to file tokens. Pre-uploaded tokens can be supplied through the command's asset mapping.

HTTP(S) and data images can be useful for local preview, but live create and readback must confirm they render. Production delivery should use local placeholders or file tokens with clear rights.

## Fallbacks

Do not leave empty image boxes. If an image cannot be obtained or cannot be used, generate a visible fallback from SVG-safe shapes, labels, diagrams, or chart geometry, and record the source risk.

Avoid depending on `filter`, `mask`, `clipPath`, `pattern`, or complex remote assets for critical meaning unless the plan explicitly allows fallback or rasterization.
