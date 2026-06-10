// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package credential

import (
	"context"
	"crypto"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"

	"github.com/larksuite/cli/errs"
	"github.com/larksuite/cli/extension/keysigner"
	"github.com/larksuite/cli/internal/core"
)

// stubRoundTripper lets us assert request shape and return canned responses.
type stubRoundTripper struct {
	gotReq   *http.Request
	gotBody  string
	respCode int
	respBody string
	err      error
}

func (s *stubRoundTripper) RoundTrip(req *http.Request) (*http.Response, error) {
	s.gotReq = req
	if req.Body != nil {
		b, _ := io.ReadAll(req.Body)
		s.gotBody = string(b)
	}
	if s.err != nil {
		return nil, s.err
	}
	return &http.Response{
		StatusCode: s.respCode,
		Body:       io.NopCloser(strings.NewReader(s.respBody)),
		Header:     make(http.Header),
	}, nil
}

func TestFetchTAT_Success(t *testing.T) {
	rt := &stubRoundTripper{
		respCode: 200,
		respBody: `{"code":0,"tenant_access_token":"t-abc","msg":"ok"}`,
	}
	hc := &http.Client{Transport: rt}

	token, err := FetchTAT(context.Background(), hc, core.BrandFeishu, "cli_app", "secret_x")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if token != "t-abc" {
		t.Errorf("token = %q, want t-abc", token)
	}
	if rt.gotReq.URL.String() != "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" {
		t.Errorf("url = %s", rt.gotReq.URL.String())
	}
	if !strings.Contains(rt.gotBody, `"app_id":"cli_app"`) || !strings.Contains(rt.gotBody, `"app_secret":"secret_x"`) {
		t.Errorf("request body missing credentials: %s", rt.gotBody)
	}
}

// 10003 (bad / non-existent app_id, "invalid param") is classified locally by
// classifyTATResponseCode as CategoryConfig / SubtypeInvalidClient — the same
// typed error doResolveTAT (and thus every token-resolving command) returns.
func TestFetchTAT_Code10003_ConfigInvalidClient(t *testing.T) {
	rt := &stubRoundTripper{respCode: 200, respBody: `{"code":10003,"msg":"invalid param"}`}
	hc := &http.Client{Transport: rt}

	token, err := FetchTAT(context.Background(), hc, core.BrandFeishu, "cli_app", "secret_x")
	if err == nil {
		t.Fatal("expected error for code 10003")
	}
	if token != "" {
		t.Errorf("token = %q, want empty", token)
	}
	var cfgErr *errs.ConfigError
	if !errors.As(err, &cfgErr) {
		t.Fatalf("error not *errs.ConfigError: %T %v", err, err)
	}
	if cfgErr.Category != errs.CategoryConfig {
		t.Errorf("Category = %q, want %q", cfgErr.Category, errs.CategoryConfig)
	}
	if cfgErr.Subtype != errs.SubtypeInvalidClient {
		t.Errorf("Subtype = %q, want %q", cfgErr.Subtype, errs.SubtypeInvalidClient)
	}
	if cfgErr.Code != 10003 {
		t.Errorf("Code = %d, want 10003", cfgErr.Code)
	}
}

// 10014 ("app secret invalid") — the most common real-world rejection (real
// app_id + wrong secret) — is globally mapped in codemeta to
// CategoryConfig / SubtypeInvalidClient via BuildAPIError.
func TestFetchTAT_Code10014_ConfigInvalidClient(t *testing.T) {
	rt := &stubRoundTripper{respCode: 200, respBody: `{"code":10014,"msg":"app secret invalid"}`}
	hc := &http.Client{Transport: rt}

	_, err := FetchTAT(context.Background(), hc, core.BrandFeishu, "cli_app", "secret_x")
	var cfgErr *errs.ConfigError
	if !errors.As(err, &cfgErr) {
		t.Fatalf("error not *errs.ConfigError: %T %v", err, err)
	}
	if cfgErr.Subtype != errs.SubtypeInvalidClient || cfgErr.Code != 10014 {
		t.Errorf("got Subtype=%q Code=%d, want invalid_client/10014", cfgErr.Subtype, cfgErr.Code)
	}
}

