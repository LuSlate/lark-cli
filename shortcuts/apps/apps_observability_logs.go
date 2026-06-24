// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"strings"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/shortcuts/common"
)

const (
	defaultAppsLogEnv      = "online"
	logSearchEndpoint      = "search_logs"
	resolveStackEndpoint   = "resolve_stack_trace"
	sourceStackStatusOK    = "resolved"
	sourceStackStatusError = "unresolved"
)

// AppsLogList searches online app logs with observability filters.
var AppsLogList = common.Shortcut{
	Service:     appsService,
	Command:     "+log-list",
	Description: "Search online app logs with observability filters",
	Risk:        "read",
	Tips: []string{
		"Example: lark-cli apps +log-list --app-id <app_id> --level error --keyword timeout --since 1h",
		"Tip: use --page-token from the response to fetch the next page.",
	},
	Scopes:    []string{"spark:app:read"},
	AuthTypes: []string{"user"},
	HasFormat: true,
	Flags: []common.Flag{
		{Name: "app-id", Desc: "app ID whose online logs should be searched", Required: true},
		{Name: "env", Default: defaultAppsLogEnv, Desc: "observability environment; only online is supported"},
		{Name: "since", Desc: "start time, relative duration (30s, 5m, 0.5h, 2h, 3d, 1w), local date/time, or RFC3339"},
		{Name: "until", Desc: "end time, relative duration (30s, 5m, 0.5h, 2h, 3d, 1w), local date/time, or RFC3339"},
		{Name: "level", Type: "string_array", Desc: "log level filter; repeatable, one of DEBUG, INFO, WARN, ERROR (case-insensitive)"},
		{Name: "log-id", Type: "string_array", Desc: "log ID filter; repeatable"},
		{Name: "trace-id", Type: "string_array", Desc: "trace ID filter; repeatable"},
		{Name: "keyword", Desc: "keyword filter applied by the log search backend"},
		{Name: "module", Desc: "module name filter"},
		{Name: "user-id", Desc: "end user ID filter"},
		{Name: "page", Desc: "frontend page or route filter"},
		{Name: "api", Desc: "API path/name filter"},
		{Name: "min-duration", Type: "int", Desc: "minimum duration in milliseconds; must be non-negative"},
		{Name: "max-duration", Type: "int", Desc: "maximum duration in milliseconds; must be non-negative and >= --min-duration"},
		{Name: "page-size", Type: "int", Default: fmt.Sprintf("%d", defaultAppsPageSize), Desc: "page size, 1..100"},
		{Name: "page-token", Desc: "pagination cursor from a previous log search response"},
	},
	Validate: func(ctx context.Context, rctx *common.RuntimeContext) error {
		if _, err := requireAppID(rctx.Str("app-id")); err != nil {
			return err
		}
		_, err := buildLogSearchBody(rctx)
		return err
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		body, _ := buildLogSearchBody(rctx)
		return common.NewDryRunAPI().
			POST(logSearchPath(rctx.Str("app-id"))).
			Desc("Search online app logs").
			Body(body)
	},
	Execute: func(ctx context.Context, rctx *common.RuntimeContext) error {
		appID, _ := requireAppID(rctx.Str("app-id"))
		body, err := buildLogSearchBody(rctx)
		if err != nil {
			return err
		}
		data, err := rctx.CallAPITyped("POST", logSearchPath(appID), nil, body)
		if err != nil {
			return withAppsHint(err, appIDListHint)
		}
		out := normalizeLogSearchResponse(data)
		rctx.OutFormat(out, nil, func(w io.Writer) {
			output.PrintTable(w, logListRows(out.Items))
		})
		return nil
	},
}

