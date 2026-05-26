// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package im

import (
	"context"
	"errors"
	"testing"

	"github.com/spf13/cobra"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/shortcuts/common"
)

// TestImMessagesSend_IsMountable is the compile-time gate that locks the pilot
// shortcut onto the TypedShortcut → Mountable contract. A breaking change to
// the framework interface set must be reflected here.
func TestImMessagesSend_IsMountable(t *testing.T) {
	var _ common.Mountable = ImMessagesSend
	var _ common.ShortcutDescriptor = ImMessagesSend
}

// TestImMessagesSend_Metadata pins the descriptor surface that auth-login /
// scope-hint / shortcuts.json generators read. Drift here is silent in the
// migration diff because the legacy struct disappears.
func TestImMessagesSend_Metadata(t *testing.T) {
	t.Helper()
	if got := ImMessagesSend.GetService(); got != "im" {
		t.Errorf("GetService = %q, want \"im\"", got)
	}
	if got := ImMessagesSend.GetCommand(); got != "+messages-send" {
		t.Errorf("GetCommand = %q, want \"+messages-send\"", got)
	}
	if got := ImMessagesSend.GetRisk(); got != "write" {
		t.Errorf("GetRisk = %q, want \"write\"", got)
	}
	wantAuth := map[string]bool{"bot": true, "user": true}
	gotAuth := ImMessagesSend.GetAuthTypes()
	if len(gotAuth) != len(wantAuth) {
		t.Errorf("GetAuthTypes = %v, want set %v", gotAuth, wantAuth)
	}
	for _, a := range gotAuth {
		if !wantAuth[a] {
			t.Errorf("unexpected auth type %q in %v", a, gotAuth)
		}
	}
}

// TestImMessagesSend_ScopesForIdentity verifies user / bot variants resolve
// to the right scope sets. Login flows depend on this routing.
func TestImMessagesSend_ScopesForIdentity(t *testing.T) {
	tests := []struct {
		identity string
		want     []string
	}{
		{"user", []string{"im:message.send_as_user", "im:message"}},
		{"bot", []string{"im:message:send_as_bot"}},
		{"", []string{"im:message:send_as_bot"}}, // fallback to Scopes
	}
	for _, tc := range tests {
		got := ImMessagesSend.ScopesForIdentity(tc.identity)
		if len(got) != len(tc.want) {
			t.Errorf("ScopesForIdentity(%q) = %v, want %v", tc.identity, got, tc.want)
			continue
		}
		for i, s := range got {
			if s != tc.want[i] {
				t.Errorf("ScopesForIdentity(%q)[%d] = %q, want %q", tc.identity, i, s, tc.want[i])
			}
		}
	}
}

// TestImMessagesSend_MountRegistersFlags exercises the full Mount path to
// confirm every flag the legacy shortcut accepted is still registered on the
// generated cobra subcommand. Full Execute / Validate integration is in
// tests_e2e/shortcuts/ (runShortcut needs a real Factory).
func TestImMessagesSend_MountRegistersFlags(t *testing.T) {
	root := &cobra.Command{Use: "root"}
	imParent := &cobra.Command{Use: "im"}
	root.AddCommand(imParent)
	ImMessagesSend.MountWithContext(context.Background(), imParent, &cmdutil.Factory{})

	sub, _, err := imParent.Find([]string{"+messages-send"})
	if err != nil {
		t.Fatalf("find +messages-send: %v", err)
	}
	if sub == nil {
		t.Fatal("expected +messages-send subcommand registered")
	}

	wantFlags := []string{
		"chat-id", "user-id",
		"text", "markdown", "image", "file", "video", "video-cover", "audio",
		"content", "msg-type",
		"idempotency-key",
	}
	for _, name := range wantFlags {
		if sub.Flag(name) == nil {
			t.Errorf("expected --%s registered on +messages-send", name)
		}
	}
}

// TestImMessagesSend_HelpFuncInstalled verifies the typed help renderer was
// wired by the Mount adapter (covers Examples section + Risk/Tips passthrough
// indirectly — full render content is asserted in typed_help_test.go).
func TestImMessagesSend_HelpFuncInstalled(t *testing.T) {
	root := &cobra.Command{Use: "root"}
	imParent := &cobra.Command{Use: "im"}
	root.AddCommand(imParent)
	ImMessagesSend.MountWithContext(context.Background(), imParent, &cmdutil.Factory{})

	sub, _, _ := imParent.Find([]string{"+messages-send"})
	if sub == nil || sub.HelpFunc() == nil {
		t.Fatal("expected typed help func installed on +messages-send")
	}
}