// Any non-zero body code is a deterministic server-side rejection, so it
// always yields a typed error (errs.IsTyped). An unrecognized code falls back
// to CategoryAPI / SubtypeUnknown via BuildAPIError — still typed, so a probe
// caller still surfaces it rather than silently swallowing.
func TestFetchTAT_UnknownBodyCode_Typed(t *testing.T) {
	rt := &stubRoundTripper{respCode: 200, respBody: `{"code":99999,"msg":"future-unknown"}`}
	hc := &http.Client{Transport: rt}

	_, err := FetchTAT(context.Background(), hc, core.BrandFeishu, "cli_app", "secret_x")
	if err == nil {
		t.Fatal("expected error for code 99999")
	}
	if !errs.IsTyped(err) {
		t.Fatalf("expected a typed errs.* error, got %T %v", err, err)
	}
	var apiErr *errs.APIError
	if !errors.As(err, &apiErr) {
		t.Errorf("unknown code should fall back to *errs.APIError, got %T", err)
	}
}

// Non-2xx HTTP is ambiguous (not a payload-level credential rejection) — it
// must stay UNTYPED so a probe caller treats it as upstream noise and stays
// silent.
func TestFetchTAT_HTTPNon200_Untyped(t *testing.T) {
	for _, code := range []int{401, 403, 500, 503} {
		rt := &stubRoundTripper{respCode: code, respBody: `whatever`}
		hc := &http.Client{Transport: rt}
		_, err := FetchTAT(context.Background(), hc, core.BrandFeishu, "cli_app", "secret_x")
		if err == nil {
			t.Fatalf("HTTP %d: expected error", code)
		}
		if errs.IsTyped(err) {
			t.Errorf("HTTP %d: must be UNTYPED (ambiguous), got typed %T %v", code, err, err)
		}
	}
}

func TestFetchTAT_TransportError_Untyped(t *testing.T) {
	sentinel := errors.New("network down")
	rt := &stubRoundTripper{err: sentinel}
	hc := &http.Client{Transport: rt}

	_, err := FetchTAT(context.Background(), hc, core.BrandFeishu, "cli_app", "secret_x")
	if err == nil {
		t.Fatal("expected error")
	}
	if errs.IsTyped(err) {
		t.Errorf("transport error must be UNTYPED, got typed %T", err)
	}
	if !errors.Is(err, sentinel) {
		t.Errorf("error chain missing sentinel: %v", err)
	}
}

func TestFetchTAT_ParseError_Untyped(t *testing.T) {
	rt := &stubRoundTripper{respCode: 200, respBody: `not json`}
	hc := &http.Client{Transport: rt}

	_, err := FetchTAT(context.Background(), hc, core.BrandFeishu, "cli_app", "secret_x")
	if err == nil {
		t.Fatal("expected parse error")
	}
	if errs.IsTyped(err) {
		t.Errorf("parse error must be UNTYPED, got typed %T", err)
	}
}

func TestFetchTAT_BrandRouting(t *testing.T) {
	tests := []struct {
		brand   core.LarkBrand
		wantURL string
	}{
		{core.BrandFeishu, "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"},
		{core.BrandLark, "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"},
	}
	for _, tc := range tests {
		t.Run(string(tc.brand), func(t *testing.T) {
			rt := &stubRoundTripper{respCode: 200, respBody: `{"code":0,"tenant_access_token":"t"}`}
			hc := &http.Client{Transport: rt}
			if _, err := FetchTAT(context.Background(), hc, tc.brand, "a", "b"); err != nil {
				t.Fatal(err)
			}
			if got := rt.gotReq.URL.String(); got != tc.wantURL {
				t.Errorf("url = %s, want %s", got, tc.wantURL)
			}
		})
	}
}

func TestFetchTAT_ContextCanceled(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		<-r.Context().Done()
	}))
	defer srv.Close()

	rt := &urlRewriteRT{base: srv.URL}
	hc := &http.Client{Transport: rt}

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // pre-canceled

	_, err := FetchTAT(ctx, hc, core.BrandFeishu, "a", "b")
	if err == nil {
		t.Fatal("expected error for canceled context")
	}
	if errs.IsTyped(err) {
		t.Errorf("canceled context must be UNTYPED, got typed %T", err)
	}
	if !errors.Is(err, context.Canceled) {
		t.Errorf("error chain missing context.Canceled: %v", err)
	}
}

// urlRewriteRT forwards requests to a fixed base URL (test server).
type urlRewriteRT struct{ base string }

func (r *urlRewriteRT) RoundTrip(req *http.Request) (*http.Response, error) {
	newURL := r.base + req.URL.Path
	req2, err := http.NewRequestWithContext(req.Context(), req.Method, newURL, req.Body)
	if err != nil {
		return nil, err
	}
	req2.Header = req.Header
	return http.DefaultTransport.RoundTrip(req2)
}

