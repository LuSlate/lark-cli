// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package doc

import (
	"strings"

	"github.com/larksuite/cli/shortcuts/common"
)

func outDocsAIResult(runtime *common.RuntimeContext, data map[string]interface{}) error {
	if docsAIResultFailed(data) {
		return runtime.OutRawPartialFailure(data, nil)
	}
	runtime.OutRaw(data, nil)
	return nil
}

func docsAIResultFailed(data map[string]interface{}) bool {
	if data == nil {
		return false
	}
	result, _ := data["result"].(string)
	return strings.EqualFold(strings.TrimSpace(result), "failed")
}