// AppsLogGet fetches one log by log ID through the search_logs endpoint.
var AppsLogGet = common.Shortcut{
	Service:     appsService,
	Command:     "+log-get",
	Description: "Get one online app log by log ID",
	Risk:        "read",
	Tips: []string{
		"Example: lark-cli apps +log-get --app-id <app_id> --log-id <log_id>",
		"Tip: +log-get searches online logs with limit=1; use +log-list first if the log ID is unknown.",
	},
	Scopes:    []string{"spark:app:read"},
	AuthTypes: []string{"user"},
	HasFormat: true,
	Flags: []common.Flag{
		{Name: "app-id", Desc: "app ID whose online logs should be searched", Required: true},
		{Name: "log-id", Desc: "log ID to fetch", Required: true},
		{Name: "env", Default: defaultAppsLogEnv, Desc: "observability environment; only online is supported"},
	},
	Validate: func(ctx context.Context, rctx *common.RuntimeContext) error {
		if _, err := requireAppID(rctx.Str("app-id")); err != nil {
			return err
		}
		if strings.TrimSpace(rctx.Str("log-id")) == "" {
			return appsValidationParamError("--log-id", "--log-id is required")
		}
		return validateObservabilityEnv(rctx.Str("env"))
	},
	DryRun: func(ctx context.Context, rctx *common.RuntimeContext) *common.DryRunAPI {
		return common.NewDryRunAPI().
			POST(logSearchPath(rctx.Str("app-id"))).
			Desc("Search online app logs by log ID").
			Body(buildLogGetSearchBody(rctx))
	},
	Execute: func(ctx context.Context, rctx *common.RuntimeContext) error {
		appID, _ := requireAppID(rctx.Str("app-id"))
		data, err := rctx.CallAPITyped("POST", logSearchPath(appID), nil, buildLogGetSearchBody(rctx))
		if err != nil {
			return withAppsHint(err, appIDListHint)
		}
		out := normalizeLogSearchResponse(data)
		if len(out.Items) == 0 {
			return appsFailedPreconditionParamError("--log-id", "log not found").
				WithHint("verify --log-id and --env online")
		}
		log := out.Items[0]
		enrichLogSourceStack(rctx, appID, log)
		rctx.OutFormat(log, nil, func(w io.Writer) {
			output.PrintTable(w, []map[string]interface{}{logSummaryRow(log)})
		})
		return nil
	},
}

type logSearchOutput struct {
	Items     []map[string]interface{} `json:"items"`
	PageToken string                   `json:"page_token,omitempty"`
	HasMore   bool                     `json:"has_more"`
}

func logSearchPath(appID string) string {
	return appScopedPath(appID, logSearchEndpoint)
}

func resolveStackPath(appID string) string {
	return appScopedPath(appID, resolveStackEndpoint)
}

func buildLogSearchBody(rctx *common.RuntimeContext) (map[string]interface{}, error) {
	env := strings.TrimSpace(rctx.Str("env"))
	if env == "" {
		env = defaultAppsLogEnv
	}
	if err := validateObservabilityEnv(env); err != nil {
		return nil, err
	}
	if err := validateAppsPageSize(rctx.Int("page-size")); err != nil {
		return nil, err
	}
	body := map[string]interface{}{
		"app_env": appsObservabilityBackendEnv,
		"limit":   rctx.Int("page-size"),
	}
	if token := strings.TrimSpace(rctx.Str("page-token")); token != "" {
		body["page_token"] = token
	}
	if err := addLogSearchTimeRange(body, rctx); err != nil {
		return nil, err
	}
	filter, err := buildLogSearchFilter(rctx)
	if err != nil {
		return nil, err
	}
	if len(filter) > 0 {
		body["filter"] = filter
	}
	return body, nil
}

func buildLogGetSearchBody(rctx *common.RuntimeContext) map[string]interface{} {
	return map[string]interface{}{
		"app_env": appsObservabilityBackendEnv,
		"limit":   1,
		"filter": map[string]interface{}{
			"log_ids": []string{strings.TrimSpace(rctx.Str("log-id"))},
		},
	}
}

