// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package registry

import "strings"

var methodDescriptionOverrides = map[string]string{
	"drive.files.patch": "修改文件标题",
}

// GetMethodDescription returns the method description from metadata, falling back
// to a curated override when the upstream meta has an empty description.
func GetMethodDescription(service, resource, method string, meta map[string]interface{}) string {
	if desc := strings.TrimSpace(GetStrFromMap(meta, "description")); desc != "" {
		return desc
	}
	return methodDescriptionOverrides[service+"."+resource+"."+method]
}
