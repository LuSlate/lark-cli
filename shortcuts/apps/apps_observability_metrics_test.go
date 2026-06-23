// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/larksuite/cli/internal/httpmock"
)

func TestMetricNamesMapping(t *testing.T) {
	got, labels, err := metricNamesForCLI("requests", "")
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(got, ",") != "client_api_request_count,client_api_request_error_count" {
		t.Fatalf("names = %#v", got)
	}
	if strings.Join(labels, ",") != "total,error" {
		t.Fatalf("labels = %#v", labels)
	}
	if _, _, err := metricNamesForCLI("cpu", "p99"); err == nil {
		t.Fatalf("cpu with p99 should fail")
	}
}

func TestAppsMetricQuery_DryRunUsesSeconds(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsMetricQuery, []string{
		"+metric-query", "--app-id", "app_x", "--metric", "requests",
		"--series", "total", "--since", "2026-06-23T10:00:00Z",
		"--until", "2026-06-23T10:01:00Z", "--down-sample", "1m",
		"--dry-run", "--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("dry-run err=%v", err)
	}
	var env struct {
		API []struct {
			Method string                 `json:"method"`
			URL    string                 `json:"url"`
			Body   map[string]interface{} `json:"body"`
		} `json:"api"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode dry-run: %v\n%s", err, stdout.String())
	}
	if env.API[0].Method != "POST" || env.API[0].URL != "/open-apis/spark/v1/apps/app_x/query_metrics_data" {
		t.Fatalf("method/url = %s %s", env.API[0].Method, env.API[0].URL)
	}
	body := env.API[0].Body
	if _, ok := body["start_timestamp"]; !ok {
		t.Fatalf("metric dry-run missing start_timestamp: %#v", body)
	}
	if _, ok := body["start_timestamp_ns"]; ok {
		t.Fatalf("metric should not use start_timestamp_ns: %#v", body)
	}
	if body["start_timestamp"] != "1782208800" || body["end_timestamp"] != "1782208860" {
		t.Fatalf("metric timestamps = %v %v", body["start_timestamp"], body["end_timestamp"])
	}
	if body["down_sample"] != "1m" {
		t.Fatalf("down_sample = %v", body["down_sample"])
	}
}

func TestAppsMetricQuery_RejectsDevEnv(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsMetricQuery, []string{
		"+metric-query", "--app-id", "app_x", "--metric", "requests", "--env", "dev", "--as", "user",
	}, factory, stdout)
	requireAppsValidationParam(t, err, "--env")
}

func TestAppsMetricQuery_FillsMissingRequestValuesWithZero(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/query_metrics_data",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"items": []interface{}{
					map[string]interface{}{
						"timestamp":  "1782208800",
						"dimensions": map[string]interface{}{"page": "/home"},
						"values":     map[string]interface{}{"total": float64(12)},
					},
					map[string]interface{}{
						"timestamp":  "1782208860",
						"dimensions": map[string]interface{}{"page": "/settings"},
						"values":     map[string]interface{}{"total": float64(8), "error": nil},
					},
				},
			},
		},
	})

	if err := runAppsShortcut(t, AppsMetricQuery, []string{
		"+metric-query", "--app-id", "app_x", "--metric", "requests", "--as", "user",
	}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}

	var env struct {
		Data struct {
			Items []struct {
				Values map[string]interface{} `json:"values"`
			} `json:"items"`
			HasMore bool `json:"has_more"`
		} `json:"data"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode output: %v\n%s", err, stdout.String())
	}
	if env.Data.HasMore {
		t.Fatalf("has_more = true, want false")
	}
	if len(env.Data.Items) != 2 {
		t.Fatalf("items len = %d", len(env.Data.Items))
	}
	for i, item := range env.Data.Items {
		if item.Values["error"] != float64(0) {
			t.Fatalf("item %d error = %#v, want 0; values=%#v", i, item.Values["error"], item.Values)
		}
	}
}

