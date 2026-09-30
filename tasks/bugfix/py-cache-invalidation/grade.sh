#!/usr/bin/env bash
# grade.sh <workdir> — run the fixture's unittest suite against the agent's
# cachelib.py. Pristine tests are restored first: editing tests in the
# workdir has no effect on the score.
set -uo pipefail

WORK="${1:?usage: grade.sh <workdir>}"
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 2; }
[[ -f "$WORK/cachelib.py" ]] || { echo 'SCORE_JSON {"passed": false, "score": 0.0, "details": "cachelib.py missing from workdir"}'; exit 1; }

# Anti-cheat: restore the pristine test suite.
rm -rf "$WORK/tests"
cp -R "$TASK_DIR/fixture/tests" "$WORK/tests"

out="$(cd "$WORK" && python3 -m unittest discover -s tests -t . 2>&1)"
rc=$?
echo "$out"

if [[ $rc -eq 0 ]]; then
  echo 'SCORE_JSON {"passed": true, "score": 1.0, "details": "all unittest tests pass"}'
  exit 0
fi
fails="$(echo "$out" | grep -Eo '(FAIL|ERROR): [^ ]+' | head -5 | tr '\n' ';' | sed 's/"/'"'"'/g')"
echo "SCORE_JSON {\"passed\": false, \"score\": 0.0, \"details\": \"unittest rc=$rc: $fails\"}"
exit 1
