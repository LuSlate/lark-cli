// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package main

import (
	"embed"
	"fmt"
	"io/fs"
	"os"

	"github.com/larksuite/cli/cmd"
)

// skillsEmbedFS embeds each skill's versioned content so the CLI serves content
// matching the binary version. It is intentionally a whitelist: agent-readable
// docs are embedded for every skill, while lark-slides machine resources embed
// only script/prompt/renderer files needed by SVGlide. Broad directories such
// as node_modules/, fixtures/, assets/, and generated project outputs stay out
// of the Go binary.
//
//go:embed skills/*/SKILL.md skills/*/references skills/*/routes skills/*/scenes skills/*/prompts
//go:embed skills/*/scripts/*.py
//go:embed skills/*/scripts/artboard_renderer/*.mjs skills/*/scripts/artboard_renderer/package.json skills/*/scripts/artboard_renderer/pnpm-lock.yaml
//go:embed skills/*/scripts/artboard_renderer/components skills/*/scripts/artboard_renderer/dist skills/*/scripts/artboard_renderer/templates skills/*/scripts/artboard_renderer/themes
var skillsEmbedFS embed.FS

// init wires the embedded tree in as the default skill content. It compiles into
// `go build .` but not the single-file preview build (`go build ./main.go`), so
// main.go stays self-contained and that build still compiles (shipping no
// embedded skills). Assembly failure warns on stderr rather than panicking.
func init() {
	sub, err := fs.Sub(skillsEmbedFS, "skills")
	if err != nil {
		fmt.Fprintln(os.Stderr, "warning: skills embed assembly failed, skills commands disabled:", err)
		return
	}
	cmd.SetEmbeddedSkillContent(sub)
}
