#!/usr/bin/env bash
# harnesses/lib/peko_isolate.sh — per-run environment isolation for peko.
#
# Adapted from peko-runtime/scripts/e2e/lib/isolate.sh (same seam, smaller
# surface). Source this from harnesses/peko.sh:
#
#   source "$(dirname "$0")/lib/peko_isolate.sh"
#   pb_iso_init            # fresh tempdir + exported env
#   ... peko commands ...  # subprocesses inherit the isolation
#   pb_iso_done            # kill daemon, remove tempdir (unless KEEP_TEMPDIR)
#
# Isolated: HOME, PEKO_HOME, PEKO_CONFIG_DIR/DATA_DIR/CACHE_DIR,
# PEKO_DAEMON_SOCK, vault/identity passphrases (deterministic).
#
# Why HOME and not just PEKO_HOME: the daemon's IPC layer hard-codes
# dirs::home_dir().join(".peko").join("run") for its socket + PID file, so
# only HOME redirects them in-process. And why the tempdir must be SHORT:
# the daemon's Unix socket bind fails once the path exceeds SUN_LEN
# (107 bytes on macOS) — /tmp/peko-bench/pb<pid><rand> stays well under.
set +u

_PB_ISO_DIR=""
_PB_ISO_HOME=""

pb_iso_init() {
  local root="${BENCH_TMP_ROOT:-/tmp/peko-bench}"
  local rand
  rand="$(LC_ALL=C tr -dc 'a-z0-9' </dev/urandom | head -c 4)"
  _PB_ISO_DIR="$root/pb$$${rand}"
  _PB_ISO_HOME="$_PB_ISO_DIR/home"
  rm -rf "$_PB_ISO_DIR"

  # Pre-create the skeleton the daemon expects on first touch.
  local sub
  for sub in home/.peko/run home/.peko/data home/.peko/cache \
             home/.peko/runtime/extensions home/.peko/runtime/mcps \
             home/.peko/runtime/registry home/.peko/runtime/locks; do
    mkdir -p "$_PB_ISO_DIR/$sub"
  done

  export HOME="$_PB_ISO_HOME"
  export USERPROFILE="$_PB_ISO_HOME"
  export PEKO_HOME="$_PB_ISO_HOME/.peko"
  export PEKO_CONFIG_DIR="$PEKO_HOME"
  export PEKO_DATA_DIR="$PEKO_HOME/data"
  export PEKO_CACHE_DIR="$PEKO_HOME/cache"
  export PEKO_DAEMON_SOCK="$PEKO_HOME/run/daemon.sock"
  export PEKO_DAEMON_PIPE=""
  export PEKO_MASTER_PASSPHRASE="peko-bench-vault-passphrase"
  export PEKO_IDENTITY_PASSPHRASE="peko-bench-vault-passphrase"
  # Headless key resolution: bypass the OS keychain, honour *_API_KEY env.
  export PEKO_TEST_RESOLVER_BOOTSTRAP=1

  echo "[peko.sh] isolated HOME=$HOME"
}

# Kill the run's daemon (via its pidfile) and remove the tempdir.
# Unlike the e2e lib we deliberately do NOT pkill peko processes globally —
# a benchmark box may have a developer daemon running on the default socket.
pb_iso_done() {
  local pid_file="$_PB_ISO_HOME/.peko/run/daemon.pid"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 0.3
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
  if [[ -z "${KEEP_TEMPDIR:-}" && -n "$_PB_ISO_DIR" ]]; then
    rm -rf "$_PB_ISO_DIR"
  elif [[ -n "$_PB_ISO_DIR" ]]; then
    echo "[peko.sh] KEEP_TEMPDIR set — leaving $_PB_ISO_DIR"
  fi
  _PB_ISO_DIR=""
  _PB_ISO_HOME=""
}
