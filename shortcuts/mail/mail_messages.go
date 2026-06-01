// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package mail

import (
	"context"
	"fmt"
	"regexp"
	"strings"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
)

// mailMessagesOutput is the +messages JSON output: the batch-get result,
// plus the total count and any requested IDs the backend did not return.
type mailMessagesOutput struct {
	Messages              []map[string]interface{} `json:"messages"`
	Total                 int                      `json:"total"`
	UnavailableMessageIDs []string                 `json:"unavailable_message_ids,omitempty"`
}

// MailMessages is the `+messages` shortcut: batch-fetch full content for
// up to 20 message IDs in a single call, preserving request order.
var MailMessages = common.Shortcut{
	Service:     "mail",
	Command:     "+messages",
	Description: "Use when reading full content for multiple emails by message ID. Prefer this shortcut over calling raw mail user_mailbox.messages batch_get directly, because it base64url-decodes body fields and returns normalized per-message output that is easier to consume.",
	Risk:        "read",
	Scopes:      []string{"mail:user_mailbox.message:readonly", "mail:user_mailbox.message.address:read", "mail:user_mailbox.message.subject:read", "mail:user_mailbox.message.body:read"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags: []common.Flag{
		{Name: "mailbox", Default: "me", Desc: "email address (default: me)"},
		{Name: "message-ids", Desc: `Required. Comma-separated email message IDs. Example: "id1,id2,id3"`, Required: true},
		{Name: "html", Type: "bool", Default: "true", Desc: "Whether to return HTML body (false returns plain text only to save bandwidth)"},
		{Name: "print-output-schema", Type: "bool", Desc: "Print output field reference (run this first to learn field names before parsing output)"},
	},
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if err := validateBotMailboxNotMe(runtime); err != nil {
			return err
		}
		messageIDs := splitByComma(runtime.Str("message-ids"))
		return validateMessageIDs(messageIDs)
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		mailboxID := resolveMailboxID(runtime)
		messageIDs := splitByComma(runtime.Str("message-ids"))
		body := map[string]interface{}{
			"format":      messageGetFormat(runtime.Bool("html")),
			"message_ids": []string{"<message_id_1>", "<message_id_2>"},
		}
		if len(messageIDs) > 0 {
			body["message_ids"] = messageIDs
		}
		return common.NewDryRunAPI().
			Desc("Fetch multiple emails via messages.batch_get (auto-chunked in batches of 20 IDs during execution)").
			POST(mailboxPath(mailboxID, "messages", "batch_get")).
			Body(body)
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		if runtime.Bool("print-output-schema") {
			printMessageOutputSchema(runtime)
			return nil
		}
		mailboxID := resolveMailboxID(runtime)
		hintIdentityFirst(runtime, mailboxID)
		messageIDs := splitByComma(runtime.Str("message-ids"))
		if len(messageIDs) == 0 {
			return output.ErrValidation("--message-ids is required; provide one or more message IDs separated by commas")
		}
		html := runtime.Bool("html")

		rawMessages, missingMessageIDs, err := fetchFullMessages(runtime, mailboxID, messageIDs, html)
		if err != nil {
			return err
		}

		messages := make([]map[string]interface{}, 0, len(rawMessages))
		for _, msg := range rawMessages {
			messages = append(messages, buildMessageOutput(msg, html))
		}

		runtime.Out(mailMessagesOutput{
			Messages:              messages,
			Total:                 len(messages),
			UnavailableMessageIDs: missingMessageIDs,
		}, nil)
		for _, msg := range rawMessages {
			maybeHintReadReceiptRequest(runtime, mailboxID, strVal(msg["message_id"]), msg)
		}
		return nil
	},
}

// messageIDPattern matches a single message ID after cleaning: non-empty,
// no spaces, no brackets, no colons. Message IDs from the Lark mail API are
// opaque strings (typically hex or alphanumeric), so any character that
// suggests structural content (brackets, colons) is rejected.
var messageIDPattern = regexp.MustCompile(`^[^\s\[\]:]+$`)

// commonEnglishWords are words that indicate the input is natural language
// rather than opaque message IDs. The check is case-insensitive.
var commonEnglishWords = []string{
	"the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
	"her", "was", "one", "our", "out", "get", "has", "how", "its", "may",
	"new", "now", "old", "see", "way", "who", "did", "let", "say",
	"she", "too", "use", "from", "with", "this", "that", "have",
	"will", "been", "they", "what", "about", "would", "could", "their",
	"which", "there", "these", "other", "should", "please", "message",
	"email", "subject", "fetch", "read", "list", "send", "reply", "forward",
}

// validateMessageIDs validates each individual message ID after comma splitting.
// It rejects IDs that are clearly illegal before they reach the batch_get API:
//   - empty or whitespace-only
//   - wrapped in literal quotes (stripped before further validation)
//   - look like a JSON array string
//   - contain colon separators
//   - contain spaces (likely natural language)
//   - match common English words (likely natural language)
//   - don't match a reasonable message ID pattern
func validateMessageIDs(ids []string) error {
	if len(ids) == 0 {
		return nil // empty list is handled by the Execute function
	}
	var invalid []string
	for _, raw := range ids {
		if reason := validateSingleMessageID(raw); reason != "" {
			invalid = append(invalid, reason)
		}
	}
	if len(invalid) > 0 {
		return output.ErrValidation("invalid --message-ids: %s", strings.Join(invalid, "; "))
	}
	return nil
}

// validateSingleMessageID returns an empty string if the ID is valid, or a
// human-readable reason if it is invalid. It applies cleaning (quote
// stripping) before validation.
func validateSingleMessageID(raw string) string {
	id := strings.TrimSpace(raw)

	// Strip surrounding literal quotes (both single and double).
	if len(id) >= 2 {
		if (id[0] == '"' && id[len(id)-1] == '"') || (id[0] == '\'' && id[len(id)-1] == '\'') {
			id = strings.TrimSpace(id[1 : len(id)-1])
		}
	}

	// Reject empty or whitespace-only after trim.
	if id == "" {
		return fmt.Sprintf("%q: empty or whitespace-only", raw)
	}

	// Reject JSON array strings (e.g. "[\"id1\",\"id2\"]").
	if strings.HasPrefix(id, "[") && strings.HasSuffix(id, "]") {
		return fmt.Sprintf("%q: looks like a JSON array, not a single message ID", raw)
	}

	// Reject colon-separated IDs (e.g. "id1:id2:id3").
	if strings.Contains(id, ":") {
		return fmt.Sprintf("%q: contains colon separators (multiple IDs concatenated)", raw)
	}

	// Reject IDs with spaces — likely natural language or malformed input.
	if strings.Contains(id, " ") {
		return fmt.Sprintf("%q: contains spaces (expected opaque identifier)", raw)
	}

	// Reject IDs that look like natural language: common English words.
	lower := strings.ToLower(id)
	for _, word := range commonEnglishWords {
		if lower == word {
			return fmt.Sprintf("%q: looks like natural language, not a message ID", raw)
		}
	}

	// Final pattern check: non-empty, no spaces, no brackets, no colons.
	if !messageIDPattern.MatchString(id) {
		return fmt.Sprintf("%q: contains invalid characters (spaces, brackets, or colons)", raw)
	}

	return ""
}
