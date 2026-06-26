// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package config

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/spf13/cobra"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/internal/cmdutil"
	"github.com/larksuite/cli/internal/core"
	"github.com/larksuite/cli/internal/credential"
)

// SetAppSecretOptions holds all inputs for config set-app-secret.
type SetAppSecretOptions struct {
	Factory        *cmdutil.Factory
	AppSecretStdin bool
	Yes            bool
}

// NewCmdConfigSetAppSecret creates the config set-app-secret subcommand.
func NewCmdConfigSetAppSecret(f *cmdutil.Factory) *cobra.Command {
	opts := &SetAppSecretOptions{Factory: f}

	cmd := &cobra.Command{
		Use:   "set-app-secret",
		Short: "Rotate a profile's stored app secret (verified before saving)",
		Long: `Rotate a profile's app secret after you reset it on the Lark/Feishu open platform.
The new secret is verified against Lark before anything is saved; only the target
profile changes — other profiles and the active selection stay untouched.

Targets the active profile; use the global --profile <name|app_id> to pick another.`,
		RunE: func(cmd *cobra.Command, args []string) error {
			return setAppSecretRun(f, opts)
		},
	}

	cmd.Flags().BoolVar(&opts.AppSecretStdin, "app-secret-stdin", false, "Read the new secret from stdin (required with --yes).")
	cmd.Flags().BoolVar(&opts.Yes, "yes", false, "Apply; without it, only preview the target and exit 10.")
	// Do NOT call MarkFlagRequired("app-secret-stdin") — preview path (no --yes)
	// must work without it; the "required" is enforced inside setAppSecretRun on
	// the apply path only.
	cmdutil.SetRisk(cmd, "high-risk-write")

	return cmd
}

