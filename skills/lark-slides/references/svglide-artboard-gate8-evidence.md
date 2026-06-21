# SVGlide Artboard Gate 8 Evidence

Gate: `Gate 8: Special Cases And Fallback Coverage`

Status: `PASS`

Date: 2026-06-21

## Scope

Gate 8 covers special cases that can break the renderer/compiler boundary:

```text
unsupported Satori feature fail-fast
svglide-chart-spec-v1 chart marker
image asset binding and readback
local raster fallback island
```

## Implemented Local Evidence

New fixtures:

```text
skills/lark-slides/scripts/fixtures/svglide_artboard/gate8_special_cases/unsupported-filter.canvas-spec.json
skills/lark-slides/scripts/fixtures/svglide_artboard/gate8_special_cases/chart-spec.json
```

New evidence runner:

```text
skills/lark-slides/scripts/svglide_gate8_special_cases.py
skills/lark-slides/scripts/svglide_gate8_special_cases_test.py
```

Readback was strengthened to check source image nodes:

```text
skills/lark-slides/scripts/svglide_readback.py
skills/lark-slides/scripts/svglide_readback_test.py
```

Readback was also strengthened to reuse PPE request headers from live-create:

```text
cmd/api/api.go
cmd/api/api_test.go
skills/lark-slides/scripts/svglide_readback.py
skills/lark-slides/scripts/svglide_readback_test.py
```

Behavior:

```text
live-create request_headers.x-tt-env=ppe_pure_svg
  -> svglide_readback.py calls:
     lark-cli api GET /open-apis/slides_ai/v1/xml_presentations/{id}
     --request-header x-tt-env=ppe_pure_svg

no live-create request_headers
  -> svglide_readback.py keeps the legacy:
     lark-cli slides xml_presentations get --params ...
```

Local evidence command:

```bash
python3 skills/lark-slides/scripts/svglide_gate8_special_cases.py \
  .tmp/svglide-gate8-special-cases-r4 \
  --pretty
```

Local evidence receipt:

```text
.tmp/svglide-gate8-special-cases-r4/gate8-special-cases.json
```

Result:

```text
status: passed
case_count: 4
passed_count: 4
failed_count: 0
```

Local cases:

```text
unsupported_feature_fail_fast:
  render_failed_before_live: true
  bridge_failed_before_live: true

chart_marker_svglide_chart_spec_v1:
  preflight error_count: 0
  chart_verify_status: passed
  local readback chart_markers: passed

image_asset_binding_readback:
  injection used_count: 1
  prepare asset ref status: mapped
  local readback asset_tokens: passed
  local readback image_assets: passed

local_raster_fallback_island:
  preflight error_count: 0
  raster_fallback status: passed
  fallback bbox: 128 x 128
  file_exists: true
```

## Real Live Evidence

### PPE Deployment Used For Fresh Readback

Slide branch:

```text
worktree: /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/slide-svglide-chart-direct-snapshot
branch: feat/svglide-chart-direct-snapshot
commit: 8f682ab082f7d86ade966eb2ffc5849827b17dc5
message: fix: guard svglide chart snapshot options
```

Validation before deploy:

```text
focused Jest:
  env API=true GULUX_ENV=test ROUTE_IP=common-consul-boe.bytedance.net \
    pnpm --dir .../apps/server exec jest --config jest.config.js \
    test/svg-parser/svglide-chart-spec-export.test.ts --runInBand --silent
  result: PASS, 6 tests passed

strict single-file TypeScript:
  pnpm --dir .../apps/server exec tsc --noEmit --strict --skipLibCheck \
    --target ES2020 --module commonjs service/svglide-chart-spec.ts
  result: PASS

diff check:
  git diff --check
  result: PASS
```

PPE lane deploy:

