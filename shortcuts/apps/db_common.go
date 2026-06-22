// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package apps

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/larksuite/cli/internal/output"
	"github.com/larksuite/cli/internal/validate"
)

// pollUntil 轮询异步任务直到 check 判定终态。async migrate/recovery 用：dataloom 立即返
// task_id/preview_request_id，CLI 自己 poll（避免单连接长挂被网关/SDK 30s 中断）。
// 首次立即 fetch（不睡）；check 返 done→返回；返 err→透传（失败终态）；否则按 interval 间隔重试至 maxWait。
func pollUntil(ctx context.Context, interval, maxWait time.Duration,
	fetch func() (map[string]interface{}, error),
	check func(map[string]interface{}) (done bool, err error)) (map[string]interface{}, error) {
	maxAttempts := int(maxWait / interval)
	if maxAttempts < 1 {
		maxAttempts = 1
	}
	for i := 0; ; i++ {
		data, err := fetch()
		if err != nil {
			return nil, err
		}
		done, cerr := check(data)
		if cerr != nil {
			return nil, cerr
		}
		if done {
			return data, nil
		}
		if i+1 >= maxAttempts {
			return nil, output.ErrNetwork("timed out waiting for completion after %s", maxWait)
		}
		select {
		case <-ctx.Done():
			return nil, output.ErrNetwork("cancelled while waiting: %v", ctx.Err())
		case <-time.After(interval):
		}
	}
}

// URL helpers for the db CLI commands.

// appTablesPath 返回 app db 表列表 URL（复用存量「获取数据表列表」接口）。
func appTablesPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/tables", apiBasePath, validate.EncodePathSegment(appID))
}

// appTablePath 返回单个 app db 表详情 URL（复用存量「获取数据表详细信息」接口）。
func appTablePath(appID, table string) string {
	return appTablesPath(appID) + "/" + validate.EncodePathSegment(table)
}

// appSQLPath 返回 app db SQL 执行 URL（复用存量「执行 SQL」接口）。
func appSQLPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/sql_commands", apiBasePath, validate.EncodePathSegment(appID))
}

// appDbEnvCreatePath 返回 app db 环境创建 URL（服务端接口名仍为 db_dev_init）。
func appDbEnvCreatePath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db_dev_init", apiBasePath, validate.EncodePathSegment(appID))
}

// ── 多环境发布（env diff/migrate）/ 数据恢复（recovery）/ 配额 路由 ──

func appEnvMigratePath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/env_migrate", apiBasePath, validate.EncodePathSegment(appID))
}
func appEnvMigrateStatusPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/env_migrate_status", apiBasePath, validate.EncodePathSegment(appID))
}
func appRecoveryPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/env_recovery", apiBasePath, validate.EncodePathSegment(appID))
}
func appRecoveryDiffStatusPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/env_recovery_diff_status", apiBasePath, validate.EncodePathSegment(appID))
}
func appRecoveryApplyStatusPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/env_recovery_apply_status", apiBasePath, validate.EncodePathSegment(appID))
}
func appDbQuotaPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/quota", apiBasePath, validate.EncodePathSegment(appID))
}

// ── 变更追溯（changelog / audit）路由 ──

func appChangelogListPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/changelog_list", apiBasePath, validate.EncodePathSegment(appID))
}
func appAuditStatusPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/audit_status", apiBasePath, validate.EncodePathSegment(appID))
}
func appAuditSetPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/audit_set", apiBasePath, validate.EncodePathSegment(appID))
}
func appAuditListPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/audit_list", apiBasePath, validate.EncodePathSegment(appID))
}

// operatorRef 是 operator 的 {id,name}。后端用 JSON 字符串内嵌透传，CLI parse：
// json 输出还原成对象（下游能区分同名用户），pretty 只取 name。
type operatorRef struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

// parseOperator 解析 operator 字符串：空→nil；非 JSON→{raw,raw}；JSON→{id,name}（name 空兜底 id）。
func parseOperator(raw string) *operatorRef {
	s := strings.TrimSpace(raw)
	if s == "" {
		return nil
	}
	if !strings.HasPrefix(s, "{") {
		return &operatorRef{ID: s, Name: s}
	}
	var o operatorRef
	if json.Unmarshal([]byte(s), &o) != nil {
		return &operatorRef{ID: s, Name: s}
	}
	if o.Name == "" {
		o.Name = o.ID
	}
	return &o
}

// operatorName 取 operator 的展示名（pretty），空用 "—"。
func operatorName(op *operatorRef) string {
	if op == nil || op.Name == "" {
		return "—"
	}
	return op.Name
}

// safeParseJSON 把 before/after 的 JSON 字符串还原成结构化对象供下游消费；失败时透传原始串。
func safeParseJSON(s string) interface{} {
	var v interface{}
	if json.Unmarshal([]byte(s), &v) == nil {
		return v
	}
	return s
}

// appDataImportPath 返回 db 数据导入 URL（新增 db/ 域段路由）。
func appDataImportPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/data_import", apiBasePath, validate.EncodePathSegment(appID))
}

// appDataExportPath 返回 db 数据导出 URL（返原始字节）。
func appDataExportPath(appID string) string {
	return fmt.Sprintf("%s/apps/%s/db/data_export", apiBasePath, validate.EncodePathSegment(appID))
}

// appTableRecordsPath 返回数据表记录列表 URL（复用 GetAppTableRecordList，其 total 即符合条件的记录总数）。
func appTableRecordsPath(appID, table string) string {
	return appTablePath(appID, table) + "/records"
}

// resolveDataFormat 由文件扩展名推断数据格式。lark-cli 的 --format 已被框架占用（输出渲染），
// 故数据格式从文件名推断：import 接受 csv/json，export 还接受 sql。
func resolveDataFormat(ext string, allowSQL bool) (string, error) {
	raw := strings.TrimPrefix(strings.ToLower(strings.TrimSpace(ext)), ".")
	switch raw {
	case "csv", "json":
		return raw, nil
	case "sql":
		if allowSQL {
			return "sql", nil
		}
	}
	if allowSQL {
		return "", output.ErrValidation("unsupported data format %q (file must end in .csv, .json or .sql)", raw)
	}
	return "", output.ErrValidation("unsupported data format %q (file must end in .csv or .json)", raw)
}

// countDataRows 粗估数据行数（用于导入上限校验、导出兜底计数）。
// csv：非空行数 - 1（表头）；json：顶层数组长度，非数组算 1，解析失败算 0。
func countDataRows(body []byte, format string) int {
	if format == "csv" {
		lines := 0
		for _, ln := range strings.Split(string(body), "\n") {
			if strings.TrimRight(ln, "\r") != "" {
				lines++
			}
		}
		if lines > 0 {
			return lines - 1
		}
		return 0
	}
	var arr []json.RawMessage
	if err := json.Unmarshal(body, &arr); err == nil {
		return len(arr)
	}
	var obj map[string]json.RawMessage
	if err := json.Unmarshal(body, &obj); err == nil {
		return 1
	}
	return 0
}

// requireAppID trims --app-id and rejects blank, returning a uniform validation error.
func requireAppID(raw string) (string, error) {
	id := strings.TrimSpace(raw)
	if id == "" {
		return "", output.ErrValidation("--app-id is required")
	}
	return id, nil
}