func addLogSearchTimeRange(body map[string]interface{}, rctx *common.RuntimeContext) error {
	since, until, hasSince, hasUntil, err := parseAppsTimeRange("--since", rctx.Str("since"), "--until", rctx.Str("until"))
	if err != nil {
		return err
	}
	if hasSince {
		body["start_timestamp_ns"] = nsNumber(since)
	}
	if hasUntil {
		body["end_timestamp_ns"] = nsNumber(until)
	}
	return nil
}

func buildLogSearchFilter(rctx *common.RuntimeContext) (map[string]interface{}, error) {
	filter := make(map[string]interface{})
	levels, err := normalizeLogLevels(rctx.StrArray("level"))
	if err != nil {
		return nil, err
	}
	if len(levels) > 0 {
		filter["levels"] = levels
	}
	if logIDs := cleanRepeatedStrings(rctx.StrArray("log-id")); len(logIDs) > 0 {
		filter["log_ids"] = logIDs
	}
	if traceIDs := cleanRepeatedStrings(rctx.StrArray("trace-id")); len(traceIDs) > 0 {
		filter["trace_ids"] = traceIDs
	}
	addTrimmedLogFilterString(filter, "keyword", rctx.Str("keyword"))
	addTrimmedLogFilterStrings(filter, "modules", rctx.Str("module"))
	addTrimmedLogFilterStrings(filter, "user_ids", rctx.Str("user-id"))
	addTrimmedLogFilterStrings(filter, "pages", rctx.Str("page"))
	addTrimmedLogFilterStrings(filter, "apis", rctx.Str("api"))
	if err := addDurationFilters(filter, rctx); err != nil {
		return nil, err
	}
	return filter, nil
}

func addTrimmedLogFilterStrings(filter map[string]interface{}, key, value string) {
	if value = strings.TrimSpace(value); value != "" {
		filter[key] = []string{value}
	}
}

func addTrimmedLogFilterString(filter map[string]interface{}, key, value string) {
	if value = strings.TrimSpace(value); value != "" {
		filter[key] = value
	}
}

func addDurationFilters(filter map[string]interface{}, rctx *common.RuntimeContext) error {
	hasMin := rctx.Changed("min-duration")
	hasMax := rctx.Changed("max-duration")
	minDuration := rctx.Int("min-duration")
	maxDuration := rctx.Int("max-duration")
	if hasMin {
		if minDuration < 0 {
			return appsValidationParamError("--min-duration", "--min-duration must be non-negative")
		}
		filter["min_duration_ms"] = minDuration
	}
	if hasMax {
		if maxDuration < 0 {
			return appsValidationParamError("--max-duration", "--max-duration must be non-negative")
		}
		filter["max_duration_ms"] = maxDuration
	}
	if hasMin && hasMax && minDuration > maxDuration {
		return appsValidationParamError("--max-duration", "--max-duration must be greater than or equal to --min-duration")
	}
	return nil
}

func normalizeLogLevels(values []string) ([]string, error) {
	values = cleanRepeatedStrings(values)
	if len(values) == 0 {
		return nil, nil
	}
	out := make([]string, 0, len(values))
	for _, value := range values {
		level := strings.ToUpper(strings.TrimSpace(value))
		switch level {
		case "DEBUG", "INFO", "WARN", "ERROR":
			out = append(out, level)
		default:
			return nil, appsValidationParamError("--level", "--level must be one of DEBUG, INFO, WARN, ERROR")
		}
	}
	return out, nil
}

func normalizeLogSearchResponse(data map[string]interface{}) logSearchOutput {
	items := firstMapSlice(data, "items", "log_items", "logItems")
	normalized := make([]map[string]interface{}, 0, len(items))
	for _, item := range items {
		normalized = append(normalized, normalizeLogItem(item))
	}
	return logSearchOutput{
		Items:     normalized,
		PageToken: firstLogString(data, "page_token", "next_page_token", "pageToken", "nextPageToken"),
		HasMore:   firstLogBool(data, "has_more", "hasMore"),
	}
}

