// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package vc

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
)

const vcActiveMeetingsAPIPath = "/open-apis/vc/v1/bots/active-meetings"

// VCMeetingListActive lists the caller's ongoing meetings.
// As user (UAT): returns the user's own ongoing meetings.
// As bot (TAT): returns the target user's ongoing meetings that the bot is also in.
var VCMeetingListActive = common.Shortcut{
	Service:     "vc",
	Command:     "+meeting-list-active",
	Description: "List ongoing meetings for the current identity (UAT: self; TAT: target user with bot in meeting)",
	Risk:        "read",
	Scopes:      []string{"vc:meeting.active:read"},
	AuthTypes:   []string{"user", "bot"},
	HasFormat:   true,
	Flags: []common.Flag{
		{Name: "user-id", Desc: "target user open_id (ou_...), required when --as bot"},
	},
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		userID := strings.TrimSpace(runtime.Str("user-id"))
		if runtime.IsBot() {
			if userID == "" {
				return errs.NewValidationError(errs.SubtypeInvalidArgument, "--user-id is required when --as bot").WithParam("--user-id")
			}
			if !strings.HasPrefix(userID, "ou_") {
				return errs.NewValidationError(errs.SubtypeInvalidArgument, "--user-id must be an open_id (ou_...), got %q", userID).WithParam("--user-id")
			}
		}
		return nil
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		dryRun := common.NewDryRunAPI().GET(vcActiveMeetingsAPIPath)
		if params := buildActiveMeetingsParams(runtime); len(params) > 0 {
			dryRun.Params(params)
		}
		return dryRun
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		params := buildActiveMeetingsParams(runtime)
		data, err := runtime.CallAPITyped(http.MethodGet, vcActiveMeetingsAPIPath, params, nil)
		if err != nil {
			return err
		}
		if data == nil {
			data = map[string]interface{}{}
		}
		meetings := common.GetSlice(data, "meetings")
		runtime.OutFormat(data, &output.Meta{Count: len(meetings)}, func(w io.Writer) {
			if len(meetings) == 0 {
				fmt.Fprintln(w, "No ongoing meetings.")
				return
			}
			for _, raw := range meetings {
				m, _ := raw.(map[string]interface{})
				if m == nil {
					continue
				}
				title := common.GetString(m, "meeting_title")
				if title == "" {
					title = "(no title)"
				}
				fmt.Fprintf(w, "%s\n", title)
				if id := common.GetString(m, "meeting_id"); id != "" {
					fmt.Fprintf(w, "  Meeting ID: %s\n", id)
				}
				if no := common.GetString(m, "meeting_no"); no != "" {
					fmt.Fprintf(w, "  Meeting No: %s\n", no)
				}
			}
		})
		return nil
	},
}

func buildActiveMeetingsParams(runtime *common.RuntimeContext) map[string]interface{} {
	params := map[string]interface{}{}
	if runtime.IsBot() {
		if userID := strings.TrimSpace(runtime.Str("user-id")); userID != "" {
			params["user_id"] = userID
		}
	}
	return params
}