// TestValidateVideoGroup covers the manual paired-flag check that compensates
// for the framework binder not recursing groups inside OneOf buckets.
// --video without --video-cover (and vice versa) must produce a structured
// envelope with subtype shortcut_group_incomplete.
func TestValidateVideoGroup(t *testing.T) {
	tests := []struct {
		name     string
		args     []string
		wantErr  bool
		wantSub  errs.Subtype
		wantPara string
	}{
		{"both unset → ok", nil, false, "", ""},
		{"both set → ok", []string{"--video=v.mp4", "--video-cover=c.png"}, false, "", ""},
		{"video without cover", []string{"--video=v.mp4"}, true, errs.SubtypeShortcutGroupIncomplete, "VideoContent"},
		{"cover without video", []string{"--video-cover=c.png"}, true, errs.SubtypeShortcutGroupIncomplete, "VideoContent"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			cmd := &cobra.Command{Use: "send"}
			cmd.Flags().String("video", "", "")
			cmd.Flags().String("video-cover", "", "")
			if err := cmd.ParseFlags(tc.args); err != nil {
				t.Fatalf("ParseFlags: %v", err)
			}
			err := validateVideoGroup(cmd)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr = %v", err, tc.wantErr)
			}
			if !tc.wantErr {
				return
			}
			var ve *errs.ValidationError
			if !errors.As(err, &ve) {
				t.Fatalf("expected *errs.ValidationError, got %T (%v)", err, err)
			}
			if ve.Subtype != tc.wantSub {
				t.Errorf("Subtype = %q, want %q", ve.Subtype, tc.wantSub)
			}
			if ve.Param != tc.wantPara {
				t.Errorf("Param = %q, want %q", ve.Param, tc.wantPara)
			}
		})
	}
}

// TestValidateMsgTypeInterplay covers the legacy guard that rejects an
// explicit --msg-type that contradicts the inferred type. The Content bucket
// pointer fields drive the inference (matching the typed-args read path).
func TestValidateMsgTypeInterplay(t *testing.T) {
	mkArgs := func() *ImMessagesSendArgs { return &ImMessagesSendArgs{} }
	tests := []struct {
		name      string
		setup     func(*ImMessagesSendArgs)
		msgType   string
		changed   bool
		wantErr   bool
		wantParam string
	}{
		{"msg-type unchanged → ok", func(a *ImMessagesSendArgs) { s := "hi"; a.Content.Text = &s }, "text", false, false, ""},
		{"text + text → ok", func(a *ImMessagesSendArgs) { s := "hi"; a.Content.Text = &s }, "text", true, false, ""},
		{"text + image → conflict", func(a *ImMessagesSendArgs) { s := "hi"; a.Content.Text = &s }, "image", true, true, "msg-type"},
		{"markdown + image → conflict", func(a *ImMessagesSendArgs) { s := "**hi**"; a.Content.Markdown = &s }, "image", true, true, "msg-type"},
		{"no content selected → ok", func(a *ImMessagesSendArgs) {}, "image", true, false, ""},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			cmd := &cobra.Command{Use: "send"}
			cmd.Flags().String("msg-type", "text", "")
			args := []string{}
			if tc.changed {
				args = append(args, "--msg-type="+tc.msgType)
			}
			if err := cmd.ParseFlags(args); err != nil {
				t.Fatalf("ParseFlags: %v", err)
			}
			a := mkArgs()
			tc.setup(a)
			err := validateMsgTypeInterplay(cmd, a)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr = %v", err, tc.wantErr)
			}
			if !tc.wantErr {
				return
			}
			var ve *errs.ValidationError
			if !errors.As(err, &ve) {
				t.Fatalf("expected *errs.ValidationError, got %T", err)
			}
			if ve.Subtype != errs.SubtypeInvalidArgument {
				t.Errorf("Subtype = %q, want invalid_argument", ve.Subtype)
			}
			if ve.Param != tc.wantParam {
				t.Errorf("Param = %q, want %q", ve.Param, tc.wantParam)
			}
		})
	}
}

// TestBindMessagesSendArgs covers the local sub-struct binder that fills the
// Content / Target OneOf buckets from cobra flag state. Pointer is non-nil iff
// the flag was explicitly Changed — matches the "nil = unset" OneOf contract.
func TestBindMessagesSendArgs(t *testing.T) {
	cmd := &cobra.Command{Use: "send"}
	cmd.Flags().String("chat-id", "", "")
	cmd.Flags().String("user-id", "", "")
	cmd.Flags().String("text", "", "")
	cmd.Flags().String("markdown", "", "")
	cmd.Flags().String("image", "", "")
	cmd.Flags().String("file", "", "")
	cmd.Flags().String("video", "", "")
	cmd.Flags().String("video-cover", "", "")
	cmd.Flags().String("audio", "", "")
	cmd.Flags().String("content", "", "")
	cmd.Flags().String("msg-type", "text", "")
	cmd.Flags().String("idempotency-key", "", "")

	if err := cmd.ParseFlags([]string{
		"--chat-id=oc_abc",
		"--text=hi",
	}); err != nil {
		t.Fatalf("ParseFlags: %v", err)
	}

	args := &ImMessagesSendArgs{}
	bindMessagesSendArgs(cmd, args)

	if args.Target.Chat == nil || string(*args.Target.Chat) != "oc_abc" {
		t.Errorf("Target.Chat = %v, want non-nil oc_abc", args.Target.Chat)
	}
	if args.Target.User != nil {
		t.Errorf("Target.User = %v, want nil (flag unset)", args.Target.User)
	}
	if args.Content.Text == nil || *args.Content.Text != "hi" {
		t.Errorf("Content.Text = %v, want non-nil \"hi\"", args.Content.Text)
	}
	if args.Content.Markdown != nil {
		t.Errorf("Content.Markdown = %v, want nil", args.Content.Markdown)
	}
	if args.Content.Video != nil {
		t.Errorf("Content.Video = %v, want nil", args.Content.Video)
	}
	if args.Content.Raw != nil {
		t.Errorf("Content.Raw = %v, want nil", args.Content.Raw)
	}
}