func normalizeLogItem(item map[string]interface{}) map[string]interface{} {
	out := cloneMap(item)
	copyFirstAlias(out, item, "log_id", "log_id", "id", "logID", "logId")
	copyFirstAlias(out, item, "trace_id", "trace_id", "traceID", "traceId")
	copyFirstAlias(out, item, "timestamp_ns", "timestamp_ns", "timestampNs")
	copyFirstAlias(out, item, "severity_text", "severity_text", "severityText")
	if level := firstItemString(out, "level", "severity_text", "severityText"); level != "" {
		out["level"] = level
	}
	return out
}

func firstMapSlice(data map[string]interface{}, keys ...string) []map[string]interface{} {
	for _, key := range keys {
		raw, ok := data[key]
		if !ok {
			continue
		}
		switch items := raw.(type) {
		case []map[string]interface{}:
			return items
		case []interface{}:
			out := make([]map[string]interface{}, 0, len(items))
			for _, item := range items {
				if m, ok := item.(map[string]interface{}); ok {
					out = append(out, m)
				}
			}
			return out
		}
	}
	return nil
}

func firstLogString(data map[string]interface{}, keys ...string) string {
	for _, key := range keys {
		if s, ok := data[key].(string); ok && strings.TrimSpace(s) != "" {
			return s
		}
	}
	return ""
}

func firstLogBool(data map[string]interface{}, keys ...string) bool {
	for _, key := range keys {
		if b, ok := data[key].(bool); ok {
			return b
		}
	}
	return false
}

func copyFirstAlias(dst, src map[string]interface{}, canonical string, keys ...string) {
	for _, key := range keys {
		if value, ok := src[key]; ok {
			dst[canonical] = value
			return
		}
	}
}

func cloneMap(src map[string]interface{}) map[string]interface{} {
	dst := make(map[string]interface{}, len(src)+4)
	for key, value := range src {
		dst[key] = value
	}
	return dst
}

func logListRows(items []map[string]interface{}) []map[string]interface{} {
	rows := make([]map[string]interface{}, 0, len(items))
	for _, item := range items {
		rows = append(rows, logSummaryRow(item))
	}
	return rows
}

func logSummaryRow(item map[string]interface{}) map[string]interface{} {
	return map[string]interface{}{
		"log_id":       item["log_id"],
		"level":        firstItemString(item, "level", "severity_text"),
		"trace_id":     item["trace_id"],
		"timestamp_ns": item["timestamp_ns"],
		"message":      firstItemString(item, "message", "body"),
	}
}

func firstItemString(item map[string]interface{}, keys ...string) string {
	for _, key := range keys {
		if s, ok := item[key].(string); ok && strings.TrimSpace(s) != "" {
			return s
		}
	}
	return ""
}

func enrichLogSourceStack(rctx *common.RuntimeContext, appID string, log map[string]interface{}) {
	if !shouldResolveSourceStack(log) {
		return
	}
	body, ok := extractSourceStackResolveBody(log)
	if !ok {
		log["source_stack_status"] = sourceStackStatusError
		log["source_stack_reason"] = "source stack fields incomplete"
		return
	}
	data, err := rctx.CallAPITyped("POST", resolveStackPath(appID), nil, body)
	if err != nil {
		if _, typed := errs.ProblemOf(err); typed {
			log["source_stack_status"] = sourceStackStatusError
			log["source_stack_reason"] = "resolve_stack_trace failed"
		}
		return
	}
	stack := firstLogValue(data, "source_stack", "sourceStack", "frames")
	if stack == nil {
		stack = data
	}
	log["source_stack_status"] = sourceStackStatusOK
	log["source_stack"] = stack
}

func shouldResolveSourceStack(log map[string]interface{}) bool {
	level := strings.ToUpper(firstItemString(log, "level", "severity_text", "severityText"))
	if level != "ERROR" {
		return false
	}
	if _, ok := extractSourceStackResolveBody(log); ok {
		return true
	}
	return hasFrontendSourceMapSignal(log)
}

