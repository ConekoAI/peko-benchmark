#!/usr/bin/env bash
# grade.sh <workdir> — mutation grading for an agent-written test suite.
#
#   validity:  agent's tests must PASS against the pristine pricing.py
#   mutation:  agent's tests must FAIL against each hidden mutant
#
# score = 0.5 * validity + 0.5 * (mutants caught / mutants total)
# passed = score == 1.0
set -uo pipefail

WORK="${1:?usage: grade.sh <workdir>}"
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRATCH="$(mktemp -d -t peko-bench-grade.XXXXXX)"
trap 'rm -rf "$SCRATCH"' EXIT

command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 2; }

if [[ ! -f "$WORK/test_pricing.py" ]]; then
  echo 'SCORE_JSON {"passed": false, "score": 0.0, "details": "test_pricing.py not found in workdir"}'
  exit 1
fi

run_suite() { # $1 = dir containing pricing.py + test_pricing.py; returns unittest rc
  (cd "$1" && python3 -m unittest test_pricing 2>&1)
}

# --- 1. validity against the pristine module -------------------------------
mkdir "$SCRATCH/valid"
cp "$TASK_DIR/fixture/pricing.py" "$SCRATCH/valid/pricing.py"
cp "$WORK/test_pricing.py" "$SCRATCH/valid/test_pricing.py"
valid_out="$(run_suite "$SCRATCH/valid")"
valid_rc=$?
echo "=== validity (tests vs pristine pricing.py): rc=$valid_rc ==="
echo "$valid_out" | tail -5

validity=0
[[ $valid_rc -eq 0 ]] && validity=1

# --- 2. mutation catching ----------------------------------------------------
total=0
caught=0
for mutant in "$TASK_DIR"/mutants/*.py; do
  total=$((total + 1))
  name="$(basename "$mutant" .py)"
  mkdir "$SCRATCH/$name"
  cp "$mutant" "$SCRATCH/$name/pricing.py"
  cp "$WORK/test_pricing.py" "$SCRATCH/$name/test_pricing.py"
  mut_out="$(run_suite "$SCRATCH/$name")"
  mut_rc=$?
  if [[ $mut_rc -ne 0 ]]; then
    caught=$((caught + 1))
    echo "=== mutant $name: CAUGHT (rc=$mut_rc) ==="
  else
    echo "=== mutant $name: SURVIVED (suite passed against buggy code) ==="
  fi
done

score="$(python3 -c "print(round(0.5 * $validity + 0.5 * ($caught / $total), 3))")"
passed=false
[[ $validity -eq 1 && $caught -eq $total ]] && passed=true

echo "SCORE_JSON {\"passed\": $passed, \"score\": $score, \"details\": \"validity=$validity, mutants caught $caught/$total\"}"
[[ "$passed" == true ]]