```text
command:
  bytedcli --json tce deploy-lane \
    --env ppe_pure_svg \
    --standard-env online_cn \
    --psm creation.slide.nodeserver_pre_release \
    --flow-base prod \
    --branch feat/svglide-chart-direct-snapshot \
    --action upgrade \
    --hot-deploy

ENV ticket: 2068537756495360000
ENV status: success
ENV log_id: 20260621113326B21024A54E2E8A51E9BA
SCM version: 1.0.0.1184
SCM base commit: 8f682ab082f7d86ade966eb2ffc5849827b17dc5
TCE deployment: 362509781
TCE service id: 208677037
TCE service status: running
image_version: 1.0.0.480
main repo after deploy: ee/slide/server@1.0.0.1184
dependency conf after deploy: ee/apacana/conf@1.0.9.148
```

Deploy notes:

```text
The first corrected deploy ticket 2068535054574407680 built SCM version
1.0.0.1183 and failed during SCM compile because `viewModel` could be null in
`svglide-chart-spec.ts`.

The follow-up fix was committed as 8f682ab082f7d86ade966eb2ffc5849827b17dc5.
The second deploy built SCM version 1.0.0.1184 successfully. Hot deploy fell
back to a normal TCE deploy because the lane also had an ee/conf version diff:
1.0.8.9733 -> 1.0.9.148.
```

### Combined Live Probe

Project:

```text
.tmp/svglide-gate8-live
```

Scope:

```text
page 1: svglide-chart-spec-v1 chart marker
page 2: uploaded image asset
page 3: local raster fallback image island
```

Live receipt:

```text
.tmp/svglide-gate8-live/07-create/live-create.json
```

Result:

```text
status: passed
xml_presentation_id: J35tspvJgltBnsdJpL7chnv6n2f
slides_added: 3
slide_ids: ["pdd", "pdu", "pdR"]
images_uploaded: 2
request_headers.x-tt-env: ppe_pure_svg
url: https://www.feishu.cn/slides/J35tspvJgltBnsdJpL7chnv6n2f
```

Readback receipt:

```text
.tmp/svglide-gate8-live/08-readback/readback-check.json
```

Historical pre-deploy result:

```text
status: failed
failed_checks: ["readback_command"]
error.code: 5090000
error.message: nodeServer internal error
log_id: 20260621042348E90BA595E19D631C3BD0
```

Fresh header-aware retry:

```text
command:
  env SVGLIDE_LARK_CLI_CMD='env GOCACHE=/private/tmp/svglide-gocache HTTP_PROXY=http://127.0.0.1:8899 HTTPS_PROXY=http://127.0.0.1:8899 http_proxy=http://127.0.0.1:8899 https_proxy=http://127.0.0.1:8899 go run .' \
  python3 skills/lark-slides/scripts/svglide_readback.py \
    .tmp/svglide-gate8-live \
    --pretty

raw command inside receipt:
  env ... go run . api GET /open-apis/slides_ai/v1/xml_presentations/J35tspvJgltBnsdJpL7chnv6n2f
    --as user
    --request-header x-tt-env=ppe_pure_svg

request_headers:
  x-tt-env: ppe_pure_svg

status: failed
failed_checks: ["readback_command"]
error.code: 5090000
error.message: nodeServer internal error
log_id: 202606210441215C24A4F7B9A4D30D0AB4
revision_id in input_binding: 4
```

Fresh post-deploy readback result:

```text
command:
  env SVGLIDE_LARK_CLI_CMD='env GOCACHE=/private/tmp/svglide-gocache HTTP_PROXY=http://127.0.0.1:8899 HTTPS_PROXY=http://127.0.0.1:8899 http_proxy=http://127.0.0.1:8899 https_proxy=http://127.0.0.1:8899 go run .' \
  python3 skills/lark-slides/scripts/svglide_readback.py \
    .tmp/svglide-gate8-live \
    --pretty

status: passed
xml_presentation_id: J35tspvJgltBnsdJpL7chnv6n2f
revision_id in input_binding: 4
expected_slide_count: 3
created_slide_count: 3
page_count: passed, expected 3, actual 3
slide_order: passed, ["pdd", "pdu", "pdR"]
blank_page: passed
text_fit: passed
bounds: passed
chart_markers: passed, expected 1
image_assets: passed, expected 2
core_visible_text: passed, expected 3, missing []
failed_checks: []
```

### Chart-Only Isolation

Project:

```text
.tmp/svglide-gate8-live-chart
```

Live receipt:

```text
.tmp/svglide-gate8-live-chart/07-create/live-create.json
```

