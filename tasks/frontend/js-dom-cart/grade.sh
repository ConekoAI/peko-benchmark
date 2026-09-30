#!/usr/bin/env bash
# grade.sh <workdir> — run hidden node:test tests against the agent's cart.js.
set -uo pipefail

WORK="${1:?usage: grade.sh <workdir>}"
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v node >/dev/null 2>&1; then
  echo "node not found — cannot grade frontend task"
  echo 'SCORE_JSON {"passed": false, "score": 0.0, "details": "grader unavailable: node not installed"}'
  exit 2
fi
[[ -f "$WORK/cart.js" ]] || { echo 'SCORE_JSON {"passed": false, "score": 0.0, "details": "cart.js missing from workdir"}'; exit 1; }

cp "$TASK_DIR/grade_tests/cart.test.mjs" "$WORK/cart.test.mjs"

out="$(cd "$WORK" && node --test cart.test.mjs 2>&1)"
rc=$?
echo "$out"
rm -f "$WORK/cart.test.mjs"

if [[ $rc -eq 0 ]]; then
  echo 'SCORE_JSON {"passed": true, "score": 1.0, "details": "all hidden node tests pass"}'
  exit 0
fi
fails="$(echo "$out" | grep -Eo '(✖ .+|not ok [0-9]+ .+)' | head -5 | tr '\n' ';' | sed 's/"/'"'"'/g')"
echo "SCORE_JSON {\"passed\": false, \"score\": 0.0, \"details\": \"node --test rc=$rc: $fails\"}"
exit 1
