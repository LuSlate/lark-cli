// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"strconv"
	"strings"
	"time"

	"github.com/larksuite/cli/internal/validate"
)

const (
	defaultAppsPageSize = 50
	maxAppsPageSize     = 100
)

func appScopedPath(appID, suffix string) string {
	base := apiBasePath + "/apps/" + validate.EncodePathSegment(strings.TrimSpace(appID))
	suffix = strings.TrimLeft(strings.TrimSpace(suffix), "/")
	if suffix == "" {
		return base
	}
	return base + "/" + suffix
}

func validateObservabilityEnv(env string) error {
	switch strings.TrimSpace(env) {
	case "", "online":
		return nil
	default:
		return appsValidationParamError("--env", "observability commands only support --env online (got %q)", env).
			WithHint("only online is supported; omit --env to use the default online environment")
	}
}

func validateEnvVarEnv(env string) error {
	switch strings.TrimSpace(env) {
	case "dev", "online":
		return nil
	default:
		return appsValidationParamError("--env", "env var commands only support --env dev or --env online (got %q)", env)
	}
}

func validateAppsPageSize(n int) error {
	if n < 1 || n > maxAppsPageSize {
		return appsValidationParamError("--page-size", "--page-size must be between 1 and %d", maxAppsPageSize)
	}
	return nil
}

func cleanRepeatedStrings(values []string) []string {
	if len(values) == 0 {
		return nil
	}
	seen := make(map[string]struct{}, len(values))
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" {
			continue
		}
		if _, ok := seen[value]; ok {
			continue
		}
		seen[value] = struct{}{}
		out = append(out, value)
	}
	return out
}

func parseAppsTimeRange(sinceName, sinceRaw, untilName, untilRaw string) (time.Time, time.Time, bool, bool, error) {
	var since, until time.Time
	var hasSince, hasUntil bool
	now := time.Now()
	if strings.TrimSpace(sinceRaw) != "" {
		parsed, err := parseAppsTimeFlag(sinceName, sinceRaw, now)
		if err != nil {
			return time.Time{}, time.Time{}, false, false, err
		}
		since = parsed
		hasSince = true
	}
	if strings.TrimSpace(untilRaw) != "" {
		parsed, err := parseAppsTimeFlag(untilName, untilRaw, now)
		if err != nil {
			return since, time.Time{}, hasSince, false, err
		}
		until = parsed
		hasUntil = true
	}
	if hasSince && hasUntil && since.After(until) {
		return since, until, true, true, appsValidationParamError(untilName, "%s must be greater than or equal to %s", untilName, sinceName)
	}
	return since, until, hasSince, hasUntil, nil
}

func parseAppsTimeFlag(param, raw string, now time.Time) (time.Time, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return time.Time{}, appsValidationParamError(param, "%s is required", param)
	}
	if d, ok := parseAppsRelativeDuration(raw); ok {
		return now.Add(-d), nil
	}
	if t, err := time.Parse(time.RFC3339Nano, raw); err == nil {
		return t, nil
	}
	for _, layout := range []string{
		"2006-01-02",
		"2006-01-02T15:04:05",
		"2006-01-02T15:04:05.000",
	} {
		if t, err := time.ParseInLocation(layout, raw, time.Local); err == nil {
			return t, nil
		}
	}
	return time.Time{}, appsValidationParamError(param, "invalid %s %q: expected relative duration (30s, 5m, 2h, 3d, 1w), YYYY-MM-DD, local YYYY-MM-DDTHH:mm:ss(.SSS), or RFC3339", param, raw)
}

func parseAppsRelativeDuration(s string) (time.Duration, bool) {
	s = strings.TrimSpace(s)
	if len(s) < 2 {
		return 0, false
	}
	unit := s[len(s)-1]
	number := s[:len(s)-1]
	for i := 0; i < len(number); i++ {
		if number[i] < '0' || number[i] > '9' {
			return 0, false
		}
	}
	n, err := strconv.ParseInt(number, 10, 64)
	if err != nil || n <= 0 {
		return 0, false
	}
	var unitDuration time.Duration
	switch unit {
	case 's':
		unitDuration = time.Second
	case 'm':
		unitDuration = time.Minute
	case 'h':
		unitDuration = time.Hour
	case 'd':
		unitDuration = 24 * time.Hour
	case 'w':
		unitDuration = 7 * 24 * time.Hour
	default:
		return 0, false
	}
	const maxDuration = time.Duration(1<<63 - 1)
	if n > int64(maxDuration)/int64(unitDuration) {
		return 0, false
	}
	return time.Duration(n) * unitDuration, true
}

func nsString(t time.Time) string {
	return strconv.FormatInt(t.UnixNano(), 10)
}

func secString(t time.Time) string {
	return strconv.FormatInt(t.Unix(), 10)
}
