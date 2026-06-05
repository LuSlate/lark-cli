# Slides CLI E2E Coverage

## Metrics
- Denominator: 4 leaf commands
- Covered: 2
- Coverage: 50.0%

## Summary
- TestSlides_CreateWorkflowAsUser: proves the user slides workflow through `create presentation with slide as user` and `get created presentation xml as user`; creates a fresh presentation, asserts returned IDs, then reads back the XML content to prove the title and slide body persisted.
- TestSlidesCreateSVGDryRunRequestShape: locks the `slides +create-svg --dry-run` request chain and recursive SVGlide validation, including `g` containers, geometry-required leaves, `px` geometry, nested defs/filter, shadow style preservation, and `foreignObject` XHTML `<br />`.
- TestSlidesCreateSVGDryRunRejectsMissingRequiredAttribute: proves CLI blocks leaf shapes that would otherwise reach the server as `shape missing required attribute`.
- TestSlidesCreateSVGDryRunRejectsInvalidNumericGeometry: proves CLI blocks non-absolute geometry before issuing API calls.
- TestSlidesCreateSVGDryRunRejectsUnsupportedPathCommand: proves CLI blocks unsupported path commands before issuing API calls.
- TestSlidesCreateSVGWorkflowAsUser: opt-in live workflow for `slides +create-svg` (`LARKSUITE_CLI_RUN_SVGLIDE_LIVE=1`); creates a two-page SVG deck as user, asserts returned page count and IDs, then reads the presentation back.
- Blocked area: `slides +media-upload` is still uncovered because it needs a deterministic local image fixture plus XML follow-up proof that is separate from the base create/read workflow.
- Blocked area: `slides +replace-slide` has focused unit coverage but no E2E workflow yet.

## Command Table

| Status | Cmd | Type | Testcase | Key parameter shapes | Notes / uncovered reason |
| --- | --- | --- | --- | --- | --- |
| ✓ | slides +create | shortcut | slides_create_workflow_test.go::TestSlides_CreateWorkflowAsUser/create presentation with slide as user | `--title`; `--slides ["<slide ...>"]` | read back through raw slides API to prove persisted XML |
| ✓ | slides +create-svg | shortcut | slides_create_svg_dryrun_test.go::TestSlidesCreateSVGDryRunRequestShape; slides_create_svg_dryrun_test.go::TestSlidesCreateSVGDryRunRejectsMissingChildRole; slides_create_svg_dryrun_test.go::TestSlidesCreateSVGDryRunRejectsMissingRequiredAttribute; slides_create_svg_dryrun_test.go::TestSlidesCreateSVGDryRunRejectsInvalidNumericGeometry; slides_create_svg_dryrun_test.go::TestSlidesCreateSVGDryRunRejectsUnsupportedPathCommand; slides_create_svg_live_test.go::TestSlidesCreateSVGWorkflowAsUser | repeated `--file`; `--title`; `--dry-run` | dry-run proves existing `/slide` route, `slide.content`, recursive SVGlide validation, server-known hard failures, numeric geometry gates, and path command gates before API call; live is opt-in and depends on the target server lane containing the updated SVGlide parser |
| ✕ | slides +media-upload | shortcut |  | none | needs a stable local image fixture plus follow-up slide XML proof |
| ✕ | slides +replace-slide | shortcut |  | none | unit-covered shortcut; E2E workflow still pending |
