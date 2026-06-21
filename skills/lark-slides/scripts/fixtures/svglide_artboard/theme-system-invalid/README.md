Theme System P0 negative fixtures.

Each child directory is a project root for a specific failing condition:

- `unknown-color`: prepared SVG contains a color outside the active ThemeSpec.
- `low-contrast`: prepared SVG uses allowed colors but fails text contrast.
- `stale-theme-validate`: `theme-validate.json` is intentionally stale.

These fixtures are exercised by `svglide_theme_system_p0_fixture_test.py`.
