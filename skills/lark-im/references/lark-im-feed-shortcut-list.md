# im +feed-shortcut-list

> **Prerequisite:** Read [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) for authentication, global parameters, and security rules.

This skill maps to shortcut: `lark-cli im +feed-shortcut-list`. Underlying API: `GET /open-apis/im/v2/feed_shortcuts`.

## What it does

Lists the **current user's full** feed shortcut list.

- Only **CHAT-type** shortcuts are exposed via OpenAPI today (others in the IDL are not yet whitelisted).
- The latest OAPI contract returns the whole list directly, so this shortcut exposes **no pagination flags**.
- The shortcut also does **not** perform any follow-up `im.chats.batch_query` detail enrichment.

## Commands

```bash
# List the current user's full shortcut list
lark-cli im +feed-shortcut-list --as user
```

## Parameters

| Parameter | Required | Description |
|------|------|------|
| `--as user` | yes | Server only accepts user_access_token for this API |

## Response Structure

| Field | Type | Description |
|------|------|------|
| `shortcuts` | array | Feed shortcut entries; each has `feed_card_id` (oc_xxx) and `type` (1=CHAT). |

Example:

```json
{
  "data": {
    "shortcuts": [
      {
        "feed_card_id": "oc_092f0100fe59c35995727db1039777a8",
        "type": 1
      },
      {
        "feed_card_id": "oc_c82061d126a06635aa3569587b134bb1",
        "type": 1
      }
    ]
  }
}
```

## Permissions

- Required scope: `im:feed.shortcut:read`
- Only available with user identity (`--as user`).
