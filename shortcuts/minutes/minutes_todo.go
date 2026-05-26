// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package minutes

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/internal/validate"
	"github.com/larksuite/cli/shortcuts/common"
)

// minuteTodoOp describes the resolved single-todo operation derived from flags.
type minuteTodoOp struct {
	operation string                 // add | update | delete
	item      map[string]interface{} // the single todo_items entry sent to the API
}

// MinutesTodo adds, updates, or deletes a single todo item on a minute.
var MinutesTodo = common.Shortcut{
	Service:     "minutes",
	Command:     "+todo",
	Description: "Add, update, or delete a single todo item on a minute",
	Risk:        "write",
	Scopes:      []string{"minutes:minutes:update"},
	AuthTypes:   []string{"user"},
	HasFormat:   true,
	Flags: []common.Flag{
		{Name: "minute-token", Desc: "minute token (required)", Required: true},
		{Name: "todo", Desc: "todo plain-text content; required (with --is-done) to add or update", Input: []string{common.File, common.Stdin}},
		{Name: "is-done", Type: "bool", Desc: "completion flag; required together with --todo"},
		{Name: "todo-id", Desc: "id of an existing todo; provide to update (with --todo) or delete (without --todo); omit to add"},
	},
	Tips: []string{
		"Add a todo: `--todo \"...\" --is-done=false`.",
		"Update a todo: `--todo-id <id> --todo \"...\" --is-done`.",
		"Delete a todo: `--todo-id <id>` (omit --todo).",
		"`content` is plain text only; markdown formatting is not supported.",
		"Use `lark-cli vc +notes --minute-tokens <token>` to read current todos before writing.",
	},
	Validate: func(ctx context.Context, runtime *common.RuntimeContext) error {
		minuteToken := runtime.Str("minute-token")
		if minuteToken == "" {
			return output.ErrValidation("--minute-token is required")
		}
		if err := validate.ResourceName(minuteToken, "--minute-token"); err != nil {
			return output.ErrValidation("%s", err)
		}
		if _, err := resolveMinuteTodoOp(runtime); err != nil {
			return err
		}
		return nil
	},
	DryRun: func(ctx context.Context, runtime *common.RuntimeContext) *common.DryRunAPI {
		return common.NewDryRunAPI().
			PUT(fmt.Sprintf("/open-apis/minutes/v1/minutes/%s/todo", validate.EncodePathSegment(runtime.Str("minute-token")))).
			Body(map[string]interface{}{
				"todo_items": "<todo_items array>",
			})
	},
	Execute: func(ctx context.Context, runtime *common.RuntimeContext) error {
		minuteToken := runtime.Str("minute-token")
		op, err := resolveMinuteTodoOp(runtime)
		if err != nil {
			return err
		}

		path := fmt.Sprintf("/open-apis/minutes/v1/minutes/%s/todo", validate.EncodePathSegment(minuteToken))
		body := map[string]interface{}{
			"todo_items": []interface{}{op.item},
		}
		if _, err := runtime.CallAPI(http.MethodPut, path, nil, body); err != nil {
			return err
		}

		// Intentionally omit the todo id from the output: users never see it.
		runtime.OutFormat(map[string]interface{}{
			"minute_token": minuteToken,
			"operation":    op.operation,
			"updated":      true,
		}, nil, nil)
		return nil
	},
}

func resolveMinuteTodoOp(runtime *common.RuntimeContext) (*minuteTodoOp, error) {
	todo := strings.TrimSpace(runtime.Str("todo"))
	todoID := strings.TrimSpace(runtime.Str("todo-id"))
	hasTodo := todo != ""
	hasTodoID := todoID != ""
	hasIsDone := runtime.Changed("is-done")

	item := map[string]interface{}{}
	if hasTodoID {
		item["todo_id"] = todoID
	}

	switch {
	case hasTodo:
		// add or update: content and is_done must appear together
		if !hasIsDone {
			return nil, output.ErrValidation("--todo requires --is-done")
		}
		item["content"] = todo
		item["is_done"] = runtime.Bool("is-done")
		if hasTodoID {
			return &minuteTodoOp{operation: "update", item: item}, nil
		}
		return &minuteTodoOp{operation: "add", item: item}, nil
	case hasTodoID:
		// delete: only the id is needed; content/is_done are not allowed
		if hasIsDone {
			return nil, output.ErrValidation("--is-done cannot be used to delete a todo (omit it, and provide only --todo-id)")
		}
		return &minuteTodoOp{operation: "delete", item: item}, nil
	default:
		return nil, output.ErrValidation("provide --todo (with --is-done) to add/update, or --todo-id alone to delete")
	}
}
