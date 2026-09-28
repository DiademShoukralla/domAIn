#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GENERATE="$REPO_ROOT/deploy/generate-env.sh"
DEPLOY="$REPO_ROOT/deploy/deploy.sh"
EXAMPLE="$REPO_ROOT/.env.production.example"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_eq() {
  if [[ "$1" != "$2" ]]; then
    fail "Expected '$2', got '$1'"
  fi
}

assert_contains() {
  if [[ "$1" != *"$2"* ]]; then
    fail "Output missing expected substring: $2"
  fi
}

# Build a complete env file: every template key set; VOYAGE_BASE_URL intentionally blank.
build_complete_env() {
  local dest="$1"
  : >"$dest"
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      local key="${BASH_REMATCH[1]}"
      if [[ "$key" == "VOYAGE_BASE_URL" ]]; then
        printf '%s=\n' "$key" >>"$dest"
      else
        printf '%s=test-value\n' "$key" >>"$dest"
      fi
    fi
  done <"$EXAMPLE"
}

ENV_COMPLETE="$TMPDIR/complete.env"
ENV_INCOMPLETE="$TMPDIR/incomplete.env"

build_complete_env "$ENV_COMPLETE"

grep -v '^SESSION_SECRET=' "$ENV_COMPLETE" | grep -v '^GITHUB_APP_OAUTH_CLIENT_ID=' >"$ENV_INCOMPLETE"

echo "==> --check: incomplete env exits 1 and names missing keys"
set +e
CHECK_OUT="$(bash "$GENERATE" --check --env-file "$ENV_INCOMPLETE" 2>&1)"
CHECK_STATUS=$?
set -e
if [[ $CHECK_STATUS -ne 1 ]]; then
  fail "--check should exit 1 for incomplete env"
fi
assert_contains "$CHECK_OUT" "SESSION_SECRET"
assert_contains "$CHECK_OUT" "GITHUB_APP_OAUTH_CLIENT_ID"

echo "==> --check: complete env exits 0"
set +e
CHECK_OK="$(bash "$GENERATE" --check --env-file "$ENV_COMPLETE" 2>&1)"
CHECK_OK_STATUS=$?
set -e
if [[ $CHECK_OK_STATUS -ne 0 ]]; then
  fail "--check should exit 0 for complete env"
fi
assert_contains "$CHECK_OK" "all template variables"

echo "==> deploy.sh aborts before sourcing when keys are missing"
set +e
DEPLOY_OUT="$(cd "$REPO_ROOT" && IMAGE_TAG=test bash "$DEPLOY" --env-file "$ENV_INCOMPLETE" 2>&1)"
DEPLOY_STATUS=$?
set -e
if [[ $DEPLOY_STATUS -eq 0 ]]; then
  fail "deploy should fail when env is incomplete"
fi
assert_contains "$DEPLOY_OUT" "generate-env.sh --missing"
if [[ "$DEPLOY_OUT" == *"Pulling images"* ]]; then
  fail "deploy should not reach image pull when --check fails"
fi

echo "==> --missing: prompts only for absent keys; preserves existing values"
MISSING_INPUT="$(mktemp)"
cat >"$MISSING_INPUT" <<'EOF'
new-oauth-client-id
n
new-session-secret-value
EOF
BEFORE_LINE="$(grep '^APP_ENV=' "$ENV_INCOMPLETE")"
set +e
MISSING_OUT="$(bash "$GENERATE" --missing --env-file "$ENV_INCOMPLETE" <"$MISSING_INPUT" 2>&1)"
MISSING_STATUS=$?
set -e
rm -f "$MISSING_INPUT"
if [[ $MISSING_STATUS -ne 0 ]]; then
  fail "--missing should succeed"
fi
assert_contains "$MISSING_OUT" "Added:"
AFTER_LINE="$(grep '^APP_ENV=' "$ENV_INCOMPLETE")"
assert_eq "$BEFORE_LINE" "$AFTER_LINE"
if ! grep -q '^VOYAGE_BASE_URL=$' "$ENV_INCOMPLETE"; then
  fail "VOYAGE_BASE_URL should remain blank-but-present"
fi
if ! grep -q '^SESSION_SECRET=new-session-secret-value$' "$ENV_INCOMPLETE"; then
  fail "SESSION_SECRET should be set from prompt"
fi

echo "==> --missing: unknown keys preserved with warning"
build_complete_env "$TMPDIR/rewrite.env"
echo 'LEGACY_CUSTOM_VAR=keep-me' >>"$TMPDIR/rewrite.env"
grep -v '^SESSION_TTL_DAYS=' "$TMPDIR/rewrite.env" >"$TMPDIR/rewrite-missing.env"
printf '30\n' | bash "$GENERATE" --missing --env-file "$TMPDIR/rewrite-missing.env" >/dev/null
if ! grep -q '^LEGACY_CUSTOM_VAR=keep-me' "$TMPDIR/rewrite-missing.env"; then
  fail "unknown key should survive rewrite"
fi
if ! grep -q 'Not in .env.production.example (kept):' "$TMPDIR/rewrite-missing.env"; then
  fail "expected preservation comment in env file"
fi

echo "==> --missing: up to date leaves file untouched"
UPTODATE="$TMPDIR/uptodate.env"
build_complete_env "$UPTODATE"
BEFORE_HASH="$(sha256sum "$UPTODATE" | awk '{print $1}')"
BEFORE_MTIME="$(stat -c %Y "$UPTODATE")"
UPTODATE_MSG="$(bash "$GENERATE" --missing --env-file "$UPTODATE" 2>&1)"
AFTER_HASH="$(sha256sum "$UPTODATE" | awk '{print $1}')"
AFTER_MTIME="$(stat -c %Y "$UPTODATE")"
assert_contains "$UPTODATE_MSG" "up to date"
assert_eq "$BEFORE_HASH" "$AFTER_HASH"
assert_eq "$BEFORE_MTIME" "$AFTER_MTIME"

echo "All generate-env tests passed."
