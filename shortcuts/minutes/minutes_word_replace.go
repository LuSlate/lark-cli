// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package minutes

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/internal/validate"
	"github.com/larksuite/cli/shortcuts/common"
)

const (
	minutesWordReplaceNoEditPermission = 40005
	minutesWordReplaceOthersEditing    = 40110
)

type transcriptWordReplace struct {
	SourceWord string `json:"source_word"`
	TargetWord string `json:"target_word"`
}

// MinutesWordReplace batch-replaces words in a minute's transcript.
var MinutesWordReplace = common.Shortcut{
	Service:     "minutes",
	Command:     "+word-replace",
	Description: "Batch replace words in a minute's transcript",
	Risk:        "write",
	Scopes:      []string{"minutes:minutes:update"},
	AuthTypes:   []string{"user"},
	HasFormat:   true,
	Flags: []common.Flag{
		{Name: "minute-token", Desc: "minute token", Required: true},
		{
			Name:     "replace-words",
			Desc:     `JSON array of replacements, e.g. [{"source_word":"old","target_word":"new"}]`,
			Required: true,
			Input:    []string{common.File, common.Stdin},
		},
	},
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		minuteToken := strings.TrimSpace(runtime.Str("minute-token"))
		if minuteToken == "" {
			return output.ErrValidation("--minute-token is required")
		}
		if err := validate.ResourceName(minuteToken, "--minute-token"); err != nil {
			return output.ErrValidation("%s", err)
		}
		if _, err := parseReplaceWords(runtime.Str("replace-words")); err != nil {
			return output.ErrValidation("--replace-words: %s", err)
		}
		return nil
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		minuteToken := strings.TrimSpace(runtime.Str("minute-token"))
		replaceWords, _ := parseReplaceWords(runtime.Str("replace-words"))
		return common.NewDryRunAPI().
			PUT(fmt.Sprintf("/open-apis/minutes/v1/minutes/%s/transcript/word", validate.EncodePathSegment(minuteToken))).
			Body(map[string]interface{}{
				"minute_token":  minuteToken,
				"replace_words": replaceWords,
			})
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		minuteToken := strings.TrimSpace(runtime.Str("minute-token"))
		replaceWords, err := parseReplaceWords(runtime.Str("replace-words"))
		if err != nil {
			return output.ErrValidation("--replace-words: %s", err)
		}

		body := map[string]interface{}{
			"minute_token":  minuteToken,
			"replace_words": replaceWords,
		}

		_, err = runtime.CallAPI(http.MethodPut,
			fmt.Sprintf("/open-apis/minutes/v1/minutes/%s/transcript/word", validate.EncodePathSegment(minuteToken)),
			nil, body)
		if err != nil {
			return minutesWordReplaceError(err, minuteToken)
		}

		outData := map[string]interface{}{
			"minute_token":  minuteToken,
			"replace_words": replaceWords,
		}

		runtime.OutFormat(outData, nil, nil)
		return nil
	},
}

func parseReplaceWords(raw string) ([]map[string]string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil, errors.New("value is required")
	}

	var items []transcriptWordReplace
	if err := json.Unmarshal([]byte(raw), &items); err != nil {
		return nil, fmt.Errorf("must be a JSON array of {source_word,target_word} objects: %v", err)
	}
	if len(items) == 0 {
		return nil, errors.New("must include at least one replacement")
	}

	replaceWords := make([]map[string]string, 0, len(items))
	seen := make(map[string]struct{}, len(items))
	for i, item := range items {
		sourceWord := strings.TrimSpace(item.SourceWord)
		if sourceWord == "" {
			return nil, fmt.Errorf("item %d: source_word is required", i)
		}
		if _, exists := seen[sourceWord]; exists {
			return nil, fmt.Errorf("duplicate source_word %q", sourceWord)
		}
		seen[sourceWord] = struct{}{}
		replaceWords = append(replaceWords, map[string]string{
			"source_word": sourceWord,
			"target_word": item.TargetWord,
		})
	}
	return replaceWords, nil
}

func minutesWordReplaceError(err error, minuteToken string) error {
	var exitErr *output.ExitError
	if !errors.As(err, &exitErr) || exitErr.Detail == nil {
		return err
	}

	switch exitErr.Detail.Code {
	case minutesWordReplaceNoEditPermission:
		return &output.ExitError{
			Code: output.ExitAPI,
			Detail: &output.ErrDetail{
				Type:    "no_edit_permission",
				Code:    minutesWordReplaceNoEditPermission,
				Message: fmt.Sprintf("No edit permission for minute %q: cannot replace transcript words.", minuteToken),
				Hint:    "Ask the minute owner for minute edit permission",
				Detail:  exitErr.Detail.Detail,
			},
			Err: err,
		}
	case minutesWordReplaceOthersEditing:
		return &output.ExitError{
			Code: output.ExitAPI,
			Detail: &output.ErrDetail{
				Type:    "others_are_editing",
				Code:    minutesWordReplaceOthersEditing,
				Message: fmt.Sprintf("Minute %q transcript is being edited by someone else.", minuteToken),
				Hint:    "Wait until the other editor finishes, then retry",
				Detail:  exitErr.Detail.Detail,
			},
			Err: err,
		}
	}

	return err
}
