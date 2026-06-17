// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package credential

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/extension/keysigner"
	"github.com/larksuite/cli/internal/auth"
	"github.com/larksuite/cli/internal/auth/jwt"
	"github.com/larksuite/cli/internal/core"
)

// FetchTAT performs a single HTTP POST to mint a tenant access token with the
// given credentials. It does not read configuration or keychain, so callers
// that already hold plaintext credentials (e.g. the post-`config init` probe)
// can validate them without a second keychain round-trip.
//
// A non-zero TAT response code means the server inspected the payload and
// rejected the credentials; FetchTAT returns the canonical typed error from
// classifyTATResponseCode — the SAME classification doResolveTAT (and thus
// every token-resolving command) produces, so callers see one consistent
// envelope (CategoryConfig / SubtypeInvalidClient for 10003 / 10014, etc.).
// Transport, HTTP-status and JSON-parse failures are returned raw (untyped),
// leaving them ambiguous; a caller can use errs.IsTyped to tell a deterministic
// credential rejection apart from upstream/transport noise.
//
// The caller owns the context timeout.
func FetchTAT(ctx context.Context, httpClient *http.Client, brand core.LarkBrand, appID, appSecret string) (string, error) {
	ep := core.ResolveEndpoints(brand)
	url := ep.Open + "/open-apis/auth/v3/tenant_access_token/internal"

	body, err := json.Marshal(map[string]string{
		"app_id":     appID,
		"app_secret": appSecret,
	})
	if err != nil {
		return "", fmt.Errorf("failed to marshal TAT request: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("TAT API returned HTTP %d", resp.StatusCode)
	}

	var result struct {
		Code              int    `json:"code"`
		Msg               string `json:"msg"`
		TenantAccessToken string `json:"tenant_access_token"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("failed to parse TAT response: %w", err)
	}
	if result.Code != 0 {
		return "", classifyTATResponseCode(result.Code, result.Msg, string(brand), appID)
	}
	return result.TenantAccessToken, nil
}

// FetchTATWithAssertion mints a tenant access token for a private_key_jwt app via
// the RFC 7523 jwt-bearer grant: it signs a short-lived client_assertion with the
// TEE-held key and posts it to the unified OAuth token endpoint, replacing the
// app_secret entirely.
//
// The unified v2 token endpoint returns the minted token as access_token
// (tenant_access_token is accepted as a fallback).
func FetchTATWithAssertion(ctx context.Context, httpClient *http.Client, brand core.LarkBrand, clientID string, signer keysigner.Signer, keyLabel string) (string, error) {
	if signer == nil {
		return "", fmt.Errorf("private_key_jwt requires a key signer, but none is available on this build")
	}
	ep := core.ResolveEndpoints(brand)
	endpoint := ep.Open + auth.PathOAuthTokenV2

	assertion, err := jwt.SignClientAssertion(ctx, signer, keysigner.KeyRef{Label: keyLabel}, clientID, core.OpenAPIAudience(brand), time.Now())
	if err != nil {
		return "", err
	}

	form := url.Values{}
	form.Set("grant_type", "urn:ietf:params:oauth:grant-type:jwt-bearer")
	form.Set("client_id", clientID)
	form.Set("client_assertion_type", jwt.ClientAssertionType)
	form.Set("client_assertion", assertion)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, strings.NewReader(form.Encode()))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read token response: %w", err)
	}

	var result struct {
		Code              int    `json:"code"`
		Msg               string `json:"msg"`
		Error             string `json:"error"`
		ErrorDescription  string `json:"error_description"`
		AccessToken       string `json:"access_token"`
		TenantAccessToken string `json:"tenant_access_token"`
	}
	_ = json.Unmarshal(body, &result) // best-effort; error body may not be JSON

	token := result.AccessToken
	if token == "" {
		token = result.TenantAccessToken
	}
	if resp.StatusCode == http.StatusOK && token != "" && result.Error == "" && result.Code == 0 {
		return token, nil
	}

	// Surface the server's reason, preferring the OAuth `error` code (e.g.
	// unauthorized_client) which is more diagnostic than the description alone.
	detail := result.ErrorDescription
	if detail == "" {
		detail = result.Msg
	}
	if detail == "" {
		detail = strings.TrimSpace(string(body))
	}
	if result.Error != "" {
		return "", classifyAssertionError(result.Error, resp.StatusCode, detail)
	}
	return "", fmt.Errorf("token endpoint HTTP %d (code=%d): %s", resp.StatusCode, result.Code, detail)
}

// classifyAssertionError maps the OAuth token endpoint's `error` field to a
// typed or untyped error. Only deterministic client-credential rejections get a
// typed errs.ConfigError (so runProbePKJWT can tell "this key is not bound to
// this app" apart from upstream noise); every other error (e.g.
// temporarily_unavailable) stays untyped and is swallowed by the probe. detail
// carries only the server's error_description / msg / body text — it never
// echoes the client_assertion or private key (the assertion lives only in the
// request form).
func classifyAssertionError(oauthError string, httpStatus int, detail string) error {
	switch oauthError {
	case "invalid_client", "unauthorized_client", "invalid_grant":
		return errs.NewConfigError(errs.SubtypeInvalidClient,
			"token endpoint rejected the key (%s): %s", oauthError, detail)
	default:
		return fmt.Errorf("token endpoint HTTP %d (%s): %s", httpStatus, oauthError, detail)
	}
}