Result:

```text
status: passed
xml_presentation_id: C5fxszdjrlftMedvShmcOWtinqe
slides_added: 1
slide_ids: ["pvv"]
request_headers.x-tt-env: ppe_pure_svg
url: https://www.feishu.cn/slides/C5fxszdjrlftMedvShmcOWtinqe
```

Readback receipt:

```text
.tmp/svglide-gate8-live-chart/08-readback/readback-check.json
```

Historical pre-deploy result:

```text
status: failed
failed_checks: ["readback_command"]
error.code: 5090000
error.message: nodeServer internal error
log_id: 202606210425412E6648986B9EBE0CC571
```

Fresh header-aware retry:

```text
command:
  env SVGLIDE_LARK_CLI_CMD='env GOCACHE=/private/tmp/svglide-gocache HTTP_PROXY=http://127.0.0.1:8899 HTTPS_PROXY=http://127.0.0.1:8899 http_proxy=http://127.0.0.1:8899 https_proxy=http://127.0.0.1:8899 go run .' \
  python3 skills/lark-slides/scripts/svglide_readback.py \
    .tmp/svglide-gate8-live-chart \
    --pretty

raw command inside receipt:
  env ... go run . api GET /open-apis/slides_ai/v1/xml_presentations/C5fxszdjrlftMedvShmcOWtinqe
    --as user
    --request-header x-tt-env=ppe_pure_svg

request_headers:
  x-tt-env: ppe_pure_svg

status: failed
failed_checks: ["readback_command"]
error.code: 5090000
error.message: nodeServer internal error
log_id: 2026062104391986A0240903F18411513C
revision_id in input_binding: 2
```

Fresh post-deploy readback result:

```text
command:
  env SVGLIDE_LARK_CLI_CMD='env GOCACHE=/private/tmp/svglide-gocache HTTP_PROXY=http://127.0.0.1:8899 HTTPS_PROXY=http://127.0.0.1:8899 http_proxy=http://127.0.0.1:8899 https_proxy=http://127.0.0.1:8899 go run .' \
  python3 skills/lark-slides/scripts/svglide_readback.py \
    .tmp/svglide-gate8-live-chart \
    --pretty

status: passed
xml_presentation_id: C5fxszdjrlftMedvShmcOWtinqe
revision_id in input_binding: 2
expected_slide_count: 1
created_slide_count: 1
page_count: passed, expected 1, actual 1
slide_order: passed, ["pvv"]
blank_page: passed
text_fit: passed
bounds: passed
chart_markers: passed, expected 1
core_visible_text: passed, expected 1, missing []
failed_checks: []
```

### Image-Only Isolation

Project:

```text
.tmp/svglide-gate8-live-image
```

Live receipt:

```text
.tmp/svglide-gate8-live-image/07-create/live-create.json
```

Readback receipt:

```text
.tmp/svglide-gate8-live-image/08-readback/readback-check.json
```

Result:

```text
live_create: passed
xml_presentation_id: JAtBshUhElvhUxdb3RFc18Nknye
slides_added: 1
images_uploaded: 1
readback: passed after header-aware raw API retry
page_count: passed
slide_order: passed
image_assets: passed, expected 1
core_visible_text: passed
revision_id in input_binding: 2
```

### Raster-Fallback-Only Isolation

Project:

```text
.tmp/svglide-gate8-live-raster
```

Live receipt:

```text
.tmp/svglide-gate8-live-raster/07-create/live-create.json
```

Readback receipt:

```text
.tmp/svglide-gate8-live-raster/08-readback/readback-check.json
```

Result:

```text
live_create: passed
xml_presentation_id: Px22s6J7VlBWlcd9AXRcI0emnmh
slides_added: 1
images_uploaded: 1
readback: passed after header-aware raw API retry
page_count: passed
slide_order: passed
image_assets: passed, expected 1
core_visible_text: passed
revision_id in input_binding: 2
```

## Validation Passed

```bash
python3 -m unittest skills/lark-slides/scripts/svglide_readback_test.py
```

Result:

```text
Ran 13 tests
OK
```

```bash
python3 -m unittest skills/lark-slides/scripts/svglide_gate8_special_cases_test.py
```

