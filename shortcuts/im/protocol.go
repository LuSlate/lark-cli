// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package im

import (
	"encoding/json"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/shortcuts/common"
	"github.com/larksuite/cli/shortcuts/common/argstype"
)

// MessageTarget — exactly one of Chat or User identifies the recipient.
type MessageTarget struct {
	Chat *argstype.ChatID     `flag:"chat-id"  desc:"chat ID (oc_xxx)"`
	User *argstype.UserOpenID `flag:"user-id"  desc:"user open_id (ou_xxx)"`
}

func (MessageTarget) OneOf() {}

// MessageContent — exactly one of the seven content variants is sent.
type MessageContent struct {
	Text     *string              `flag:"text"     desc:"plain text message"`
	Markdown *string              `flag:"markdown" desc:"markdown text"`
	Image    *argstype.MediaInput `flag:"image"    desc:"image local file path / URL / img_xxx key"`
	File     *argstype.MediaInput `flag:"file"     desc:"file local file path / URL / file_xxx key"`
	Video    *VideoContent
	Audio    *argstype.MediaInput `flag:"audio"    desc:"audio file"`
	Raw      *RawContent
}

func (MessageContent) OneOf() {}

// VideoContent — video file requires an accompanying cover image.
type VideoContent struct {
	File  argstype.MediaInput `flag:"video"       oneof_trigger:"true" desc:"video file path / URL / file_xxx key"`
	Cover argstype.MediaInput `flag:"video-cover" desc:"video cover image; required with --video"`
}

// RawContent — raw JSON body with explicit msg-type, selected by --content.
type RawContent struct {
	JSON    string `flag:"content"  oneof_trigger:"true" desc:"raw message content JSON"`
	MsgType string `flag:"msg-type" default:"text" enum:"text,post,image,file,audio,media,interactive,share_chat,share_user" desc:"message type for --content JSON (default: text)"`
}

func (r *RawContent) ValidateValue(_ *common.RuntimeContext, _ string) error {
	if r == nil || r.JSON == "" {
		return nil
	}
	if !json.Valid([]byte(r.JSON)) {
		return &errs.ValidationError{
			Problem: errs.Problem{
				Category: errs.CategoryValidation,
				Subtype:  errs.SubtypeInvalidArgument,
				Message:  "--content is not valid JSON",
				Hint:     `pass a JSON string such as {"text":"hello"}`,
			},
			Param: "--content",
		}
	}
	return nil
}