func hasFrontendSourceMapSignal(value interface{}) bool {
	switch v := value.(type) {
	case map[string]interface{}:
		for key, nested := range v {
			if isSourceMapSignal(key) || hasFrontendSourceMapSignal(nested) {
				return true
			}
		}
	case []interface{}:
		for _, nested := range v {
			if hasFrontendSourceMapSignal(nested) {
				return true
			}
		}
	case string:
		return isSourceMapSignal(v) || strings.Contains(strings.ToLower(v), ".js")
	}
	return false
}

func isSourceMapSignal(value string) bool {
	normalized := strings.NewReplacer("-", "_", " ", "_").Replace(strings.ToLower(value))
	return strings.Contains(normalized, "source_map") || strings.Contains(normalized, "sourcemap")
}

func extractSourceStackResolveBody(log map[string]interface{}) (map[string]interface{}, bool) {
	sources := []map[string]interface{}{log}
	if attrs, ok := log["attributes"].(map[string]interface{}); ok {
		sources = append([]map[string]interface{}{attrs}, sources...)
	}
	if bodyMap, ok := log["body"].(map[string]interface{}); ok {
		sources = append([]map[string]interface{}{bodyMap}, sources...)
	}
	commitID := firstStringInMaps(sources, "commit_id", "commitID", "commitId")
	prefix := firstStringInMaps(sources, "source_map_file_prefix", "sourceMapFilePrefix", "source_map_prefix", "sourceMapPrefix")
	frames := firstFramesInMaps(sources, "frames", "stack_frames", "stackFrames", "source_stack_frames", "sourceStackFrames")
	if commitID == "" || prefix == "" || len(frames) == 0 {
		return nil, false
	}
	return map[string]interface{}{
		"commit_id":              commitID,
		"source_map_file_prefix": prefix,
		"frames":                 frames,
	}, true
}

func firstStringInMaps(sources []map[string]interface{}, keys ...string) string {
	for _, source := range sources {
		if s := firstLogString(source, keys...); s != "" {
			return s
		}
	}
	return ""
}

func firstFramesInMaps(sources []map[string]interface{}, keys ...string) []interface{} {
	for _, source := range sources {
		for _, key := range keys {
			frames := normalizeFrames(source[key])
			if len(frames) > 0 {
				return frames
			}
		}
	}
	return nil
}

func normalizeFrames(raw interface{}) []interface{} {
	switch frames := raw.(type) {
	case []interface{}:
		out := make([]interface{}, 0, len(frames))
		for _, frame := range frames {
			if isNonEmptyFrame(frame) {
				out = append(out, frame)
			}
		}
		return out
	case []map[string]interface{}:
		out := make([]interface{}, 0, len(frames))
		for _, frame := range frames {
			if len(frame) > 0 {
				out = append(out, frame)
			}
		}
		return out
	case string:
		return parseFrameString(frames)
	default:
		return nil
	}
}

func isNonEmptyFrame(frame interface{}) bool {
	switch f := frame.(type) {
	case map[string]interface{}:
		return len(f) > 0
	case map[string]string:
		return len(f) > 0
	case string:
		return strings.TrimSpace(f) != ""
	default:
		return frame != nil
	}
}

func parseFrameString(raw string) []interface{} {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	var decoded []interface{}
	if err := json.Unmarshal([]byte(raw), &decoded); err == nil {
		return normalizeFrames(decoded)
	}
	lines := strings.Split(raw, "\n")
	out := make([]interface{}, 0, len(lines))
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line != "" {
			out = append(out, map[string]interface{}{"raw": line})
		}
	}
	return out
}

func firstLogValue(data map[string]interface{}, keys ...string) interface{} {
	for _, key := range keys {
		if value, ok := data[key]; ok {
			return value
		}
	}
	return nil
}