Result:

```text
Ran 1 test
OK
```

```bash
python3 -m unittest discover skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
Ran 264 tests
OK
```

```bash
env GOCACHE=/private/tmp/svglide-gocache go test ./shortcuts/common ./shortcuts/slides ./cmd/api
```

Result:

```text
ok github.com/larksuite/cli/shortcuts/common
ok github.com/larksuite/cli/shortcuts/slides
ok github.com/larksuite/cli/cmd/api
```

## Current Gate 8 State

Gate 8 has reviewer PASS after the PPE deployment and fresh readback reruns.

Current closure facts:

```text
local special-case runner: passed, 4/4
image-only live/readback: passed
raster-fallback-only live/readback: passed
chart-only live/readback after ppe_pure_svg deploy: passed
combined chart + image + raster live/readback after ppe_pure_svg deploy: passed
deployed lane main repo: ee/slide/server@1.0.0.1184
```

Gate 9 can start next. This does not mean the full PLAN is complete.

Next required action:

```text
Move execution cursor to Gate 9.
Do not claim full-plan completion until Gates 9-12 also pass review.
```

## Historical Reviewer Verdict Before Service Deployment

Reviewer status:

```text
BLOCKED
```

Blocking issues:

```text
1. Gate 8 and PLAN.md require svglide-chart-spec-v1 chart marker readback.
   Chart-only live_create succeeded, but readback failed at `readback_command`
   because `xml_presentations.get` returned 5090000 nodeServer internal error.

2. Combined chart + image + raster live_create also succeeded, but combined
   readback failed with the same 5090000 error. Therefore combined Gate 8
   live/readback evidence is incomplete.

3. At review time, no already-implemented repo-local readback fix was found.
   The readback implementation only used `lark-cli slides xml_presentations get`;
   that path passed image-only and raster-only decks, but failed chart-only.

4. Post-review, a header-aware raw API readback path was added and tested. It
   still fails chart-only with 5090000 while image-only and raster-only pass.
```

Non-blocking risks:

```text
1. Image-only live readback proves an image asset exists. Exact asset token
   binding is still mainly covered by the local special-case fake readback.

2. Real readback receipt currently records numeric revision ids as null in
   `input_binding.revision_id`, which weakens traceability but is not the
   active Gate 8 blocker.
```

Reviewer-required next action:

```text
At that time, keep Gate 8 BLOCKED. Escalate or fix chart-marker readback for deck
`C5fxszdjrlftMedvShmcOWtinqe` with log_id
`202606210425412E6648986B9EBE0CC571`, or implement a supported chart-specific
readback path. Then rerun chart-only and combined Gate 8 live/readback before
proceeding.
```

## Historical Reviewer Re-Review After Header-Aware Readback

Reviewer status:

```text
BLOCKED
```

Blocking issues:

```text
1. Header-aware readback did not unblock Gate 8. Chart-only live_create passed,
   but `.tmp/svglide-gate8-live-chart/08-readback/readback-check.json` still
   fails `readback_command` with 5090000, log_id
   `2026062104391986A0240903F18411513C`.

2. Combined chart + image + raster live_create passed, but
   `.tmp/svglide-gate8-live/08-readback/readback-check.json` still fails with
   5090000, log_id `202606210441215C24A4F7B9A4D30D0AB4`.

3. Gate 8 / PLAN.md still require svglide-chart-spec-v1 chart marker readback.
   Image-only and raster-only pass through the same header-aware raw API path,
   so the remaining blocker is native chart marker readback / service behavior,
   not missing PPE header propagation.
```

Reviewer-required next action:

```text
At that time, keep Gate 8 BLOCKED. Escalate or fix readback for presentations containing
`svglide-chart-spec-v1`, or add a supported chart-specific readback path, then
rerun chart-only and combined Gate 8 live/readback before proceeding to Gate 9.
```

## Service-Side Candidate Fix Investigation

Date: 2026-06-21

Slide worktree:

```text
/Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/slide-svglide-chart-direct-snapshot
branch: feat/svglide-chart-direct-snapshot
```

Read code path:

