# SVGlide Artboard Gate 7 Evidence

Gate: `Gate 7: P0c Live Closure`

Status: `PASS`

Date: 2026-06-21

## Scope

This gate closes the P0c live path with the real `slides +create-svg` command:

```text
dry_run -> ppe_proof -> live_create -> readback
```

The fresh evidence project is:

```text
.tmp/svglide-p0c-gate7-live6
```

## Root Cause From Earlier Blocker

Earlier Gate 7 attempts failed with:

```text
[4001000] nodeServer invalid param
slides_added: 0
```

The failed receipts are kept for audit:

```text
.tmp/svglide-p0c-gate7-live4/07-create/live-create.json
.tmp/svglide-live-probes/probe-e2e-with-header.json
.tmp/svglide-live-probes/probe-e2e-no-header.json
```

The cause was not the artboard SVG output itself. The local process was not reaching the required PPE pure-SVG service lane. The successful lane requires:

```text
Whistle capture mode
open.feishu.cn -> open.feishu-pre.cn
Env=Pre_release
x-tt-env=ppe_pure_svg
HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:8899
```

The Whistle rule is now tracked in the CLI worktree:

```text
skills/lark-slides/references/ppe-pure-svg.whistle.js
sha256: 641d01be2b2ea6b7a57a21302ee45cf10cc60d247132f50681966b88481a8487
```

## Code Changes For Gate 7

Request-scoped PPE header propagation:

```text
shortcuts/common/runner.go
shortcuts/slides/slides_create.go
shortcuts/slides/slides_create_svg.go
shortcuts/slides/slides_create_svg_test.go
```

Runner and proof integration:

```text
skills/lark-slides/scripts/svglide_project_runner.py
skills/lark-slides/scripts/svglide_project_runner_test.py
skills/lark-slides/scripts/svglide_ppe_proof.py
skills/lark-slides/scripts/svglide_ppe_proof_test.py
skills/lark-slides/scripts/svglide_readback.py
skills/lark-slides/scripts/svglide_readback_test.py
skills/lark-slides/scripts/fixtures/svglide_artboard/p0c-live/07-create/ppe-proof.input.json
```

Implemented behavior:

```text
ppe-proof.input.json
  -> validates quality_gate and dry_run hashes
  -> validates Whistle proxy/capture/rule hash/injected headers
  -> ppe-proof.json
  -> runner live_create command
  -> slides +create-svg --request-header x-tt-env=ppe_pure_svg
  -> RuntimeContext.CallAPIWithHeaders
  -> presentation create and slide add API calls
```

Readback now checks:

```text
created slide count
actual readback page count from xml_presentation.content
created slide order
blank page markers
text-fit and bounds markers
CanvasSpec visible text fragments
```

## Fresh P0c Command

```bash
SVGLIDE_LARK_CLI_CMD="env GOCACHE=/private/tmp/svglide-gocache HTTP_PROXY=http://127.0.0.1:8899 HTTPS_PROXY=http://127.0.0.1:8899 http_proxy=http://127.0.0.1:8899 https_proxy=http://127.0.0.1:8899 go run ." \
python3 skills/lark-slides/scripts/svglide_project_runner.py run \
  .tmp/svglide-p0c-gate7-live6 \
  --until readback \
  --network-policy fixture \
  --asset-provider none \
  --image-backend none
```

Result:

```text
current_stage: readback
dry_run: passed
ppe_proof: passed
live_create: passed
readback: passed
```

## PPE Proof Receipt

Receipt:

```text
.tmp/svglide-p0c-gate7-live6/07-create/ppe-proof.json
```

Key evidence:

