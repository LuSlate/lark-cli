# SVGlide Visual Planning

Read this file only after `svglide-svg` route admission. Shared layout guidance remains in `visual-planning.md`; this file adds SVG-specific rendering constraints.

## Layout Boxes First

Define stable boxes before writing SVG coordinates:

```text
page = 960 x 540
safe = x:48 y:40 w:864 h:460
titleBox = x:54 y:52 w:600 h:96
visualBox = x:516 y:176 w:350 h:260
notesGrid = x:54 y:430 w:760 h:48
```

Generate source from these boxes. Do not paste 1280 x 720 coordinates and only change the root viewBox.

## Text Safety

- Use `foreignObject` text with explicit `font-size`, `font-weight`, `font-family`, `color`, `line-height`, and `text-align`.
- Avoid CSS font shorthand for key text.
- Leave extra height for Chinese and mixed Chinese/English text.
- White or near-white text must sit fully on a dark backing shape.
- Circular and elliptical nodes should contain only short labels; explanations belong in separate callouts.
- Do not rely on browser wrapping or clipping to hide layout mistakes.

## SVG-Safe Geometry

- Geometry attributes must be numbers or `px`.
- Path data should use only `M/L/H/V/C/Q/Z` commands.
- Use explicit shapes, short line segments, and filled dots for important dashed routes.
- Use double shapes for critical rings instead of depending on stroked circle width.
- Bake important image opacity into the image, or use a semi-transparent shape overlay.

## Visual Advantage

Each SVG slide should show a real SVG-native advantage: path composition, dense geometry, explicit annotation layers, dashboard frames, image overlays, texture, or brand-system motifs. If the page is only title plus cards or bullets, route back to XML or redesign the page.