```text
GetSXSDXml / GetSlidesSXSDXml
-> tasks/get-xml.ts builds SXSD from current blocks
-> chartService.handleXMLData(...)
-> chartService.writeChartData(...)
-> chartService.extractChartXML(...)
-> sheetSupportBlockService.GetChartLatestSnapshot(...)
-> sheetSupportBlockService.GetChartData(...)
-> ThreadTaskName.Chart2XML
```

Finding:

```text
SVGlide chart markers are created successfully as ChartEmbedBlock objects, but
readback/export expands chartToken through the generic Chart2XML worker. The
existing tests proved only chart creation and insertion; they did not prove that
the custom `svglide-chart-spec/v1` snapshot/staticData shape can be exported
back through `xml_presentations.get`.
```

## Actual PPE Readback Lane Discovery

Date: 2026-06-21

Trace command:

```bash
bytedcli log trace-tree \
  --log-id 2026062104391986A0240903F18411513C \
  --region China-North
```

Result:

```text
Full trace saved to:
/var/folders/gh/pcgh9htj0ynfb6mbvy38rtpc0000gn/T/trace-tree-2026062104391986A0240903F18411513C.json

sampling_source.psm: creation.slide.nodeserver_pre_release
sampling_source.method: GetSXSDXml
```

TCE env discovery:

```bash
bytedcli --json tce env-cascader \
  --psm creation.slide.nodeserver_pre_release
```

Relevant result:

```text
partition: CN
env: ppe
lane: ppe_pure_svg
rid: 208677037
```

Service detail:

```bash
bytedcli --json tce service get 208677037
```

Relevant result:

```text
psm: creation.slide.nodeserver_pre_release
env: ppe_pure_svg
status: running
owner: songtianyi.theo
main repo: ee/slide/server
current main repo version: 1.0.0.1149
service url: https://cloud.bytedance.net/tce/services/208677037
last deploy ticket: 360169625
```

Available main repo package check:

```bash
bytedcli --json tce service repo-info-list --service-id 208677037
```

Relevant result:

```text
latest listed ee/slide/server package: 1.0.0.1180
latest songtianyi.theo listed package: 1.0.0.1172
current ppe_pure_svg deployed package: 1.0.0.1149
no listed package contains the current local chart readback candidate fix
```

Implication:

```text
The remaining Gate 8 closure requires a real remote state change:

1. Commit/push the slide-side candidate fix. Done.
2. Build or deploy the fixed branch/package for `ee/slide/server`.
3. Upgrade TCE service `208677037`
   (`creation.slide.nodeserver_pre_release`, env/lane `ppe_pure_svg`).
4. Rerun chart-only and combined Gate 8 live/readback.
```

Slide-side deployable branch state:

```text
worktree: /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/slide-svglide-chart-direct-snapshot
branch: feat/svglide-chart-direct-snapshot
commit: 90dbcdf8e779c17ab3617868578d5566b3739dd1
message: fix: export svglide chart specs for readback
remote ref: origin/feat/svglide-chart-direct-snapshot
status: clean after push
```

Remote verification:

```bash
git -C /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/slide-svglide-chart-direct-snapshot \
  ls-remote origin refs/heads/feat/svglide-chart-direct-snapshot
```

Result:

```text
90dbcdf8e779c17ab3617868578d5566b3739dd1 refs/heads/feat/svglide-chart-direct-snapshot
```

PPE service pre-deploy check:

```bash
bytedcli --json tce service get 208677037
```

Result:

```text
service: creation.slide.nodeserver_pre_release_cn
env/lane: ppe_pure_svg
status: running
current main repo package: ee/slide/server@1.0.0.1149
candidate branch head: 90dbcdf8e779c17ab3617868578d5566b3739dd1
deploy status: not deployed yet
```

Deploy command preflight check:

```bash
bytedcli tce deploy-lane --help --debug
bytedcli env service --help --debug
bytedcli env ticket --help --debug
bytedcli --json tce deployment list --service-id 208677037 --page 1
```

Findings:

