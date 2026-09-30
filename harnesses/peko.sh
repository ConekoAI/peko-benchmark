#!/usr/bin/env bash
# harnesses/peko.sh — run one benchmark task with the peko runtime.
#
# Contract (see README.md "Harness contract"):
#   peko.sh <workdir> <prompt_file> <out_dir> <timeout_secs>
#   - writes transcript to <out_dir>/transcript.txt
#   - exit 0 = harness ran to completion; non-zero = harness failure
#
# Required env: PEKO_BIN, PEKO_API_KEY (unless PEKO_SKIP_MODEL_ADD=1).
# Optional env: PEKO_MODEL_TEMPLATE (minimax), PEKO_MODEL_NAME (MiniMax-M3),
#               PEKO_MODEL_ID (minimax-MiniMax-M3), BENCH_TMP_ROOT,
#               KEEP_TEMPDIR, BENCH_PRINCIPAL (bench).
set -uo pipefail

WORK_DIR="${1:?usage: peko.sh <workdir> <prompt_file> <out_dir> <timeout_secs>}"
PROMPT_FILE="${2:?}"
OUT_DIR="${3:?}"
TIMEOUT_SECS="${4:?}"

PEKO_BIN="${PEKO_BIN:?set PEKO_BIN to the peko binary path}"
[[ -x "$PEKO_BIN" ]] || { echo "[peko.sh] PEKO_BIN not executable: $PEKO_BIN" >&2; exit 2; }

MODEL_TEMPLATE="${PEKO_MODEL_TEMPLATE:-minimax}"
MODEL_NAME="${PEKO_MODEL_NAME:-MiniMax-M3}"
MODEL_ID="${PEKO_MODEL_ID:-minimax-MiniMax-M3}"
PRINCIPAL="${BENCH_PRINCIPAL:-bench}"

source "$(dirname "$0")/lib/peko_isolate.sh"
pb_iso_init
trap 'pb_iso_done' EXIT

echo "[peko.sh] peko version: $("$PEKO_BIN" version 2>&1 | head -1)"

# ---- model catalog + principal -------------------------------------------
if [[ -z "${PEKO_SKIP_MODEL_ADD:-}" ]]; then
  [[ -n "${PEKO_API_KEY:-}" ]] || {
    echo "[peko.sh] PEKO_API_KEY required (or PEKO_SKIP_MODEL_ADD=1)" >&2; exit 2; }
  "$PEKO_BIN" model add --template "$MODEL_TEMPLATE" --model "$MODEL_NAME" \
    --key "$PEKO_API_KEY" || {
    echo "[peko.sh] model add failed" >&2; exit 2; }
fi

# --detach: provision + return immediately; create ensures the daemon is
# running and knows the peko. The genesis turn fires in the background.
"$PEKO_BIN" create "$PRINCIPAL" --model "$MODEL_ID" --detach || {
  echo "[peko.sh] peko create failed" >&2; exit 2; }

# ---- run the task ---------------------------------------------------------
# `peko send` streams the reply and returns when the run completes.
echo "[peko.sh] sending task prompt (timeout ${TIMEOUT_SECS}s)…"
"$PEKO_BIN" send "$PRINCIPAL" --file "$PROMPT_FILE" \
  >"$OUT_DIR/transcript.txt" 2>"$OUT_DIR/send.err" &
send_pid=$!

elapsed=0
rc=0
while kill -0 "$send_pid" 2>/dev/null; do
  if (( elapsed >= TIMEOUT_SECS )); then
    echo "[peko.sh] TIMEOUT after ${TIMEOUT_SECS}s — stopping run" >&2
    "$PEKO_BIN" stop "$PRINCIPAL" >/dev/null 2>&1 || true
    kill "$send_pid" 2>/dev/null || true
    sleep 1
    kill -9 "$send_pid" 2>/dev/null || true
    rc=124
    break
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done
if [[ $rc -eq 0 ]]; then
  wait "$send_pid" || rc=$?
fi

# Best-effort: structured channel log alongside the human transcript.
"$PEKO_BIN" log "$PRINCIPAL" --json >"$OUT_DIR/channel_log.json" 2>/dev/null || true

if [[ $rc -ne 0 ]]; then
  echo "[peko.sh] send exited rc=$rc (see send.err)" >&2
  exit "$rc"
fi
echo "[peko.sh] run complete"
exit 0
