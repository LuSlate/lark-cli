# PPE Pure SVG Live Create Notes

This note is private to the `slides +create-svg` route. XML/SXSD generation must not read or rely on it.

## Route Setup

When validating `ppe_pure_svg` with the local worktree CLI, use the worktree-local binary, not a global `lark-cli`:

```bash
/path/to/worktree/./lark-cli slides +create-svg ...
```

Whistle routing needs the pre OpenAPI host plus both headers:

```text
/^https:\/\/open\.feishu\.cn\/(.*)$/ https://open.feishu-pre.cn/$1
https://open.feishu.cn/ reqHeaders://Env=Pre_release
https://open.feishu.cn/ reqHeaders://x-tt-env=ppe_pure_svg
https://open.feishu-pre.cn/ reqHeaders://Env=Pre_release
https://open.feishu-pre.cn/ reqHeaders://x-tt-env=ppe_pure_svg
/^https:\/\/accounts\.feishu\.cn\/(.*)$/ https://accounts.feishu-pre.cn/$1
```

`w2 start` / `w2 add` may require sandbox escalation because Whistle writes user-level runtime files.

## Image Token Boundary

`slides +create-svg` image transport is:

```text
create xml_presentation
-> scan SVG href="@./assets/..."
-> upload local images through /open-apis/drive/v1/medias/upload_all
-> inject <metadata data-svglide-assets="true"><img src="file_token" /></metadata>
-> replace image href with file_token
-> POST the SVG to /slides_ai/v1/xml_presentations/<id>/slide
```

Upload success does not prove the live lane can parse the image token. In the 2026-06-12 `ppe_pure_svg` smoke, pure SVG pages succeeded, but pages with uploaded image tokens failed after upload with `nodeServer internal error [5090000]`. Treat that as a slide/nodeServer image-token compatibility issue, not a local image upload failure.

## Publishing Fallback

If a live deck must be published before the image-token issue is fixed:

1. Keep the rich local HTML/image preview intact.
2. Generate a separate online-pure SVG directory.
3. Remove `<image>` and `@./assets/...` references only in that online-pure directory.
4. Replace photo regions with SVG-native gradients, paths, ribbons, overlays, and texture geometry.
5. Verify no `@./assets`, `<image>`, `uploaded_file_token`, or missing `url(#id)` refs remain.
6. Run preflight, dry-run, live create, and readback page-count verification.

Do not silently remove real images from the authoring preview. State the fallback in the final delivery and keep a follow-up item to repair the image-token lane.
