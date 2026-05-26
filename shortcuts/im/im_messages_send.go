// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package im

import (
	"context"
	"net/http"

	larkcore "github.com/larksuite/oapi-sdk-go/v3/core"
	"github.com/spf13/cobra"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/shortcuts/common"
	"github.com/larksuite/cli/shortcuts/common/argstype"
)

// ImMessagesSendArgs is the typed argument struct backing `im +messages-send`.
//
// Target / Content are OneOf buckets (see protocol.go) — the framework enforces
// "exactly one trigger flag set" and emits structured errors with subtype
// shortcut_oneof_missing / shortcut_oneof_multiple if the caller violates that.
// VideoContent is a paired group inside the Content bucket — the framework
// emits shortcut_group_incomplete when --video is set without --video-cover.
type ImMessagesSendArgs struct {
	Target         MessageTarget
	Content        MessageContent
	IdempotencyKey string `flag:"idempotency-key" desc:"idempotency key (prevents duplicate sends)"`
}

// imSendExamples are rendered in the --help EXAMPLES section by the typed help
// builder. The text mirrors §"Pilot 改造" of the shortcut-protocol spec
// (lines 442-446).
var imSendExamples = []common.HelpExample{
	{Title: "text to chat", Cmd: `--chat-id oc_x --text "hi"`},
	{Title: "markdown to user", Cmd: `--user-id ou_x --markdown "**hi**"`},
	{Title: "video with cover", Cmd: `--chat-id oc_x --video v.mp4 --video-cover c.png`},
}

// ImMessagesSend is the typed pilot for the shortcut-protocol refactor.
// Behavior matches the legacy common.Shortcut version exactly (same flags,
// same body shape, same envelope) — only the wiring changes: OneOf / group /
// typed-primitive format are framework-enforced instead of hand-rolled
// inside a Validate closure.
var ImMessagesSend = common.TypedShortcut[*ImMessagesSendArgs]{
	Service:     "im",
	Command:     "+messages-send",
	Description: "Send a message to a chat or direct message; user/bot; sends to chat-id or user-id with text/markdown/post/media, supports idempotency key",
	Risk:        "write",
	Scopes:      []string{"im:message:send_as_bot"},
	UserScopes:  []string{"im:message.send_as_user", "im:message"},
	BotScopes:   []string{"im:message:send_as_bot"},
	AuthTypes:   []string{"bot", "user"},
	Examples:    imSendExamples,

	// Validate covers the one cross-field rule the framework cannot infer
	// from enum tags alone: an explicit --msg-type that conflicts with the
	// inferred type from the selected content flag (e.g. --text "hi"
	// --msg-type image).
	//
	// Other invariants (OneOf missing/multiple, VideoContent group
	// completeness, ChatID/UserOpenID/MediaInput format, RawContent JSON
	// validity, msg-type enum membership) are enforced upstream by the
	// framework's runValidateValue + runFrameworkRules. The bindMessagesSendArgs
	// + validateVideoGroup defensive calls below let direct invocations of
	// this closure (e.g. unit tests that bypass the framework Validate stack)
	// still see populated args and surface the VideoContent group error —
	// in the production runShortcut path the framework has already done both
	// and short-circuited before this hook ever runs.
	Validate: func(ctx context.Context, args *ImMessagesSendArgs, rt *common.RuntimeContext) error {
		bindMessagesSendArgs(rt.Cmd, args)
		if err := validateVideoGroup(rt.Cmd); err != nil {
			return err
		}
		return validateMsgTypeInterplay(rt.Cmd, args)
	},

	DryRun: func(ctx context.Context, args *ImMessagesSendArgs, rt *common.RuntimeContext) *common.DryRunAPI {
		// Defensive: framework's bindBuckets has already populated args when
		// reaching this closure via the production runShortcut path. The call
		// is retained so direct invocations (e.g. unit tests that pass an
		// empty Args struct + populated cobra flags) still bind correctly.
		bindMessagesSendArgs(rt.Cmd, args)

		text := strOrEmpty(args.Content.Text)
		markdown := strOrEmpty(args.Content.Markdown)
		imageKey := mediaOrEmpty(args.Content.Image)
		fileKey := mediaOrEmpty(args.Content.File)
		videoKey, videoCoverKey := videoOrEmpty(args.Content.Video)
		audioKey := mediaOrEmpty(args.Content.Audio)
		content, msgType := rawOrDefault(args.Content.Raw)
		idempotencyKey := args.IdempotencyKey

		desc := ""
		if markdown != "" {
			msgType = "post"
			content, desc = wrapMarkdownAsPostForDryRun(markdown)
		} else if mt, c, d := buildMediaContentFromKey(text, imageKey, fileKey, videoKey, videoCoverKey, audioKey); mt != "" {
			msgType, content, desc = mt, c, d
		}

		receiveIdType := "chat_id"
		receiveId := chatOrEmpty(args.Target.Chat)
		if userID := userOrEmpty(args.Target.User); userID != "" {
			receiveIdType = "open_id"
			receiveId = userID
		}

		if msgType == "text" || msgType == "post" {
			content = normalizeAtMentions(content)
		}

		body := map[string]interface{}{"receive_id": receiveId, "msg_type": msgType, "content": content}
		if idempotencyKey != "" {
			body["uuid"] = idempotencyKey
		}

		d := common.NewDryRunAPI()
		if desc != "" {
			d.Desc(desc)
		}
		return d.
			POST("/open-apis/im/v1/messages").
			Params(map[string]interface{}{"receive_id_type": receiveIdType}).
			Body(body)
	},

	Execute: func(ctx context.Context, args *ImMessagesSendArgs, rt *common.RuntimeContext) error {
		// Defensive: see DryRun's note about double-binding.
		bindMessagesSendArgs(rt.Cmd, args)

		text := strOrEmpty(args.Content.Text)
		markdown := strOrEmpty(args.Content.Markdown)
		imageVal := mediaOrEmpty(args.Content.Image)
		fileVal := mediaOrEmpty(args.Content.File)
		videoVal, videoCoverVal := videoOrEmpty(args.Content.Video)
		audioVal := mediaOrEmpty(args.Content.Audio)
		content, msgType := rawOrDefault(args.Content.Raw)
		idempotencyKey := args.IdempotencyKey

		// Pre-flight: reject unreadable local paths early. The MediaInput typed
		// primitive only enforces cwd-relative safety (absolute path / `..`
		// rejection) — the loose os.Stat check stays here because it touches
		// the filesystem and is not appropriate at the format-validation layer.
		fio := rt.FileIO()
		for _, mf := range []struct{ flag, val string }{
			{"--image", imageVal}, {"--file", fileVal}, {"--video", videoVal},
			{"--video-cover", videoCoverVal}, {"--audio", audioVal},
		} {
			if err := validateMediaFlagPath(fio, mf.flag, mf.val); err != nil {
				return err
			}
		}

		// Resolve content type.
		if markdown != "" {
			msgType, content = "post", resolveMarkdownAsPost(ctx, rt, markdown)
		} else if mt, c, err := resolveMediaContent(ctx, rt, text, imageVal, fileVal, videoVal, videoCoverVal, audioVal); err != nil {
			return err
		} else if mt != "" {
			msgType, content = mt, c
		}

		receiveIdType := "chat_id"
		receiveId := chatOrEmpty(args.Target.Chat)
		if userID := userOrEmpty(args.Target.User); userID != "" {
			receiveIdType = "open_id"
			receiveId = userID
		}

		normalizedContent := content
		if msgType == "text" || msgType == "post" {
			normalizedContent = normalizeAtMentions(content)
		}

		data := map[string]interface{}{
			"receive_id": receiveId,
			"msg_type":   msgType,
			"content":    normalizedContent,
		}
		if idempotencyKey != "" {
			data["uuid"] = idempotencyKey
		}

		resData, err := rt.DoAPIJSON(http.MethodPost, "/open-apis/im/v1/messages",
			larkcore.QueryParams{"receive_id_type": []string{receiveIdType}}, data)
		if err != nil {
			return err
		}

		rt.Out(map[string]interface{}{
			"message_id":  resData["message_id"],
			"chat_id":     resData["chat_id"],
			"create_time": common.FormatTimeWithSeconds(resData["create_time"]),
		}, nil)
		return nil
	},
}