```text
`bytedcli tce deploy-lane` has no dry-run/preflight flag. Its public command
surface performs a real deploy into the target env lane.

`bytedcli env service` exposes deploy/upgrade commands, but the visible help
does not expose a no-side-effect preview for the required TCE lane upgrade.

Recent deployment history for service `208677037` shows previous `ppe_pure_svg`
updates were real finished deployments/hot deploys by `songtianyi.theo`,
including:

- deployment 360169625, 2026-06-15, update, note `[v1.0.0.1172] [Hot Deploy]`
- deployment 359608396, 2026-06-12, update, note `[v1.0.0.1157] [Hot Deploy]`
- deployment 358896617, 2026-06-10, upgrade to `ee/slide/server@1.0.0.1149`
```

Historical pre-deploy conclusion:

```text
There was no confirmed no-op deploy preflight path. At that point, the next
Gate 8 action was a real shared PPE lane change and required explicit execution
approval.
```

Historical initial deployment sequence:

```bash
bytedcli tce deploy-lane \
  --psm creation.slide.nodeserver_pre_release \
  --standard-env ppe \
  --env ppe_pure_svg \
  --branch feat/svglide-chart-direct-snapshot \
  --flow-base prod \
  --action upgrade
```

Note:

```text
This initial sequence was later corrected because `--standard-env ppe` is
invalid for this service. The successful deploy used `--standard-env online_cn`
and is recorded in the PPE deployment section above.
```

Remote-state caution:

```text
The deploy-lane command changes the shared PPE lane `ppe_pure_svg`. It should be
run only as an explicit Gate 8 verification step, then immediately followed by
fresh chart-only and combined readback receipts.
```

Candidate fix added in the slide worktree:

```text
apps/server/service/svglide-chart-spec.ts
  - added buildSVGlideChartSpecXML(snapshot, staticData)
  - converts controlled svglide-chart-spec/v1 static data into standard SXSD
    <chart><chartPlotArea/><chartData/></chart>

apps/server/service/chart.service.ts
  - in extractChartXML static-data branch, tries buildSVGlideChartSpecXML(...)
    before falling back to generic ThreadTaskName.Chart2XML

apps/server/test/svg-parser/create-by-xml-svg-dispatch.test.ts
  - keeps the existing SVG dispatch / preprocessing coverage

apps/server/test/svg-parser/svglide-chart-spec-export.test.ts
  - added a pure export test for SVGlide chart payload -> SXSD chart XML
  - added a ChartService prepareSVGlideChartSpec test proving chart specs are
    created directly through SheetSupportBlock.CreateChart
  - added a ChartService extractChartXML test proving Chart2XML worker is not
    called for SVGlide chart spec export
  - added non-SVGlide static chart coverage to ensure ordinary chart exports
    still fall back to generic Chart2XML
  - added XML/CSV escaping and snapshot-option coverage for labels, legend,
    and stacked settings
```

Validation attempted:

```bash
git -C /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/slide-svglide-chart-direct-snapshot diff --check
```

Result:

```text
passed
```

Test attempted:

```bash
pnpm --dir /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/slide-svglide-chart-direct-snapshot/apps/server test -- test/svg-parser/create-by-xml-svg-dispatch.test.ts
```

Result:

```text
failed before running tests: `jest: command not found`
reason: apps/server has package.json, but node_modules is missing in this worktree
```

Dependency bootstrap:

```text
eden-mono --help
```

Result:

```text
installed @ies/eden-monorepo@3.3.0 and pnpm 8.12.1 into the slide worktree
apps/server/node_modules/.bin/jest now exists
```

Targeted chart export Jest:

```bash
env API=true GULUX_ENV=test ROUTE_IP=common-consul-boe.bytedance.net \
  pnpm --dir /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/slide-svglide-chart-direct-snapshot/apps/server \
  exec jest --config jest.config.js test/svg-parser/svglide-chart-spec-export.test.ts \
  --runInBand --silent
```

Result:

```text
PASS test/svg-parser/svglide-chart-spec-export.test.ts
Tests: 5 passed, 5 total
Test Suites: 1 passed, 1 total
```

Existing SVG dispatch integration file after test isolation:

