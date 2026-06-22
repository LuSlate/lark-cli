// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"strings"
	"testing"

	"github.com/larksuite/cli/internal/httpmock"
)

const fileQuotaURL = "/open-apis/spark/v1/apps/app_x/storage/file_quota"

func TestAppsFileQuotaGet_QuotaConnectedShowsAllFields(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "GET", URL: fileQuotaURL,
		Body: map[string]interface{}{"code": 0, "data": map[string]interface{}{
			"storage_used_bytes":  157286400,
			"storage_quota_bytes":  1073741824,
			"usage_percent":        14.6,
			"files":                42,
		}},
	})
	if err := runAppsShortcut(t, AppsFileQuotaGet,
		[]string{"+file-quota-get", "--app-id", "app_x", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	got := stdout.String()
	for _, want := range []string{`"storage_quota_bytes"`, `"usage_percent"`, `"files"`} {
		if !strings.Contains(got, want) {
			t.Errorf("quota json missing %q:\n%s", want, got)
		}
	}
}

// 配额未对接（=0）：storage_quota_bytes / usage_percent 不输出。
func TestAppsFileQuotaGet_UnconnectedOmitsQuotaFields(t *testing.T) {
	factory, stdout, reg := newAppsExecuteFactory(t)
	reg.Register(&httpmock.Stub{
		Method: "GET", URL: fileQuotaURL,
		Body: map[string]interface{}{"code": 0, "data": map[string]interface{}{
			"storage_used_bytes": 157286400,
			"storage_quota_bytes": 0,
			"usage_percent":       0,
			"files":               42,
		}},
	})
	if err := runAppsShortcut(t, AppsFileQuotaGet,
		[]string{"+file-quota-get", "--app-id", "app_x", "--as", "user"}, factory, stdout); err != nil {
		t.Fatalf("execute err=%v", err)
	}
	got := stdout.String()
	for _, banned := range []string{"storage_quota_bytes", "usage_percent"} {
		if strings.Contains(got, banned) {
			t.Errorf("unconnected quota should omit %q:\n%s", banned, got)
		}
	}
	if !strings.Contains(got, `"storage_used_bytes"`) || !strings.Contains(got, `"files"`) {
		t.Errorf("should still show used/files:\n%s", got)
	}
}

func TestProjectFileQuota_DeletesZeroQuota(t *testing.T) {
	data := map[string]interface{}{"storage_used_bytes": 100, "storage_quota_bytes": float64(0), "usage_percent": float64(0), "files": 3}
	projectFileQuota(data)
	if _, ok := data["storage_quota_bytes"]; ok {
		t.Errorf("zero quota should be deleted: %v", data)
	}
	if _, ok := data["usage_percent"]; ok {
		t.Errorf("usage_percent should be deleted when quota=0: %v", data)
	}

	data2 := map[string]interface{}{"storage_used_bytes": 100, "storage_quota_bytes": float64(1024), "usage_percent": float64(9.8), "files": 3}
	projectFileQuota(data2)
	if _, ok := data2["storage_quota_bytes"]; !ok {
		t.Errorf("non-zero quota should be kept: %v", data2)
	}
}
