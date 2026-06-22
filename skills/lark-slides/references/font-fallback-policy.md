# SVGlide Font Fallback Policy

SVGlide beautiful template families record original font families for provenance, but runtime generation must lower them to system font roles.

Allowed first-tier stacks:

- `system-sans-cjk`
- `system-sans-cjk-heavy`
- `system-sans-cjk-medium`
- `system-sans-cjk-regular`
- `system-mono`

Forbidden runtime dependencies:

- Google Fonts
- scattered `@font-face`
- custom font upload
- template-specific web font loading