func TestAppsMetricQuery_EmptyResponseOutputsEmptyItemsArray(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/query_metrics_data",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{},
		},
	})

	if err := runAppsShortcut(t, AppsMetricQuery, []string{
		"+metric-query", "--app-id", "app_x", "--metric", "latency", "--as", "user",
	}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}

	var env struct {
		Data struct {
			Items   []map[string]interface{} `json:"items"`
			HasMore bool                     `json:"has_more"`
		} `json:"data"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode output: %v\n%s", err, stdout.String())
	}
	if env.Data.Items == nil {
		t.Fatalf("items decoded as nil; stdout=%s", stdout.String())
	}
	if len(env.Data.Items) != 0 || env.Data.HasMore {
		t.Fatalf("empty output = items %#v has_more %v", env.Data.Items, env.Data.HasMore)
	}
}

func TestAppsAnalyticsQuery_DryRunUsesNanoseconds(t *testing.T) {
	factory, stdout, _ := newAppsExecuteFactory(t)
	err := runAppsShortcut(t, AppsAnalyticsQuery, []string{
		"+analytics-query", "--app-id", "app_x", "--analytics", "users",
		"--granularity", "week", "--dry-run", "--as", "user",
	}, factory, stdout)
	if err != nil {
		t.Fatalf("dry-run err=%v", err)
	}
	var env struct {
		API []struct {
			Method string                 `json:"method"`
			URL    string                 `json:"url"`
			Body   map[string]interface{} `json:"body"`
		} `json:"api"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode dry-run: %v\n%s", err, stdout.String())
	}
	if env.API[0].Method != "POST" || env.API[0].URL != "/open-apis/spark/v1/apps/app_x/query_analytics_data" {
		t.Fatalf("method/url = %s %s", env.API[0].Method, env.API[0].URL)
	}
	body := env.API[0].Body
	if _, ok := body["start_timestamp_ns"]; !ok {
		t.Fatalf("analytics dry-run missing start_timestamp_ns: %#v", body)
	}
	if _, ok := body["start_timestamp"]; ok {
		t.Fatalf("analytics should not use start_timestamp: %#v", body)
	}
	if body["time_aggregation_unit"] != "WEEK" {
		t.Fatalf("time_aggregation_unit = %v", body["time_aggregation_unit"])
	}
}

func TestAppsAnalyticsQuery_PageViewDesktopSeriesSetsDeviceFilter(t *testing.T) {
	for _, tc := range []struct {
		name string
		args []string
	}{
		{
			name: "series",
			args: []string{
				"+analytics-query", "--app-id", "app_x", "--analytics", "page-view",
				"--series", "desktop", "--dry-run", "--as", "user",
			},
		},
		{
			name: "device-type",
			args: []string{
				"+analytics-query", "--app-id", "app_x", "--analytics", "page-view",
				"--device-type", "desktop", "--dry-run", "--as", "user",
			},
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			factory, stdout, _ := newAppsExecuteFactory(t)
			if err := runAppsShortcut(t, AppsAnalyticsQuery, tc.args, factory, stdout); err != nil {
				t.Fatalf("dry-run err=%v", err)
			}
			var env struct {
				API []struct {
					Body map[string]interface{} `json:"body"`
				} `json:"api"`
			}
			if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
				t.Fatalf("decode dry-run: %v\n%s", err, stdout.String())
			}
			filter := env.API[0].Body["filter"].(map[string]interface{})
			deviceTypes := filter["device_types"].([]interface{})
			if len(deviceTypes) != 1 || deviceTypes[0] != "desktop" {
				t.Fatalf("device_types = %#v", deviceTypes)
			}
		})
	}
}