// fakeTATSigner is a real in-memory ECDSA P-256 signer for assertion tests.
type fakeTATSigner struct{ key *ecdsa.PrivateKey }

func newFakeTATSigner(t *testing.T) *fakeTATSigner {
	t.Helper()
	k, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	return &fakeTATSigner{key: k}
}

func (f *fakeTATSigner) EnsureKey(context.Context, keysigner.KeyRef) (crypto.PublicKey, error) {
	return f.key.Public(), nil
}
func (f *fakeTATSigner) PublicKey(context.Context, keysigner.KeyRef) (crypto.PublicKey, error) {
	return f.key.Public(), nil
}
func (f *fakeTATSigner) Sign(_ context.Context, _ keysigner.KeyRef, in []byte) ([]byte, string, error) {
	h := sha256.Sum256(in)
	r, s, err := ecdsa.Sign(rand.Reader, f.key, h[:])
	if err != nil {
		return nil, "", err
	}
	sig := make([]byte, 64)
	r.FillBytes(sig[:32])
	s.FillBytes(sig[32:])
	return sig, keysigner.AlgES256, nil
}

func TestFetchTATWithAssertion_Success(t *testing.T) {
	rt := &stubRoundTripper{respCode: 200, respBody: `{"access_token":"t-jwt","token_type":"Bearer","expires_in":7200}`}
	hc := &http.Client{Transport: rt}

	token, err := FetchTATWithAssertion(context.Background(), hc, core.BrandFeishu, "cli_app", newFakeTATSigner(t), "agent-key")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if token != "t-jwt" {
		t.Errorf("token = %q, want t-jwt", token)
	}
	if rt.gotReq.URL.String() != "https://open.feishu.cn/open-apis/authen/v2/oauth/token" {
		t.Errorf("url = %s", rt.gotReq.URL.String())
	}

	form, err := url.ParseQuery(rt.gotBody)
	if err != nil {
		t.Fatal(err)
	}
	if form.Get("grant_type") != "urn:ietf:params:oauth:grant-type:jwt-bearer" {
		t.Errorf("grant_type = %q", form.Get("grant_type"))
	}
	if form.Get("client_assertion_type") != "urn:ietf:params:oauth:client-assertion-type:jwt-bearer" {
		t.Errorf("client_assertion_type = %q", form.Get("client_assertion_type"))
	}
	if form.Get("client_assertion") == "" {
		t.Error("client_assertion is empty")
	}
	if form.Has("client_secret") {
		t.Error("client_secret must NOT be sent for private_key_jwt")
	}

	// The assertion's aud must be the bare Open host per the App Authentication
	// JWT spec — not the full token endpoint URL.
	jwtParts := strings.Split(form.Get("client_assertion"), ".")
	if len(jwtParts) != 3 {
		t.Fatalf("malformed client_assertion: %q", form.Get("client_assertion"))
	}
	payload, err := base64.RawURLEncoding.DecodeString(jwtParts[1])
	if err != nil {
		t.Fatalf("assertion payload not base64url: %v", err)
	}
	var claims map[string]any
	if err := json.Unmarshal(payload, &claims); err != nil {
		t.Fatal(err)
	}
	if claims["aud"] != "open.feishu.cn" {
		t.Errorf("client_assertion aud = %v, want open.feishu.cn", claims["aud"])
	}
	if claims["iss"] != "cli_app" || claims["sub"] != "cli_app" {
		t.Errorf("client_assertion iss/sub = %v/%v, want cli_app", claims["iss"], claims["sub"])
	}
	if form.Get("client_id") != "cli_app" {
		t.Errorf("client_id = %q", form.Get("client_id"))
	}
}

func TestFetchTATWithAssertion_NilSigner(t *testing.T) {
	hc := &http.Client{Transport: &stubRoundTripper{respCode: 200, respBody: `{}`}}
	if _, err := FetchTATWithAssertion(context.Background(), hc, core.BrandFeishu, "cli_app", nil, "k"); err == nil {
		t.Fatal("expected error when signer is nil")
	}
}

func TestFetchTATWithAssertion_ServerError(t *testing.T) {
	rt := &stubRoundTripper{respCode: 200, respBody: `{"error":"invalid_client","error_description":"unknown key"}`}
	hc := &http.Client{Transport: rt}
	if _, err := FetchTATWithAssertion(context.Background(), hc, core.BrandFeishu, "cli_app", newFakeTATSigner(t), "k"); err == nil {
		t.Fatal("expected error for invalid_client response")
	}
}
