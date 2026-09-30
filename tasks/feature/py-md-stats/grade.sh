#!/usr/bin/env bash
# grade.sh <workdir> — restore the pristine existing tests, add the hidden
# --top-words tests, and run everything against the agent's mdstats.py.
set -uo pipefail

WORK="${1:?usage: grade.sh <workdir>}"
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 2; }
[[ -f "$WORK/mdstats.py" ]] || { echo 'SCORE_JSON {"passed": false, "score": 0.0, "details": "mdstats.py missing from workdir"}'; exit 1; }

# Anti-cheat: pristine visible tests + the hidden grading tests.
rm -rf "$WORK/tests"
cp -R "$TASK_DIR/fixture/tests" "$WORK/tests"
cp "$TASK_DIR/grade_tests/test_top_words.py" "$WORK/tests/test_top_words.py"

out="$(cd "$WORK" && python3 -m unittest discover -s tests -t . 2>&1)"
rc=$?
echo "$out"

if [[ $rc -eq 0 ]]; then
  echo 'SCORE_JSON {"passed": true, "score": 1.0, "details": "visible + hidden tests all pass"}'
  exit 0
fi
fails="$(echo "$out" | grep -Eo '(FAIL|ERROR): [^ ]+' | head -5 | tr '\n' ';' | sed 's/"/'"'"'/g')"
echo "SCORE_JSON {\"passed\": false, \"score\": 0.0, \"details\": \"unittest rc=$rc: $fails\"}"
exit 1