// bindMessagesSendArgs populates the OneOf sub-struct pointer fields from
// cobra flag state. The shared framework binder (binder.go) currently only
// binds top-level fields; sub-struct binding lives here so the typed closures
// can read `args.Target.Chat` / `args.Content.Text` etc. instead of falling
// back to `rt.Cmd.Flags().GetString`. Pointer is set iff cobra reports the
// flag was explicitly provided (matches the "nil = not set" OneOf contract).
func bindMessagesSendArgs(cmd *cobra.Command, args *ImMessagesSendArgs) {
	if cmd == nil || args == nil {
		return
	}
	flags := cmd.Flags()

	// Target bucket — exactly one of --chat-id / --user-id.
	if flags.Changed("chat-id") {
		v, _ := flags.GetString("chat-id")
		id := argstype.ChatID(v)
		args.Target.Chat = &id
	}
	if flags.Changed("user-id") {
		v, _ := flags.GetString("user-id")
		id := argstype.UserOpenID(v)
		args.Target.User = &id
	}

	// Content bucket — exactly one of --text / --markdown / --image / --file /
	// --video (+ --video-cover) / --audio / --content.
	if flags.Changed("text") {
		v, _ := flags.GetString("text")
		args.Content.Text = &v
	}
	if flags.Changed("markdown") {
		v, _ := flags.GetString("markdown")
		args.Content.Markdown = &v
	}
	if flags.Changed("image") {
		v, _ := flags.GetString("image")
		m := argstype.MediaInput(v)
		args.Content.Image = &m
	}
	if flags.Changed("file") {
		v, _ := flags.GetString("file")
		m := argstype.MediaInput(v)
		args.Content.File = &m
	}
	if flags.Changed("audio") {
		v, _ := flags.GetString("audio")
		m := argstype.MediaInput(v)
		args.Content.Audio = &m
	}
	if flags.Changed("video") {
		v, _ := flags.GetString("video")
		cover, _ := flags.GetString("video-cover")
		args.Content.Video = &VideoContent{
			File:  argstype.MediaInput(v),
			Cover: argstype.MediaInput(cover),
		}
	}
	if flags.Changed("content") {
		raw, _ := flags.GetString("content")
		msgType, _ := flags.GetString("msg-type")
		args.Content.Raw = &RawContent{JSON: raw, MsgType: msgType}
	}

	// IdempotencyKey is a top-level string field already bound by the framework
	// binder; this read keeps the path uniform for callers using a synthetic
	// command (e.g. tests bypassing the framework Validate stage).
	if flags.Changed("idempotency-key") && args.IdempotencyKey == "" {
		args.IdempotencyKey, _ = flags.GetString("idempotency-key")
	}
}

