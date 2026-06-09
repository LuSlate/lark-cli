//go:build !larkmeta

// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package metastatic

import "github.com/larksuite/cli/internal/registry/metaschema"

// Registry is an empty placeholder for builds without `-tags larkmeta`, so a
// fresh checkout compiles without running the generator. The real data lives in
// meta_data_gen.go (generated from meta_data.json, gitignored, `-tags larkmeta`).
// This mirrors the existing meta_data.json / meta_data_default.json
// fetch-at-build model: the heavy spec is never committed, only generated.
var Registry = metaschema.Registry{}
