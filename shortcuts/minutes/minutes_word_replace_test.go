// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package minutes

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"testing"

	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/httpmock"
	"github.com/larksuite/cli/internal/output"
	"github.com/spf13/cobra"
)

const minutesWordReplaceTestToken = "obcnexampleminute"

func TestMinutesWordReplace_Validate(t *testing.T) {
	t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())
	f, _, _, _ := cmdutil.TestFactory(t, defaultConfig())
	tests := []struct {
		name    string
		args    []string
		wantErr string
	}{
		{
			name:    "missing minute token",
			args:    []string{"+word-replace", "--replace-words", `[{"source_word":"a","target_word":"b"}]`, "--as", "user"},
			wantErr: "required flag(s) \"minute-token\" not set",
		},
		{
			name:    "missing replace words",
			args:    []string{"+word-replace", "--minute-token", "obcn123456", "--as", "user"},
			wantErr: "required flag(s) \"replace-words\" not set",
		},
		{
			name:    "invalid json",
			args:    []string{"+word-replace", "--minute-token", "obcn123456", "--replace-words", "not-json", "--as", "user"},
			wantErr: "JSON array",
		},
		{
			name:    "empty source word",
			args:    []string{"+word-replace", "--minute-token", "obcn123456", "--replace-words", `[{"source_word":"","target_word":"b"}]`, "--as", "user"},
			wantErr: "source_word is required",
		},
		{
			name:    "duplicate source word",
			args:    []string{"+word-replace", "--minute-token", "obcn123456", "--replace-words", `[{"source_word":"a","target_word":"b"},{"source_word":"a","target_word":"c"}]`, "--as", "user"},
			wantErr: "duplicate source_word",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			parent := &cobra.Command{Use: "minutes"}
			MinutesWordReplace.Mount(parent, f)
			parent.SetArgs(tt.args)
			parent.SilenceErrors = true
			parent.SilenceUsage = true
			err := parent.Execute()
			if err == nil {
				t.Fatalf("expected error, got nil")
			}
			if !strings.Contains(err.Error(), tt.wantErr) {
				t.Errorf("error should contain %q, got: %s", tt.wantErr, err.Error())
			}
		})
	}
}

func TestMinutesWordReplace_DryRun(t *testing.T) {
	t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())
	f, stdout, _, _ := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)

	err := mountAndRun(t, MinutesWordReplace, []string{
		"+word-replace",
		"--minute-token", minutesWordReplaceTestToken,
		"--replace-words", `[{"source_word":"foo","target_word":"bar"}]`,
		"--dry-run", "--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	out := stdout.String()
	if !strings.Contains(out, "PUT") {
		t.Errorf("expected PUT method, got:\n%s", out)
	}
	if !strings.Contains(out, "/open-apis/minutes/v1/minutes/"+minutesWordReplaceTestToken+"/transcript/word") {
		t.Errorf("expected word endpoint, got:\n%s", out)
	}
	if !strings.Contains(out, "foo") || !strings.Contains(out, "bar") {
		t.Errorf("expected replace_words in body, got:\n%s", out)
	}
}

func TestMinutesWordReplace_Execute(t *testing.T) {
	t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())
	f, stdout, _, reg := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)

	reg.Register(&httpmock.Stub{
		Method: http.MethodPut,
		URL:    "/open-apis/minutes/v1/minutes/" + minutesWordReplaceTestToken + "/transcript/word",
		Body: map[string]interface{}{
			"code": 0,
			"msg":  "ok",
			"data": map[string]interface{}{},
		},
	})

	err := mountAndRun(t, MinutesWordReplace, []string{
		"+word-replace",
		"--minute-token", minutesWordReplaceTestToken,
		"--replace-words", `[{"source_word":"foo","target_word":"bar"}]`,
		"--format", "json", "--as", "user",
	}, f, stdout)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var envelope struct {
		Data struct {
			MinuteToken  string `json:"minute_token"`
			ReplaceWords []struct {
				SourceWord string `json:"source_word"`
				TargetWord string `json:"target_word"`
			} `json:"replace_words"`
		} `json:"data"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("unmarshal stdout: %v", err)
	}
	if envelope.Data.MinuteToken != minutesWordReplaceTestToken {
		t.Errorf("data.minute_token = %q, want %q", envelope.Data.MinuteToken, minutesWordReplaceTestToken)
	}
	if len(envelope.Data.ReplaceWords) != 1 || envelope.Data.ReplaceWords[0].SourceWord != "foo" || envelope.Data.ReplaceWords[0].TargetWord != "bar" {
		t.Errorf("data.replace_words = %#v, want foo->bar", envelope.Data.ReplaceWords)
	}
}

func TestMinutesWordReplace_NoEditPermission(t *testing.T) {
	t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())
	f, stdout, _, reg := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)

	reg.Register(&httpmock.Stub{
		Method: http.MethodPut,
		URL:    "/open-apis/minutes/v1/minutes/" + minutesWordReplaceTestToken + "/transcript/word",
		Body: map[string]interface{}{
			"code": minutesWordReplaceNoEditPermission,
			"msg":  "permission deny",
		},
	})

	err := mountAndRun(t, MinutesWordReplace, []string{
		"+word-replace",
		"--minute-token", minutesWordReplaceTestToken,
		"--replace-words", `[{"source_word":"foo","target_word":"bar"}]`,
		"--format", "json", "--as", "user",
	}, f, stdout)
	if err == nil {
		t.Fatal("expected no-edit-permission error, got nil")
	}

	var exitErr *output.ExitError
	if !errors.As(err, &exitErr) {
		t.Fatalf("expected *output.ExitError, got %T: %v", err, err)
	}
	if exitErr.Detail == nil || exitErr.Detail.Type != "no_edit_permission" {
		t.Fatalf("expected no_edit_permission detail, got %#v", exitErr.Detail)
	}
}

func TestMinutesWordReplace_OthersAreEditing(t *testing.T) {
	t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())
	f, stdout, _, reg := cmdutil.TestFactory(t, defaultConfig())
	warmTokenCache(t)

	reg.Register(&httpmock.Stub{
		Method: http.MethodPut,
		URL:    "/open-apis/minutes/v1/minutes/" + minutesWordReplaceTestToken + "/transcript/word",
		Body: map[string]interface{}{
			"code": minutesWordReplaceOthersEditing,
			"msg":  "others are editing",
		},
	})

	err := mountAndRun(t, MinutesWordReplace, []string{
		"+word-replace",
		"--minute-token", minutesWordReplaceTestToken,
		"--replace-words", `[{"source_word":"foo","target_word":"bar"}]`,
		"--format", "json", "--as", "user",
	}, f, stdout)
	if err == nil {
		t.Fatal("expected others-are-editing error, got nil")
	}

	var exitErr *output.ExitError
	if !errors.As(err, &exitErr) {
		t.Fatalf("expected *output.ExitError, got %T: %v", err, err)
	}
	if exitErr.Detail == nil || exitErr.Detail.Type != "others_are_editing" {
		t.Fatalf("expected others_are_editing detail, got %#v", exitErr.Detail)
	}
}
