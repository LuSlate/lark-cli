# SVGlide Route Admission

This file is the only SVG-specific reference that may be read before the route is known. It contains route activation rules and a private-document index only. It must not carry SVG style, recipe, fallback, parser, or readback strategy bodies.

## Activation

Activate `svglide-svg` only when at least one condition is true:

- The user explicitly asks for SVG, SVGlide, or `slides +create-svg`.
- The supplied source root is `<svg slide:role="slide">`.
- The planning file declares `route: "svglide-svg"` or `output_mode: "svglide-svg"`.

If none of these conditions is true, stay on the XML route and read only XML/SXSD planning, creation, edit, validation, and troubleshooting references.

## Allowed Before Activation

Before activation, top-level skill instructions may refer only to:

- `slides +create-svg` as the route command name.
- `svglide-route-admission.md` as this gate.
- `svg-private-manifest.json` as the private-file index.

Do not read or summarize private SVG strategy files for XML route work.

## Allowed After Activation

After activation, load SVG private files through `svg-private-manifest.json`.

Primary route entrypoints:

- `lark-slides-create-svg.md`
- `svg-protocol.md`

Private planning and validation:

- `svglide-planning-layer.md`
- `svglide-validation-checklist.md`
- `svglide-visual-planning.md`
- `svglide-asset-planning.md`

Private style and quality references:

- `style-presets.json`
- `style-presets.md`
- `svg-visual-recipes.md`
- `svg-aesthetic-review.md`

Private machine profiles and local gates:

- `safe-native-v1.profile.json`
- `svglide-plan.schema.json`
- `svg_preflight.py`
- `svglide_*` lint and preview scripts when present.

## Route Boundary

XML route documents may point to this admission gate, but must not quote or inherit private SVG strategy. If a request starts on XML and later supplies SVG route evidence, perform admission at that moment and then load private SVG files.
