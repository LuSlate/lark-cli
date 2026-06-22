# +feed-group-list

> Shortcut for `lark-cli im +feed-group-list`. List the caller's feed groups (tags) with auto-pagination that correctly merges both the live and soft-deleted lists.

`+feed-group-list` is the only CLI surface for listing feed groups — there is no raw `feed.groups list` command. The list response carries two parallel arrays — `groups` (live) and `deleted_groups` (soft-deleted). The shortcut paginates this dual-list response correctly: its `--page-all` merges **both** arrays across pages (a naive single-array pager would silently drop one list's later pages). It adds no enrichment.

## Identity

User-only. Run with `--as user`.

## Scopes

- `im:feed_group_v1:read`

## Usage

```bash
# First page
lark-cli im +feed-group-list --as user

# Auto-paginate through all your feed groups (both live and deleted)
lark-cli im +feed-group-list --as user --page-all

# Within an update-time window
lark-cli im +feed-group-list --as user --page-all \
  --start-time 1767196800000 --end-time 1767200000000
```

## Flags

| Flag | Required | Description |
|---|---|---|
| `--page-size` | No | Records per page, 1–50 (default 50). Caps the combined `groups` + `deleted_groups` count, so a page may hold fewer live groups than the size suggests |
| `--page-token` | No | Continuation token for a specific page |
| `--page-all` | No | Auto-paginate and merge all pages (both lists) |
| `--page-limit` | No | Max pages when `--page-all` is set, 1–1000 (default 20) |
| `--start-time` | No | Update-time window start (Unix milliseconds as a decimal string) |
| `--end-time` | No | Update-time window end (Unix milliseconds as a decimal string) |

When `--page-token` is set explicitly, it wins over `--page-all` (you get exactly that page).

## Output

JSON keeps the raw envelope; with `--page-all` both lists are returned fully merged:

```json
{
  "groups": [
    { "group_id": "ofg_xxx", "type": "normal", "name": "Releases", "rules": { "rules": [] } }
  ],
  "deleted_groups": [
    { "group_id": "ofg_yyy", "type": "rule", "name": "Old", "rules": { "rules": [] } }
  ],
  "page_token": "",
  "has_more": false
}
```

> `page_size` counts live and deleted groups together, and the per-page count can be smaller still when entries are filtered — so never infer completeness from counts. Pagination is governed solely by `has_more`.

## Default view and `--full`

Output is a **curated view**: each group keeps `group_id`, `name`, and `type`. The `rules` object (shown in the example above) is **hidden by default**.

- `--full` returns the complete upstream payload (`rules` included).
- Need `rules`? Use **`--full --jq <path>`** (e.g. `--full --jq '.data.groups[].rules'`). The `--full` is required even with `--jq`: `--jq` filters the curated view, where hidden fields are already trimmed away — so a bare `--jq '.data.groups[].rules'` returns `null` (and stderr prints a `... is full-only ... re-run with --full` note). Pairing `--jq` with `--full` keeps the output to just that field, so you avoid dumping the whole payload back into context.
- A field missing from the default view does **not** mean it doesn't exist — it may be full-only. Don't conclude "no such field" from its absence here.
- Don't try `lark-cli schema` to introspect this command (it isn't in the catalog); the field list is in this doc.

## See also

- [lark-im-feed-groups.md](lark-im-feed-groups.md) — raw `feed.groups.*` APIs, enums, and rule guidance
- [lark-im-feed-group-list-item.md](lark-im-feed-group-list-item.md) — list the feed cards inside one group
- [lark-im-feed-group-query-item.md](lark-im-feed-group-query-item.md) — look up specific feed cards by ID
