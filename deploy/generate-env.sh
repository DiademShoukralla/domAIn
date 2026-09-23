#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXAMPLE_FILE="$REPO_ROOT/.env.production.example"
OUTPUT_FILE="$REPO_ROOT/.env.production"
TARGET_VAR=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [--var VARIABLE_NAME]

Generate or update .env.production from .env.production.example.

With no arguments, walks through every variable interactively.
With --var, updates only the named variable; requires an existing .env.production.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --var)
      TARGET_VAR="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$EXAMPLE_FILE" ]]; then
  echo "ERROR: Template not found: $EXAMPLE_FILE" >&2
  exit 1
fi

if [[ -n "$TARGET_VAR" && ! -f "$OUTPUT_FILE" ]]; then
  echo "ERROR: $OUTPUT_FILE does not exist. Run $(basename "$0") without --var first." >&2
  exit 1
fi

declare -A ENV_VALUES
declare -A EXAMPLE_DEFAULTS
declare -A VAR_COMMENTS
VAR_ORDER=()

mask_value() {
  local value="$1"
  local length=${#value}

  if [[ $length -eq 0 ]]; then
    echo "(not set)"
    return
  fi
  if [[ $length -le 4 ]]; then
    echo "****"
    return
  fi
  printf '%s***%s' "${value:0:2}" "${value: -2}"
}

is_secret_var() {
  local name="$1"
  case "$name" in
    *_KEY | *_SECRET | *PASSWORD* | *_PRIVATE_KEY* | TOKEN_ENCRYPTION_KEY | BOOTSTRAP_API_KEY | GITHUB_APP_PRIVATE_KEY_BASE64)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

generate_fernet_key() {
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

generate_bootstrap_key() {
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

load_env_file() {
  local file="$1"
  local line key value

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      ENV_VALUES["$key"]="$value"
    fi
  done < "$file"
}

parse_example_template() {
  local line var_name example_default
  local -a pending_comments=()

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      var_name="${BASH_REMATCH[1]}"
      example_default="${BASH_REMATCH[2]}"
      EXAMPLE_DEFAULTS["$var_name"]="$example_default"
      VAR_ORDER+=("$var_name")
      if ((${#pending_comments[@]} > 0)); then
        VAR_COMMENTS["$var_name"]="$(printf '%s\n' "${pending_comments[@]}")"
      else
        VAR_COMMENTS["$var_name"]=""
      fi
      pending_comments=()
      continue
    fi
    pending_comments+=("$line")
  done <"$EXAMPLE_FILE"
}

var_in_example() {
  [[ -n "${EXAMPLE_DEFAULTS[$1]+x}" ]]
}

read_line() {
  local __resultvar="$1"
  local __prompt="$2"
  local __value=""

  IFS= read -r -p "$__prompt" __value || __value=""
  printf -v "$__resultvar" '%s' "$__value"
}

read_secret_line() {
  local __resultvar="$1"
  local __prompt="$2"
  local __value=""

  IFS= read -r -s -p "$__prompt" __value || __value=""
  echo
  printf -v "$__resultvar" '%s' "$__value"
}

prompt_generate_or_enter() {
  local var_name="$1"
  local generator="$2"
  local choice=""

  read_line choice "Generate new value? [Y/n]: "
  choice="${choice:-Y}"
  if [[ "$choice" =~ ^[Yy]$ ]]; then
    ENV_VALUES["$var_name"]="$("$generator")"
    return
  fi

  read_secret_line choice "Enter value: "
  ENV_VALUES["$var_name"]="$choice"
}

prompt_for_var() {
  local var_name="$1"
  local comments="${VAR_COMMENTS[$var_name]:-}"
  local current="${ENV_VALUES[$var_name]:-}"
  local choice=""

  echo
  echo "=== ${var_name} ==="
  if [[ -n "$comments" ]]; then
    printf '%s\n' "$comments"
  fi

  if [[ "$var_name" == "TOKEN_ENCRYPTION_KEY" ]]; then
    if [[ -n "$current" ]]; then
      echo "Current value: $(mask_value "$current")"
      read_line choice "Keep current value? [Y/n/generate]: "
      case "$choice" in
        n | N)
          prompt_generate_or_enter "$var_name" generate_fernet_key
          ;;
        generate | g | G)
          ENV_VALUES["$var_name"]="$(generate_fernet_key)"
          ;;
      esac
    else
      prompt_generate_or_enter "$var_name" generate_fernet_key
    fi
    return
  fi

  if [[ "$var_name" == "VOYAGE_BASE_URL" ]]; then
    if [[ -n "$current" ]]; then
      echo "Current value: $(mask_value "$current")"
      read_line choice "Keep current value? [Y/n]: "
      if [[ "$choice" =~ ^[Nn]$ ]]; then
        read_line choice "Enter value (optional, press Enter to skip): "
        ENV_VALUES["$var_name"]="$choice"
      fi
    else
      read_line choice "Enter value (optional, press Enter to skip): "
      ENV_VALUES["$var_name"]="$choice"
    fi
    return
  fi

  if [[ "$var_name" == "BOOTSTRAP_API_KEY" ]]; then
    if [[ -n "$current" ]]; then
      echo "Current value: $(mask_value "$current")"
      read_line choice "Keep current value? [Y/n/generate]: "
      case "$choice" in
        n | N)
          prompt_generate_or_enter "$var_name" generate_bootstrap_key
          ;;
        generate | g | G)
          ENV_VALUES["$var_name"]="$(generate_bootstrap_key)"
          ;;
      esac
    else
      prompt_generate_or_enter "$var_name" generate_bootstrap_key
    fi
    return
  fi

  if [[ -n "$current" ]]; then
    echo "Current value: $(mask_value "$current")"
    read_line choice "Keep current value? [Y/n]: "
    if [[ "$choice" =~ ^[Nn]$ ]]; then
      if is_secret_var "$var_name"; then
        read_secret_line choice "Enter new value: "
      else
        read_line choice "Enter new value: "
      fi
      ENV_VALUES["$var_name"]="$choice"
    fi
    return
  fi

  if is_secret_var "$var_name"; then
    read_secret_line choice "Enter value: "
    ENV_VALUES["$var_name"]="$choice"
  else
    read_line choice "Enter value: "
    ENV_VALUES["$var_name"]="$choice"
  fi
}

should_prompt() {
  local var_name="$1"
  if [[ -z "$TARGET_VAR" ]]; then
    return 0
  fi
  [[ "$var_name" == "$TARGET_VAR" ]]
}

parse_example_template

if [[ -f "$OUTPUT_FILE" ]]; then
  load_env_file "$OUTPUT_FILE"
fi

if [[ -n "$TARGET_VAR" ]]; then
  if ! var_in_example "$TARGET_VAR"; then
    echo "ERROR: Variable not defined in $EXAMPLE_FILE: $TARGET_VAR" >&2
    exit 1
  fi
  prompt_for_var "$TARGET_VAR"
else
  for var_name in "${VAR_ORDER[@]}"; do
    prompt_for_var "$var_name"
  done
fi

tmp_file="$(mktemp "${OUTPUT_FILE}.tmp.XXXXXX")"
cleanup() {
  rm -f "$tmp_file"
}
trap cleanup EXIT

pending_comments=()
while IFS= read -r line || [[ -n "$line" ]]; do
  if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
    var_name="${BASH_REMATCH[1]}"
    example_default="${BASH_REMATCH[2]}"

    if [[ -z "${ENV_VALUES[$var_name]:-}" && -n "$example_default" ]]; then
      ENV_VALUES["$var_name"]="$example_default"
    fi

    if ((${#pending_comments[@]} > 0)); then
      for comment_line in "${pending_comments[@]}"; do
        printf '%s\n' "$comment_line" >>"$tmp_file"
      done
      pending_comments=()
    fi

    printf '%s=%s\n' "$var_name" "${ENV_VALUES[$var_name]:-}" >>"$tmp_file"
    continue
  fi

  pending_comments+=("$line")
done <"$EXAMPLE_FILE"

if ((${#pending_comments[@]} > 0)); then
  for comment_line in "${pending_comments[@]}"; do
    printf '%s\n' "$comment_line" >>"$tmp_file"
  done
fi

chmod 600 "$tmp_file"
mv "$tmp_file" "$OUTPUT_FILE"
trap - EXIT

echo
echo "Wrote $OUTPUT_FILE"