```text
status: passed
quality_gate_sha256: 072996e2b8a2c84d6d0efae0e0e23659438d7b8d1d129de3d520b40c13511844
dry_run_sha256: 9886b4fbc0d039827eca6bca99d5e8f7ddfe69ac20c78f9a8c30afc9cb713bd0
proxy.mode: whistle
proxy.capture: true
proxy.http_proxy: http://127.0.0.1:8899
proxy.https_proxy: http://127.0.0.1:8899
proxy.rewrite_host: open.feishu-pre.cn
proxy.rule_file: skills/lark-slides/references/ppe-pure-svg.whistle.js
proxy.rule_sha256: 641d01be2b2ea6b7a57a21302ee45cf10cc60d247132f50681966b88481a8487
proxy.inject_headers.Env: Pre_release
proxy.inject_headers.x-tt-env: ppe_pure_svg
headers.x-tt-env: ppe_pure_svg
summary.error_count: 0
```

## Live Create Receipt

Receipt:

```text
.tmp/svglide-p0c-gate7-live6/07-create/live-create.json
```

Key evidence:

```text
status: passed
returncode: 0
xml_presentation_id: MPcnsjAH5l5r2edcpWYcNhFVnVd
slides_added: 3
slide_ids: ["pbb", "pbu", "pbe"]
revision_id: 4
request_headers.x-tt-env: ppe_pure_svg
url: https://www.feishu.cn/slides/MPcnsjAH5l5r2edcpWYcNhFVnVd
```

Prepared SVG hashes were recorded in the live receipt:

```text
04-svg/prepared/page-001.svg: 6d35ebfe7ec500472a9fd5ab69af230d1a73aea40b2f5f6bc6f02f5a58a0900f
04-svg/prepared/page-002.svg: 9c623b3138cab6f0dcf68fb3cdfc68e9747f11ef5a8ba9f048a7a2360524e799
04-svg/prepared/page-003.svg: 13d7fc19310ac89a699f1fdf85597628b1a8428aa55468262c9a920644bf4e24
```

## Readback Receipt

Receipt:

```text
.tmp/svglide-p0c-gate7-live6/08-readback/readback-check.json
```

Key evidence:

```text
status: passed
xml_presentation_id: MPcnsjAH5l5r2edcpWYcNhFVnVd
expected_slide_count: 3
created_slide_count: 3
page_count: passed, expected 3, actual 3
slide_ids: passed, actual 3
slide_order: passed, expected ["pbb", "pbu", "pbe"], actual ["pbb", "pbu", "pbe"]
blank_page: passed
text_fit: passed
bounds: passed
core_visible_text: passed, expected 22, missing []
failed_checks: []
```

Raw readback content was saved at:

```text
.tmp/svglide-p0c-gate7-live6/08-readback/xml-presentations-get.json
```

## Validation Passed

```bash
python3 -m unittest skills/lark-slides/scripts/svglide_ppe_proof_test.py
```

Result:

```text
Ran 4 tests
OK
```

```bash
python3 -m unittest skills/lark-slides/scripts/svglide_readback_test.py
```

Result:

```text
Ran 9 tests
OK
```

```bash
python3 -m unittest skills/lark-slides/scripts/svglide_project_runner_test.py
```

Result:

```text
Ran 36 tests
OK
```

```bash
python3 -m unittest discover skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
Ran 259 tests
OK
```

```bash
env GOCACHE=/private/tmp/svglide-gocache go test ./shortcuts/common ./shortcuts/slides
```

Result:

```text
ok github.com/larksuite/cli/shortcuts/common
ok github.com/larksuite/cli/shortcuts/slides
```

## Reviewer Decision Needed

Reviewer verdict:

```text
Verdict: PASS
Blocking issues: None.
```

Gate 7 is accepted because the reviewer confirmed:

```text
1. The PPE lane proof is explicit enough and hash-bound.
2. The fresh P0c run used real lark-cli/go run, not fake dry-run.
3. live_create created 3 pages.
4. readback proves page count, page order, nonblank pages, and core CanvasSpec visible text.
5. The earlier blocker is resolved by the documented Whistle/PPE lane setup.
```
