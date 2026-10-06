#!/bin/sh
# Dedicated installation; never installs a background service or edits user config.
set -eu
version=2026.9.8
install_dir="${1:-$HOME/.local/share/peko-benchmark/openclaw/$version}"
npm_major="$(npm --version | cut -d. -f1)"
if [ "$npm_major" -ge 12 ]; then
  npm install --prefix "$install_dir" "openclaw@$version" --allow-scripts=openclaw --no-audit --no-fund
else
  npm install --prefix "$install_dir" "openclaw@$version" --no-audit --no-fund
fi
node "$install_dir/node_modules/openclaw/openclaw.mjs" --version
printf 'OPENCLAW_ENTRY=%s/node_modules/openclaw/openclaw.mjs\n' "$install_dir"
