#!/usr/bin/env bash
# harnesses/codex.sh — run one benchmark task with the codex CLI.
#
# Contract (see README.md "Harness contract"):
#   codex.sh <workdir> <prompt_file> <out_dir> <timeout_secs>
#
# Required env: OPENAI_API_KEY.
# Optional env: CODEX_BIN (default: codex from PATH), CODEX_MODEL (pin this
#               for harness comparisons!), CODEX_ARGS.
#
# NOTE: codex CLI flags vary by version. The default CODEX_ARGS targets a
# non-interactive full-auto run inside the workdir; if your installed codex
# rejects them, override CODEX_ARGS rather than editing this file.
set -uo pipefail

WORK_DIR="${1:?usage: codex.sh <workdir> <prompt_file> <out_dir> <timeout_secs>}"
PROMPT_FILE="${2:?}"
OUT_DIR="${3:?}"
TIMEOUT_SECS="${4:?}"

CODEX_BIN="${CODEX_BIN:-codex}"
CODEX_ARGS="${CODEX_ARGS:-exec --full-auto --skip-git-repo-check}"

command -v "$CODEX_BIN" >/dev/null 2>&1 || {
  echo "[codex.sh] codex binary not found: $CODEX_BIN" >&2; exit 2; }
[[ -n "${OPENAI_API_KEY:-}" ]] || {
  echo "[codex.sh] OPENAI_API_KEY required" >&2; exit 2; }

args=($CODEX_ARGS)
if [[ -n "${CODEX_MODEL:-}" ]]; then
  args+=(--model "$CODEX_MODEL")
fi

prompt="$(cat "$PROMPT_FILE")"

echo "[codex.sh] running: $CODEX_BIN ${args[*]} <prompt> (cwd=$WORK_DIR, timeout ${TIMEOUT_SECS}s)"
(cd "$WORK_DIR" && "$CODEX_BIN" "${args[@]}" "$prompt") \
  >"$OUT_DIR/transcript.txt" 2>&1 &
run_pid=$!

elapsed=0
rc=0
while kill -0 "$run_pid" 2>/dev/null; do
  if (( elapsed >= TIMEOUT_SECS )); then
    echo "[codex.sh] TIMEOUT after ${TIMEOUT_SECS}s — killing" >&2
    kill "$run_pid" 2>/dev/null || true
    sleep 1
    kill -9 "$run_pid" 2>/dev/null || true
    rc=124
    break
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done
if [[ $rc -eq 0 ]]; then
  wait "$run_pid" || rc=$?
fi

if [[ $rc -ne 0 ]]; then
  echo "[codex.sh] codex exited rc=$rc" >&2
  exit "$rc"
fi
echo "[codex.sh] run complete"
exit 0
