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

// skillsEmbedFS embeds each skill's agent-readable content (SKILL.md +
// references/, plus lark-whiteboard's routes/ and scenes/) so the CLI serves
// content matching the binary version. Machine-resource dirs remain excluded by
// default; lark-slides SVG runtime scripts are explicitly embedded because
// create-svg can execute them in packaged CLI installs.
//
//go:embed skills/*/SKILL.md skills/*/references skills/*/routes skills/*/scenes
//go:embed skills/lark-slides/scripts/svg_rasterize_effects.py
//go:embed skills/lark-slides/scripts/svg_effect_classifier.py
//go:embed skills/lark-slides/scripts/svg_safe_rewrite.py
//go:embed skills/lark-slides/scripts/svg_raster_renderer.py
//go:embed skills/lark-slides/scripts/svglide_project_runner.py
//go:embed skills/lark-slides/scripts/svg_preflight.py
//go:embed skills/lark-slides/scripts/svg_preview_lint.py
//go:embed skills/lark-slides/scripts/svglide_asset_selector.py
//go:embed skills/lark-slides/scripts/svglide_strategist.py
//go:embed skills/lark-slides/scripts/svglide_gen_runtime.py
//go:embed skills/lark-slides/scripts/svglide_golden_suite.py
var skillsEmbedFS embed.FS

// init wires the embedded tree in as the default skill content. Packaged builds
// must compile the package (`go build .`) so this file is included; otherwise
// skill commands have no embedded runtime content. Assembly failure warns on
// stderr rather than panicking.
func init() {
	sub, err := fs.Sub(skillsEmbedFS, "skills")
	if err != nil {
		fmt.Fprintln(os.Stderr, "warning: skills embed assembly failed, skills commands disabled:", err)
		return
	}
	cmd.SetEmbeddedSkillContent(sub)
}