// TestBindMessagesSendArgs_VideoPair confirms the paired --video / --video-cover
// flags collapse into one VideoContent struct (the framework would otherwise
// see two unrelated triggers).
func TestBindMessagesSendArgs_VideoPair(t *testing.T) {
	cmd := &cobra.Command{Use: "send"}
	cmd.Flags().String("chat-id", "", "")
	cmd.Flags().String("user-id", "", "")
	cmd.Flags().String("text", "", "")
	cmd.Flags().String("markdown", "", "")
	cmd.Flags().String("image", "", "")
	cmd.Flags().String("file", "", "")
	cmd.Flags().String("video", "", "")
	cmd.Flags().String("video-cover", "", "")
	cmd.Flags().String("audio", "", "")
	cmd.Flags().String("content", "", "")
	cmd.Flags().String("msg-type", "text", "")
	cmd.Flags().String("idempotency-key", "", "")

	if err := cmd.ParseFlags([]string{
		"--chat-id=oc_x",
		"--video=v.mp4",
		"--video-cover=c.png",
	}); err != nil {
		t.Fatalf("ParseFlags: %v", err)
	}
	args := &ImMessagesSendArgs{}
	bindMessagesSendArgs(cmd, args)
	if args.Content.Video == nil {
		t.Fatal("Content.Video = nil, want non-nil")
	}
	if string(args.Content.Video.File) != "v.mp4" {
		t.Errorf("Video.File = %q, want \"v.mp4\"", args.Content.Video.File)
	}
	if string(args.Content.Video.Cover) != "c.png" {
		t.Errorf("Video.Cover = %q, want \"c.png\"", args.Content.Video.Cover)
	}
}

// TestBindMessagesSendArgs_Raw covers the --content + --msg-type pair that
// rolls into a RawContent variant.
func TestBindMessagesSendArgs_Raw(t *testing.T) {
	cmd := &cobra.Command{Use: "send"}
	cmd.Flags().String("chat-id", "", "")
	cmd.Flags().String("user-id", "", "")
	cmd.Flags().String("text", "", "")
	cmd.Flags().String("markdown", "", "")
	cmd.Flags().String("image", "", "")
	cmd.Flags().String("file", "", "")
	cmd.Flags().String("video", "", "")
	cmd.Flags().String("video-cover", "", "")
	cmd.Flags().String("audio", "", "")
	cmd.Flags().String("content", "", "")
	cmd.Flags().String("msg-type", "text", "")
	cmd.Flags().String("idempotency-key", "", "")

	if err := cmd.ParseFlags([]string{
		"--chat-id=oc_x",
		"--content={\"text\":\"hello\"}",
		"--msg-type=text",
	}); err != nil {
		t.Fatalf("ParseFlags: %v", err)
	}
	args := &ImMessagesSendArgs{}
	bindMessagesSendArgs(cmd, args)
	if args.Content.Raw == nil {
		t.Fatal("Content.Raw = nil, want non-nil")
	}
	if args.Content.Raw.JSON != `{"text":"hello"}` {
		t.Errorf("Raw.JSON = %q, want \"{...}\"", args.Content.Raw.JSON)
	}
	if args.Content.Raw.MsgType != "text" {
		t.Errorf("Raw.MsgType = %q, want \"text\"", args.Content.Raw.MsgType)
	}
}

// TestImMessagesSend_TypedShortcutsRegistered confirms the package-level
// TypedShortcuts() slice exposes the pilot so register.go can mount it. A
// regression here would silently strip --messages-send from the CLI.
func TestImMessagesSend_TypedShortcutsRegistered(t *testing.T) {
	list := TypedShortcuts()
	found := false
	for _, m := range list {
		if m.GetService() == "im" && m.GetCommand() == "+messages-send" {
			found = true
			break
		}
	}
	if !found {
		t.Error("im.TypedShortcuts() must contain ImMessagesSend (service=im, command=+messages-send)")
	}
}

// TestImMessagesSend_NotInLegacyShortcuts is the dual of the above: a shortcut
// MUST live in exactly one of Shortcuts() / TypedShortcuts(), otherwise
// register.go will mount the same cobra subcommand twice.
func TestImMessagesSend_NotInLegacyShortcuts(t *testing.T) {
	for _, sc := range Shortcuts() {
		if sc.Service == "im" && sc.Command == "+messages-send" {
			t.Fatalf("ImMessagesSend appears in legacy Shortcuts() — must only be in TypedShortcuts() after migration")
		}
	}
}