```bash
env API=true GULUX_ENV=test ROUTE_IP=common-consul-boe.bytedance.net \
  pnpm --dir /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/slide-svglide-chart-direct-snapshot/apps/server \
  exec jest --config jest.config.js test/svg-parser/create-by-xml-svg-dispatch.test.ts \
  --runInBand --silent
```

Result:

```text
FAIL test/svg-parser/create-by-xml-svg-dispatch.test.ts
Tests: 12 failed, 22 passed, 34 total
```

Failure character:

```text
The remaining failures are in the existing SVG dispatch integration environment:
imageBlockService.insertImage / chartBlockService.insertEmbedChart DI shape,
viewBox/cascade/style/shadow/rgba assertions. They are not counted as Gate 8
closure evidence and do not prove the PPE readback blocker is fixed.
```

Historical status before PPE deployment:

```text
At that time, Gate 8 remained BLOCKED.

The local service-side candidate fix is now proven by the focused chart export
Jest test, but it is not deployed to the PPE lane and has not been validated by
fresh chart-only/combined live_create/readback receipts.
```

Historical next required action before PPE deployment:

```text
1. Deploy or route the candidate service-side fix to the PPE readback lane.
2. Rerun chart-only Gate 8 live/readback.
3. Rerun combined chart + image + raster Gate 8 live/readback.
4. Ask reviewer subagent for a new Gate 8 verdict.
```

## Historical Reviewer Re-Review After Service-Side Candidate Fix

Reviewer status:

```text
BLOCKED
```

Blocking issues:

```text
1. Gate 8 still requires real svglide-chart-spec-v1 chart marker readback.
   There is no fresh PPE/live/readback receipt after the candidate slide-side
   fix.

2. The latest chart-only receipt still fails:
   `.tmp/svglide-gate8-live-chart/08-readback/readback-check.json`
   status failed, 5090000, log_id `2026062104391986A0240903F18411513C`.

3. The latest combined chart + image + raster receipt still fails:
   `.tmp/svglide-gate8-live/08-readback/readback-check.json`
   status failed, 5090000, log_id `202606210441215C24A4F7B9A4D30D0AB4`.

4. The focused chart export Jest now passes locally, but no fresh PPE/readback
   receipt proves that the candidate fix is active in the readback lane.
```

Reviewer evidence checked:

```text
/Users/bytedance/Downloads/PLAN.md
skills/lark-slides/references/svglide-artboard-full-plan-action.md
skills/lark-slides/references/svglide-artboard-gate8-evidence.md
slide apps/server/service/svglide-chart-spec.ts
slide apps/server/service/chart.service.ts
slide apps/server/test/svg-parser/create-by-xml-svg-dispatch.test.ts
git status / git diff --stat / git diff --check
Gate 8 readback receipts
```

Reviewer-required next action:

```text
1. Deploy or route the slide-side fix into the PPE readback lane.
2. Rerun chart-only and combined Gate 8 live/readback.
3. Request review again.
```

## Historical Reviewer Re-Review After Focused Jest And Lane Discovery

Reviewer status:

```text
BLOCKED
```

Blocking issues:

```text
1. Gate 8 still requires real svglide-chart-spec-v1 chart marker readback.
   There is no fresh chart-only or combined live/readback receipt after the
   slide-side candidate fix is deployed or routed to the PPE readback lane.

2. The latest chart-only receipt is still the old failure:
   `.tmp/svglide-gate8-live-chart/08-readback/readback-check.json`
   status failed, 5090000, log_id `2026062104391986A0240903F18411513C`.

3. The latest combined chart + image + raster receipt is still the old failure:
   `.tmp/svglide-gate8-live/08-readback/readback-check.json`
   status failed, 5090000, log_id `202606210441215C24A4F7B9A4D30D0AB4`.

4. Focused Jest proves only the local `buildSVGlideChartSpecXML` /
   `ChartService.extractChartXML` candidate path. It does not replace Gate 8
   PPE live/readback evidence.
```

Non-blocking risks:

```text
1. `create-by-xml-svg-dispatch.test.ts` still has 12 failures, currently
   classified as existing SVG dispatch integration environment / DI / style
   assertion failures, not the active Gate 8 closure blocker.

2. Image-only and raster-only readback pass, so the active risk remains native
   chart marker readback/export.
```