// setAppSecretRun runs the set-app-secret command: resolve target profile,
// confirm gate (no --yes → preview target + exit 10), read the new secret from
// stdin, verify it via FetchTAT before writing, then store it via core.ForStorage
// and emit the result envelope.
func setAppSecretRun(f *cmdutil.Factory, opts *SetAppSecretOptions) error {
	// ── Step 1: Resolve target profile ────────────────────────────────────────
	multi, err := core.LoadOrNotConfigured()
	if err != nil {
		return err
	}

	profileOverride := f.Invocation.Profile
	app := multi.CurrentAppConfig(profileOverride)
	if app == nil {
		if profileOverride != "" {
			return errs.NewConfigError(errs.SubtypeNotConfigured,
				"profile %q not found", profileOverride).
				WithHint("available profiles: %s",
					joinProfileNames(multi.ProfileNames()))
		}
		return core.NoActiveProfileError()
	}

	// ── Step 2: Build target ──────────────────────────────────────────────────
	// IsActive: true when the resolved profile equals the default active one
	// (i.e. multi.CurrentAppConfig("") would return the same profile).
	activeApp := multi.CurrentAppConfig("")
	isActive := activeApp != nil && activeApp.ProfileName() == app.ProfileName()

	target := &errs.ErrTarget{
		Profile:  app.ProfileName(),
		AppID:    app.AppId,
		IsActive: isActive,
	}

	// ── Step 3: Confirm gate — MUST happen before any stdin read ─────────────
	if !opts.Yes {
		// Follow the framework confirmation convention (internal/cmdutil/confirm.go):
		// `action` is the operation identifier, and the hint tells the caller what to
		// append to THEIR OWN invocation — never a pre-built "lark-cli …" string.
		// A pre-built command hardcodes the binary name and trips shell-quoting /
		// wrong-binary pitfalls (e.g. an older installed `lark-cli` without this
		// subcommand). We add --profile <app_id> to the guidance so the apply pins
		// the previewed target and cannot drift to a different active profile.
		msg := fmt.Sprintf(
			"app secret for profile %q (%s) will be rotated; confirm the target, then re-run with --profile %s --yes",
			app.ProfileName(), app.AppId, app.AppId,
		)
		hint := fmt.Sprintf("add --profile %s --yes to confirm (pins the target shown above; pipe the new secret via stdin)", app.AppId)
		return errs.NewConfirmationRequiredError(
			errs.RiskHighRiskWrite,
			"config set-app-secret",
			"%s", msg,
		).WithHint("%s", hint).WithTarget(target)
	}

	// ── --yes path ────────────────────────────────────────────────────────────

	// Step 4a: require --app-secret-stdin on the apply path.
	if !opts.AppSecretStdin {
		return errs.NewValidationError(errs.SubtypeInvalidArgument, "app secret must be provided via stdin").
			WithHint("use --app-secret-stdin and pipe the secret").
			WithParam("--app-secret-stdin")
	}

	// Step 4b: read and validate the new secret from stdin.
	scanner := bufio.NewScanner(f.IOStreams.In)
	if !scanner.Scan() {
		if scanErr := scanner.Err(); scanErr != nil {
			return errs.NewValidationError(errs.SubtypeFailedPrecondition, "failed to read secret from stdin: %v", scanErr).
				WithCause(scanErr).
				WithParam("--app-secret-stdin")
		}
		return errs.NewValidationError(errs.SubtypeInvalidArgument, "stdin is empty, expected app secret").
			WithHint("pipe the app secret to stdin").
			WithParam("--app-secret-stdin")
	}
	newSecret := strings.TrimSpace(scanner.Text())
	if newSecret == "" {
		return errs.NewValidationError(errs.SubtypeInvalidArgument, "app secret read from stdin is empty").
			WithHint("pipe a non-empty app secret to stdin").
			WithParam("--app-secret-stdin")
	}

	// ── Step 5: Verify newSecret via TAT before writing ──────────────────────
	// Pattern: same as cmd/config/init_probe.go:runProbe — FetchTAT + errs.IsTyped
	// discriminator. Typed error = deterministic credential rejection (exit 3).
	// Untyped error = transient/transport (exit 4). Neither path writes anything.
	verifyCtx, verifyCancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer verifyCancel()
	httpClient, err := f.HttpClient()
	if err != nil {
		return errs.NewNetworkError(errs.SubtypeNetworkTransport, "could not initialise HTTP client for secret verification, nothing was changed, please retry").
			WithHint("the target is already confirmed — re-run with --profile %s --yes (no need to preview again)", app.AppId).
			WithCause(err).
			WithTarget(target)
	}
	if _, err := credential.FetchTAT(verifyCtx, httpClient, app.Brand, app.AppId, newSecret); err != nil {
		if errs.IsTyped(err) {
			// Deterministic credential rejection (invalid_client / unauthorized_client).
			return errs.NewConfigError(errs.SubtypeInvalidClient, "new app secret is invalid, nothing was changed").
				WithHint("the target is already confirmed — provide a valid secret and re-run with --profile %s --yes (no need to preview again)", app.AppId).
				WithCause(err).
				WithTarget(target)
		}
		// Transient / transport / timeout — surface as NetworkError so the caller
		// knows to retry rather than treat it as a bad credential.
		return errs.NewNetworkError(errs.SubtypeNetworkTransport, "could not verify the new secret (transient error), nothing was changed, please retry").
			WithHint("the target is already confirmed — re-run with --profile %s --yes (no need to preview again)", app.AppId).
			WithCause(err).
			WithTarget(target)
	}

	// ── Step 6: write newSecret via ForStorage; update config only when needed ─
	// ForStorage is the single canonical entry point for storing a secret —
	// identical to config init / config bind. No other keychain/file write logic.
	stored, err := core.ForStorage(app.AppId, core.PlainSecret(newSecret), f.Keychain)
	if err != nil {
		return errs.NewInternalError(errs.SubtypeStorage, "%v", err).WithCause(err)
	}

	// Determine whether we need to update config.json.
	// If the existing secret is already a keychain ref, ForStorage has already
	// overwritten the keychain entry in-place — the ref is unchanged, so we
	// must NOT rewrite config.json (byte-level stability).
	// For plain/file sources, we migrate to the new keychain ref.
	idx := multi.FindAppIndex(app.AppId)
	orig := multi.Apps[idx].AppSecret
	migrated := false
	if orig.IsSecretRef() && orig.Ref.Source == "keychain" {
		// keychain source: value updated in-place by ForStorage; ref unchanged → no config write.
	} else {
		// plain/file source: update only this profile's AppSecret field; all other
		// profiles and all other fields of this profile are left completely untouched.
		multi.Apps[idx].AppSecret = stored
		if err := core.SaveMultiAppConfig(multi); err != nil {
			return errs.NewInternalError(errs.SubtypeStorage, "failed to save config: %v", err).WithCause(err)
		}
		migrated = true
	}

	// ── Step 7: emit success output ──────────────────────────────────────────
	// Non-terminal (piped / agent / script): JSON envelope on stdout.
	// Terminal (human at shell): pretty human-readable line on stdout.
	if !f.IOStreams.IsTerminal {
		envelope := map[string]interface{}{
			"ok":       true,
			"identity": "bot",
			"data": map[string]interface{}{
				"profile":   target.Profile,
				"app_id":    target.AppID,
				"is_active": target.IsActive,
				"verified":  true,
				"migrated":  migrated,
			},
		}
		resultJSON, _ := json.Marshal(envelope)
		fmt.Fprintln(f.IOStreams.Out, string(resultJSON))
	} else {
		// Pretty line: ✓ app secret updated for profile "cursor" (cli_xxxxx) [active] — verified
		activeSegment := ""
		if target.IsActive {
			activeSegment = " [active]"
		}
		fmt.Fprintf(f.IOStreams.Out,
			"✓ app secret updated for profile %q (%s)%s — verified\n",
			target.Profile, target.AppID, activeSegment,
		)
	}
	return nil
}

// joinProfileNames joins profile names for a hint message.
func joinProfileNames(names []string) string {
	if len(names) == 0 {
		return "(none)"
	}
	result := ""
	for i, n := range names {
		if i > 0 {
			result += ", "
		}
		result += n
	}
	return result
}