// strOrEmpty deref-protects a *string field — nil → "".
func strOrEmpty(p *string) string {
	if p == nil {
		return ""
	}
	return *p
}

// chatOrEmpty deref-protects an *argstype.ChatID — nil → "".
func chatOrEmpty(p *argstype.ChatID) string {
	if p == nil {
		return ""
	}
	return string(*p)
}

// userOrEmpty deref-protects an *argstype.UserOpenID — nil → "".
func userOrEmpty(p *argstype.UserOpenID) string {
	if p == nil {
		return ""
	}
	return string(*p)
}

// mediaOrEmpty deref-protects an *argstype.MediaInput — nil → "".
func mediaOrEmpty(p *argstype.MediaInput) string {
	if p == nil {
		return ""
	}
	return string(*p)
}

// videoOrEmpty returns (file, cover) from an optional VideoContent. nil → ("", "").
func videoOrEmpty(v *VideoContent) (string, string) {
	if v == nil {
		return "", ""
	}
	return string(v.File), string(v.Cover)
}

// rawOrDefault returns (content, msgType) from an optional RawContent. nil →
// ("", "text"). The "text" default matches the RawContent.MsgType tag default
// and ensures the DryRun body still has a sensible msg_type when no raw
// content is supplied (it will be replaced when a media flag is selected).
func rawOrDefault(r *RawContent) (string, string) {
	if r == nil {
		return "", "text"
	}
	msgType := r.MsgType
	if msgType == "" {
		msgType = "text"
	}
	return r.JSON, msgType
}

// validateVideoGroup enforces the VideoContent paired-flag rule: --video and
// --video-cover must be supplied together. Produces a structured envelope
// with subtype shortcut_group_incomplete and param "VideoContent". The shared
// binder only runs group-completeness against top-level Args fields, so we
// run the check manually here.
func validateVideoGroup(cmd *cobra.Command) error {
	if cmd == nil {
		return nil
	}
	videoSet := cmd.Flags().Changed("video")
	coverSet := cmd.Flags().Changed("video-cover")
	if videoSet == coverSet {
		return nil
	}
	missing := "--video-cover"
	if !videoSet {
		missing = "--video"
	}
	return &errs.ValidationError{
		Problem: errs.Problem{
			Category: errs.CategoryValidation,
			Subtype:  errs.SubtypeShortcutGroupIncomplete,
			Message:  "VideoContent requires " + missing,
			Hint:     "--video and --video-cover must be supplied together",
		},
		Param: "VideoContent",
	}
}

// validateMsgTypeInterplay rejects an explicit --msg-type that conflicts with
// the message type inferred from --text / --markdown / --image / --file /
// --video / --audio. Preserved verbatim from the legacy Validate closure
// because RawContent's enum check accepts any of the listed types — the
// framework can't infer the writer's intent from the other content flags.
func validateMsgTypeInterplay(cmd *cobra.Command, args *ImMessagesSendArgs) error {
	if cmd == nil || !cmd.Flags().Changed("msg-type") {
		return nil
	}
	msgType, _ := cmd.Flags().GetString("msg-type")
	var inferred string
	switch {
	case args.Content.Text != nil:
		inferred = "text"
	case args.Content.Markdown != nil:
		inferred = "post"
	case args.Content.Image != nil:
		inferred = "image"
	case args.Content.File != nil:
		inferred = "file"
	case args.Content.Video != nil:
		inferred = "media"
	case args.Content.Audio != nil:
		inferred = "audio"
	}
	if inferred == "" || msgType == inferred {
		return nil
	}
	return &errs.ValidationError{
		Problem: errs.Problem{
			Category: errs.CategoryValidation,
			Subtype:  errs.SubtypeInvalidArgument,
			Message:  "--msg-type \"" + msgType + "\" conflicts with the inferred message type \"" + inferred + "\" from the selected content flag",
		},
		Param: "msg-type",
	}
}
