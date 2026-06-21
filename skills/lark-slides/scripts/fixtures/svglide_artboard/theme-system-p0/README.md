Theme System P0 positive fixtures.

Use these project roots to prove that ThemeSpec validation and final SVG
theme adherence can pass without relying on plan-only visual distinctness.

- `artboard-satori`: three-page cover/content/closing artboard project.
- `direct-svg`: one-page direct SVG project; it validates theme usage without
  requiring the artboard package check.

Recommended smoke commands:

```bash
python3 skills/lark-slides/scripts/svglide_theme_validate.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/artboard-satori \
  --pretty
python3 skills/lark-slides/scripts/svglide_theme_adherence.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/artboard-satori \
  --pretty
```
