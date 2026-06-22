# Third Party Notices

This file records open-source projects referenced or used by the SVGlide artboard/Satori work.

Reference absorption means SVGlide records provenance and reimplements the usable pattern with SVGlide-owned data, templates, tokens, or renderer primitives. It does not permit embedding upstream HTML, CSS, JavaScript, screenshots, or renderer source unless a specific absorption record marks that portion as copied or adapted and carries the required notice.

## Reference Sources

| Project | Repository | License | Notice | SVGlide usage |
| --- | --- | --- | --- | --- |
| beautiful-html-templates | https://github.com/zarazhangrui/beautiful-html-templates.git | MIT | Copyright (c) 2026 Zara Zhang | Template family, layout, component, and planner-selection signal extraction. |
| ppt-master | https://github.com/hugohe3/ppt-master.git | MIT | Copyright (c) 2025-2026 Hugo He | Slide workflow, planning, visual QA, and artifact discipline reference. |
| PosterGen | https://github.com/Y-Research-SBU/PosterGen.git | MIT | Copyright (c) 2025 Y-Research @SBU | Poster-style composition and visual hierarchy reference. |
| og-images-generator | https://github.com/gracile-web/og-images-generator.git | ISC | Copyright (c) 2024 Julian Cataldo - https://www.juliancataldo.com | Renderer pipeline and OG-image generation boundary reference. |
| open-design | https://github.com/nexu-io/open-design.git | Apache-2.0 | Apache License Version 2.0 | Design-generation vocabulary and planning structure reference. |

## Runtime Dependency

| Project | Repository | License | Notice | SVGlide usage |
| --- | --- | --- | --- | --- |
| satori | https://github.com/vercel/satori.git | MPL-2.0 | Mozilla Public License Version 2.0; package author Shu Ding <g@shud.in> | External runtime dependency for HTML/CSS-like tree to SVG rendering. |

Satori must remain external to `skills/lark-slides/scripts/artboard_renderer/dist/render.mjs`. The bundle build externalizes `satori`, and the package check rejects bundled Satori markers. If a future distribution embeds Satori source or compiled Satori code, that change must first add the required MPL-2.0 source and notice handling.

## Distribution Rules

- Keep `skills/lark-slides/references/oss-source-manifest.json` updated whenever a referenced upstream project, license, HEAD, or usage type changes.
- For MIT or ISC copied/adapted portions, retain the upstream copyright notice, permission notice, and warranty disclaimer with the distributed SVGlide artifact.
- For Apache-2.0 copied/adapted portions, retain the license text and any applicable NOTICE content, and mark local modifications when required.
- For MPL-2.0 dependencies, do not bundle covered source into SVGlide artifacts unless MPL source availability and notice obligations are implemented and reviewed.
- For pure reference absorption, keep a provenance record and verify the output does not embed upstream source assets.
