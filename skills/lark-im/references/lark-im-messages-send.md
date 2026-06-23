# im +messages-send

> **Prerequisite:** Read [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) first for authentication, global parameters, and safety rules.

Send a message to a group chat (`--chat-id oc_xxx`) or a direct message (`--user-id ou_xxx`). One step, supports `--as user` and `--as bot` (default `bot`). Maps to shortcut `lark-cli im +messages-send` (`POST /open-apis/im/v1/messages`).

## Safety Constraints

Messages sent by this tool are visible to other people. Before calling it, you **must** confirm with the user:

1. The recipient (which person or which group)
2. The message content
3. The sending identity (user or bot)

**Do not** send messages without explicit user approval.

- `--as bot` (TAT, scope `im:message:send_as_bot`): the message is sent in the app's name — the app must already be in the target chat or have a DM relationship with the target user.
- `--as user` (UAT, scopes `im:message.send_as_user` + `im:message`): the message is sent as the authorized end user.

## Choose The Right Content Flag

| Content | Flag | Why |
|---|---|---|
| Headings, lists, links, summaries, reports (lightweight formatting) | `--markdown` | Best default; converted to Feishu `post` JSON |
| Exact plain text — logs, code, indentation, literal Markdown chars that must **not** render | `--text` | Preserves literal text; no conversion |
| Exact `post` JSON, a `post` title, multiple locales, cards (`interactive`), `share_*`, or unsupported structures | `--content` | You provide the final JSON; it must match the effective `--msg-type` |
| Image / file / video / audio | `--image` / `--file` / `--video` / `--audio` | Uploads URLs or cwd-relative local files automatically |

These content flags (and the media flags) are **mutually exclusive** — pass exactly one. Media flags are also mutually exclusive with each other.

## `--markdown` Gotchas

`--markdown` always forces `msg_type=post` (single `zh_cn` locale) and normalizes input for Feishu post rendering. Key boundaries (not full CommonMark/GFM):

- **No `post` title** — if you need one, use `--content` with `post` JSON.
- **Headings rewritten**: `# Title` → `#### Title`; `##`–`######` normalized to `#####` when content has H1–H3. Code blocks preserved; excess blank lines compressed.
- **Images**: pre-upload via `im images create` and reference `![alt](img_xxx)` for reliable results. Remote `https://` URLs are auto-downloaded+uploaded at runtime (removed with a warning if that fails). Local paths in `![x](./a.png)` are **not** supported and will not auto-upload.

## Preserving Exact Formatting

For multi-line text, indentation, code blocks, tabs, or many backslashes/quotes, use shell ANSI-C quoting `$'...'` so `\n` is written explicitly. Use `--text` + `$'...'` when the receiver must see the text exactly as entered:

```bash
lark-cli im +messages-send --chat-id oc_xxx --text $'Build failed\nBranch: feature/x\nAction: check logs'
```

## Commands

```bash
# Formatted update (Markdown → post)
lark-cli im +messages-send --chat-id oc_xxx --markdown $'## Update\n\n- item 1\n- item 2'

# Plain one-line text
lark-cli im +messages-send --chat-id oc_xxx --text "Hello"

# Direct message (pass open_id)
lark-cli im +messages-send --user-id ou_xxx --text "Hello"

# Exact post structure with a title
lark-cli im +messages-send --chat-id oc_xxx --msg-type post --content '{"zh_cn":{"title":"Title","content":[[{"tag":"text","text":"Body"}]]}}'

# Markdown with an image (pre-upload first)
lark-cli im images create --data '{"image_type":"message"}' --file ./diagram.png   # -> {"image_key":"img_v3_xxxx"}
lark-cli im +messages-send --chat-id oc_xxx --markdown $'## Report\n\n![diagram](img_v3_xxxx)\n\nDone.'

# Media (local files uploaded automatically; --video requires --video-cover)
lark-cli im +messages-send --chat-id oc_xxx --image ./photo.png
lark-cli im +messages-send --chat-id oc_xxx --file ./report.pdf
lark-cli im +messages-send --chat-id oc_xxx --video ./demo.mp4 --video-cover ./cover.png
lark-cli im +messages-send --chat-id oc_xxx --audio ./voice.opus

# Idempotency (same key sends only once within 1 hour) / preview without sending
lark-cli im +messages-send --chat-id oc_xxx --text "Hi" --idempotency-key my-id
lark-cli im +messages-send --chat-id oc_xxx --markdown $'## Test\n\nhi' --dry-run
```

Run `lark-cli im +messages-send --help` for the full flag list and types. Load-bearing rules that `--help` may not make obvious:

- **Media paths** accept an existing key (`img_xxx`/`file_xxx`), an `http(s)://` URL, or a **cwd-relative** local path. Absolute paths (e.g. `/tmp/x.png`) are rejected — run from the file's directory and pass `./x.png`. Upload and send use the same identity.
- **`--video` must be paired with `--video-cover`** (image key/URL/local path); `--video-cover` cannot be used alone.
- **`--msg-type`** is inferred from `--text`/`--markdown`/media flags; explicitly setting a conflicting type fails validation.

## `content` Format Reference (for `--content`)

| `msg_type` | Example `content` |
|---|---|
| `text` | `{"text":"Hello <at user_id=\"ou_xxx\">name</at>"}` |
| `post` | `{"zh_cn":{"title":"Title","content":[[{"tag":"text","text":"Body"}]]}}` |
| `image` / `file` / `audio` | `{"image_key":"img_xxx"}` / `{"file_key":"file_xxx"}` / `{"file_key":"file_xxx"}` |
| `media` (video) | `{"file_key":"file_xxx","image_key":"img_xxx"}` (`image_key` is the **required** cover) |
| `share_chat` / `share_user` | `{"chat_id":"oc_xxx"}` / `{"user_id":"ou_xxx"}` |
| `interactive` (card) | Card JSON (see Feishu interactive card docs) |

When using `--content`, you are responsible for making the JSON match the effective `msg_type`.

## @Mention Format

The `<at>` syntax differs by message type; the shortcut normalizes mentions for `text` and `post` only — `interactive` cards are passed through verbatim.

- **`text`** / inside a `post` `text`/`md` element: `<at user_id="ou_xxx">name</at>` (inner name optional); @all: `<at user_id="all"></at>`. In `post` you may also use a node: `{"tag":"at","user_id":"ou_xxx"}` (`"all"` for everyone).
- **`interactive` (card)** — card-native syntax inside a `lark_md`/`markdown` element: `<at id=ou_xxx></at>`, multiple `<at ids=ou_1,ou_2></at>`, by email `<at email=user@example.com></at>`.

## Return Value

```json
{"message_id": "om_xxx", "chat_id": "oc_xxx", "create_time": "1234567890"}
```
