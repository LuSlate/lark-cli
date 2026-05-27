// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package common

import (
	"fmt"
	"io"
	"reflect"
	"strings"

	"github.com/spf13/cobra"
	"github.com/spf13/pflag"

	"github.com/larksuite/cli/internal/cmdutil"
)

// buildTypedHelp returns a cobra.HelpFunc that renders typed shortcuts in
// sections (CHOOSE ONE <FIELD> / OPTIONAL / EXAMPLES / GLOBAL FLAGS / Risk: /
// Tips:). Cobra's default HelpFunc is preserved for all non-typed commands;
// we only override per-command via cmd.SetHelpFunc.
//
// Section titles use the Args struct's field name (e.g. "TARGET", "CONTENT"),
// not the inner Go type name behind the field, so the help mirrors the
// user-visible variable name rather than an implementation detail.
func buildTypedHelp(specs []fieldSpec, examples []HelpExample) func(*cobra.Command, []string) {
	return func(cmd *cobra.Command, _ []string) {
		w := cmd.OutOrStdout()
		fmt.Fprintf(w, "%s — %s\n\n", cmd.Use, cmd.Short)
		rendered := map[string]struct{}{}
		renderOneOfSections(w, specs, rendered)
		renderOptionalSection(w, specs, rendered)
		renderExamples(w, examples)
		renderGlobalFlags(w, cmd, rendered)
		if r, ok := cmdutil.GetRisk(cmd); ok && r != "" {
			fmt.Fprintf(w, "Risk: %s\n\n", r)
		}
		for _, tip := range cmdutil.GetTips(cmd) {
			fmt.Fprintf(w, "Tips: %s\n", tip)
		}
	}
}

// renderOneOfSections walks each OneOf bucket and prints "CHOOSE ONE <FIELD>:"
// followed by every flag inside the bucket — including flags inside nested
// groups (a paired group's companion flag under its trigger) and nested
// raw-content variants (a raw-JSON variant's body + msg-type flags).
func renderOneOfSections(w io.Writer, specs []fieldSpec, rendered map[string]struct{}) {
	for _, s := range specs {
		if !s.IsOneOfBkt {
			continue
		}
		fmt.Fprintf(w, "CHOOSE ONE %s:\n", strings.ToUpper(s.GoFieldName))
		inner, _ := walkArgs(reflect.PointerTo(s.StructType))
		renderFlagsInBucket(w, inner, "  ", rendered)
		fmt.Fprintln(w)
	}
}

// renderFlagsInBucket renders bucket inner flags, recursing into nested group
// / OneOf sub-structs. The printed shape is FLATTENED so a oneof_trigger leaf
// inside a nested group renders at the parent's indent (it IS the variant
// selector, not a companion). Non-trigger leaves with a default value also
// render at parent indent (a default makes them "optional companions" rather
// than required follow-ons — e.g. an enum flag with a default). Only
// non-trigger leaves WITHOUT a default render at parent+2 indent, signaling
// "you must supply this together with the trigger" (e.g. a required companion
// flag under its trigger flag).
func renderFlagsInBucket(w io.Writer, specs []fieldSpec, indent string, rendered map[string]struct{}) {
	for _, child := range specs {
		if child.IsGroup || child.IsOneOfBkt {
			inner, _ := walkArgs(reflect.PointerTo(child.StructType))
			for _, leaf := range inner {
				if leaf.IsGroup || leaf.IsOneOfBkt {
					grand, _ := walkArgs(reflect.PointerTo(leaf.StructType))
					renderFlagsInBucket(w, grand, indent+"  ", rendered)
					continue
				}
				if leaf.FlagName == "" {
					continue
				}
				leafIndent := indent
				if !leaf.OneOfTrig && leaf.DefaultValue == "" {
					leafIndent = indent + "  "
				}
				fmt.Fprintf(w, "%s--%s    %s\n", leafIndent, leaf.FlagName, leaf.Description)
				rendered[leaf.FlagName] = struct{}{}
			}
			continue
		}
		if child.FlagName == "" {
			continue
		}
		fmt.Fprintf(w, "%s--%s    %s\n", indent, child.FlagName, child.Description)
		rendered[child.FlagName] = struct{}{}
	}
}

// renderOptionalSection prints top-level leaf flags that don't belong to any
// OneOf bucket. Sub-struct fields are skipped here because they live under
// CHOOSE ONE sections above.
func renderOptionalSection(w io.Writer, specs []fieldSpec, rendered map[string]struct{}) {
	anyFlag := false
	for _, s := range specs {
		if s.IsOneOfBkt || s.IsGroup {
			continue
		}
		if s.FlagName == "" {
			continue
		}
		if !anyFlag {
			fmt.Fprintln(w, "OPTIONAL:")
			anyFlag = true
		}
		fmt.Fprintf(w, "  --%s    %s\n", s.FlagName, s.Description)
		rendered[s.FlagName] = struct{}{}
	}
	if anyFlag {
		fmt.Fprintln(w)
	}
}

func renderExamples(w io.Writer, examples []HelpExample) {
	if len(examples) == 0 {
		return
	}
	fmt.Fprintln(w, "EXAMPLES:")
	for _, e := range examples {
		fmt.Fprintf(w, "  %-20s %s\n", e.Title+":", e.Cmd)
	}
	fmt.Fprintln(w)
}

// renderGlobalFlags prints framework-injected and cobra-inherited flags
// (--as / --dry-run / --jq / --format / -h / --help) that the typed Args
// struct does NOT define. The `rendered` set captures every flag name we
// already emitted under CHOOSE ONE / OPTIONAL — anything else surfaced by
// cmd.Flags() or cmd.InheritedFlags() falls under GLOBAL FLAGS.
func renderGlobalFlags(w io.Writer, cmd *cobra.Command, rendered map[string]struct{}) {
	type globalFlag struct {
		Name      string
		Shorthand string
		Usage     string
	}
	var globals []globalFlag
	seen := map[string]bool{}
	collect := func(fs *pflag.FlagSet) {
		fs.VisitAll(func(f *pflag.Flag) {
			if f.Hidden {
				return
			}
			if _, alreadyRendered := rendered[f.Name]; alreadyRendered {
				return
			}
			if seen[f.Name] {
				return
			}
			seen[f.Name] = true
			globals = append(globals, globalFlag{Name: f.Name, Shorthand: f.Shorthand, Usage: f.Usage})
		})
	}
	collect(cmd.Flags())
	collect(cmd.InheritedFlags())
	// Cobra auto-injects --help on every command, but it does not appear in
	// LocalFlags or InheritedFlags until the command has been resolved at
	// invocation time. Ensure it is always documented.
	if !seen["help"] {
		globals = append(globals, globalFlag{Name: "help", Shorthand: "h", Usage: "show help"})
	}
	if len(globals) == 0 {
		return
	}
	fmt.Fprintln(w, "GLOBAL FLAGS:")
	for _, g := range globals {
		if g.Shorthand != "" {
			fmt.Fprintf(w, "  -%s, --%s    %s\n", g.Shorthand, g.Name, g.Usage)
		} else {
			fmt.Fprintf(w, "  --%s    %s\n", g.Name, g.Usage)
		}
	}
	fmt.Fprintln(w)
}