Reviewer-required next action:

```text
Deploy or route the slide-side fix to service `208677037`
(`creation.slide.nodeserver_pre_release`, CN/ppe/ppe_pure_svg), rerun
chart-only and combined Gate 8 live/readback, then request PASS review again.
```

## Historical Reviewer Re-Review After Commit And Push

Reviewer status:

```text
BLOCKED
```

Blocking issues:

```text
1. Gate 8 boundary is clear: the slide-side fix is committed and pushed to
   `90dbcdf8e779c17ab3617868578d5566b3739dd1`, and focused Jest passes, but
   the PPE lane has not deployed that fix.

2. TCE service `208677037` / `creation.slide.nodeserver_pre_release` /
   `ppe_pure_svg` still runs `ee/slide/server@1.0.0.1149`; deploy status is
   explicitly `not deployed yet`.

3. There is no post-deploy fresh chart-only or combined live/readback receipt.
   Existing chart-only and combined receipts remain the old 5090000 failures.
```

Reviewer-required next action:

```text
Deploy or route commit `90dbcdf8e779c17ab3617868578d5566b3739dd1` to TCE
service `208677037` on lane `ppe_pure_svg`, rerun chart-only and combined Gate
8 live/readback, then request PASS review only after fresh receipts prove chart
marker readback passes.
```

## Executor Re-Review Request After PPE Deployment

Reviewer status:

```text
PASS
```

Executor evidence ready for review:

```text
1. Gate 8 local runner still has passing special-case evidence:
   `.tmp/svglide-gate8-special-cases-r4/gate8-special-cases.json`
   status passed, 4/4 cases.

2. The slide-side fix is deployed to the actual readback lane:
   ENV ticket `2068537756495360000` status success.
   TCE deployment `362509781` status finished.
   TCE service `208677037` status running.
   Deployed main repo `ee/slide/server@1.0.0.1184`.

3. Fresh chart-only readback now passes:
   `.tmp/svglide-gate8-live-chart/08-readback/readback-check.json`
   deck `C5fxszdjrlftMedvShmcOWtinqe`, slide `pvv`,
   `chart_markers` passed, `failed_checks: []`.

4. Fresh combined readback now passes:
   `.tmp/svglide-gate8-live/08-readback/readback-check.json`
   deck `J35tspvJgltBnsdJpL7chnv6n2f`, slides `pdd`, `pdu`, `pdR`,
   `chart_markers` passed, `image_assets` passed with expected 2,
   `failed_checks: []`.
```

Reviewer-required action:

```text
Inspect the updated evidence, receipts, deployment facts, changed files, and
validation commands. Return PASS only if Gate 8 special-case and fallback
coverage is complete under PLAN.md; otherwise return BLOCKED with the exact
missing evidence.
```

## Reviewer Re-Review After PPE Deployment

Reviewer status:

```text
PASS
```

Blocking issues:

```text
None for Gate 8. The prior chart-marker readback blocker is cleared by fresh
successful chart-only and combined readback receipts.
```

Non-blocking risks:

```text
1. This PASS applies only to Gate 8. It does not mean the full PLAN is complete;
   Gates 9-12 are still pending.

2. `create-by-xml-svg-dispatch.test.ts` still has unrelated historical failures
   per evidence, but focused chart export Jest and strict single-file
   TypeScript checks pass.
```

Evidence checked:

```text
skills/lark-slides/references/svglide-artboard-full-plan-action.md
skills/lark-slides/references/svglide-artboard-gate8-evidence.md
.tmp/svglide-gate8-special-cases-r4/gate8-special-cases.json
.tmp/svglide-gate8-live-chart/08-readback/readback-check.json
.tmp/svglide-gate8-live/08-readback/readback-check.json
raw readback receipts with PPE header-aware API command
focused Jest: svglide-chart-spec-export.test.ts passed 6/6
strict single-file TypeScript check passed
slide worktree HEAD: 8f682ab082f7d86ade966eb2ffc5849827b17dc5
```

Next required action:

```text
Mark Gate 8 as DONE/PASS in the action plan, then move the execution cursor to
Gate 9. Do not claim full-plan completion until Gates 9-12 pass.
```