func TestAppsAnalyticsQuery_DesktopSeriesUsesDesktopValueLabel(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/query_analytics_data",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{
				"data_points": []interface{}{
					map[string]interface{}{
						"timestamp_ns": "1782208800000000000",
						"value":        float64(21),
					},
				},
			},
		},
	})

	if err := runAppsShortcut(t, AppsAnalyticsQuery, []string{
		"+analytics-query", "--app-id", "app_x", "--analytics", "page-view",
		"--series", "desktop", "--as", "user",
	}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}

	var env struct {
		Data struct {
			Items []struct {
				Values map[string]interface{} `json:"values"`
			} `json:"items"`
		} `json:"data"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode output: %v\n%s", err, stdout.String())
	}
	if len(env.Data.Items) != 1 {
		t.Fatalf("items len = %d", len(env.Data.Items))
	}
	if env.Data.Items[0].Values["desktop"] != float64(21) {
		t.Fatalf("values = %#v, want desktop=21", env.Data.Items[0].Values)
	}
	if _, ok := env.Data.Items[0].Values["page-view"]; ok {
		t.Fatalf("values should not use page-view label: %#v", env.Data.Items[0].Values)
	}
}

func TestAppsAnalyticsQuery_EmptyResponseOutputsEmptyItemsArray(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "POST",
		URL:    "/open-apis/spark/v1/apps/app_x/query_analytics_data",
		Body: map[string]interface{}{
			"code": 0,
			"data": map[string]interface{}{},
		},
	})

	if err := runAppsShortcut(t, AppsAnalyticsQuery, []string{
		"+analytics-query", "--app-id", "app_x", "--analytics", "users", "--as", "user",
	}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}

	var env struct {
		Data struct {
			Items   []map[string]interface{} `json:"items"`
			HasMore bool                     `json:"has_more"`
		} `json:"data"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode output: %v\n%s", err, stdout.String())
	}
	if env.Data.Items == nil {
		t.Fatalf("items decoded as nil; stdout=%s", stdout.String())
	}
	if len(env.Data.Items) != 0 || env.Data.HasMore {
		t.Fatalf("empty output = items %#v has_more %v", env.Data.Items, env.Data.HasMore)
	}
}

func TestAnalyticsTypesMapping(t *testing.T) {
	types, labels, filter, err := analyticsTypesForCLI("users", "", "")
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(types, ",") != "ACTIVE_USER,NEW_USER,TOTAL_USER" {
		t.Fatalf("types = %#v", types)
	}
	if strings.Join(labels, ",") != "active-users,new-users,total-users" {
		t.Fatalf("labels = %#v", labels)
	}
	if len(filter) != 0 {
		t.Fatalf("filter = %#v, want empty", filter)
	}

	types, labels, filter, err = analyticsTypesForCLI("page-view", "", "")
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(types, ",") != "PAGE_VIEW" || strings.Join(labels, ",") != "all" {
		t.Fatalf("page-view all mapping = %#v %#v", types, labels)
	}
	if len(filter) != 0 {
		t.Fatalf("filter = %#v, want empty", filter)
	}

	types, labels, filter, err = analyticsTypesForCLI("page-view", "desktop", "")
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(types, ",") != "PAGE_VIEW" || strings.Join(labels, ",") != "desktop" {
		t.Fatalf("page-view mapping = %#v %#v", types, labels)
	}
	deviceTypes := filter["device_types"].([]string)
	if len(deviceTypes) != 1 || deviceTypes[0] != "desktop" {
		t.Fatalf("device_types = %#v", deviceTypes)
	}

	types, labels, filter, err = analyticsTypesForCLI("page-view", "mobile-view", "")
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(types, ",") != "PAGE_VIEW" || strings.Join(labels, ",") != "mobile" {
		t.Fatalf("page-view mobile mapping = %#v %#v", types, labels)
	}
	deviceTypes = filter["device_types"].([]string)
	if len(deviceTypes) != 1 || deviceTypes[0] != "mobile" {
		t.Fatalf("device_types = %#v", deviceTypes)
	}

	if _, _, _, err := analyticsTypesForCLI("users", "desktop", ""); err == nil {
		t.Fatalf("users desktop series should fail")
	}
	if _, _, _, err := analyticsTypesForCLI("page-view", "tablet", ""); err == nil {
		t.Fatalf("page-view tablet series should fail")
	}
	if _, _, _, err := analyticsTypesForCLI("page-view", "", "tablet"); err == nil {
		t.Fatalf("tablet device type should fail")
	}
}
