# peko-benchmark

A curated, graded task suite for measuring **agent-harness capability** —
starting with coding (bug fixing, feature work, test writing, frontend) —
and for benchmarking the [peko](https://github.com/ConekoAI/peko-runtime)
runtime against other harnesses (e.g. codex) before MVP.

This repo measures capability and carries the historical field-test reports.
Runtime unit/integration tests answer "did this specific fix hold?"; this repo
answers "can the harness actually do the work, and where does it fall over?"

The [continuity benchmark](docs/CONTINUITY_BENCHMARK.md) adds a separate multi-turn
pilot: accept commitments, revise/cancel them, restart the daemon, then act on
dependency events without stale or duplicate deliveries. It measures continuity
before testing unattended keepalive behavior.
The [first live MiMo pilot](docs/LIVE_PILOT_MIMO_2026-10-05.md) records the
completed scenario, retained setup failures, and usage-accounting findings.
The [fix verification](docs/LIVE_PILOT_MIMO_FIX_VERIFICATION_2026-10-05.md)
confirms full quota retention and clean signal shutdown in a repeat live run.
The [OpenClaw / MiMo pilot](docs/LIVE_PILOT_OPENCLAW_MIMO_2026-10-06.md) also
passed all seven turns on the same model and seed, establishing an external
persistent-assistant baseline for this scenario.

The [responsibility benchmark](docs/RESPONSIBILITY_BENCHMARK.md) adds a shared
delivery simulator and an unattended watch: silent dependency changes, revised
and cancelled commitments, conflicting conversations, a native process
restart, blocked-input escalation, and idle periods. It reports obligation,
deadline, memory, repetition, quietness, intervention, and idle-usage metrics.
The [paired live MiMo pilot](docs/LIVE_PILOT_RESPONSIBILITY_MIMO_2026-10-06.md)
passed once per harness; larger runs are deferred while stabilizing the runtime.
The [prompt and cache investigation](docs/PROMPT_PROFILE_MIMO_2026-10-06.md)
records the cost concentration, runtime fixes, and diagnostic verification.
The [interface parity investigation](docs/RESPONSIBILITY_INTERFACE_PARITY_2026-10-06.md)
records the shared supervisor API correction, the subsequent failed pair,
and a benchmark cleanup repair with offline verification.
The [state and cadence validation](docs/RESPONSIBILITY_STATE_COVERAGE_MIMO_2026-10-06.md)
adds shared status reconciliation instructions and measures timely observation coverage.
The runtime restart fix is merged; the flattened state/cadence pair has correct
memory for both, but Peko misses two deadlines while OpenClaw passes.
The [topology pilot](docs/RESPONSIBILITY_TOPOLOGY_MIMO_2026-10-06.md) implements
the intended division between organizational supervision and a recurring task
worker. Peko's repaired setup formed that arrangement, but both harnesses stopped
before the unattended watch, so task-performance results are unavailable.
Larger trials remain deferred while stabilizing setup and handoff.

## Methodology (read before trusting a number)

1. **Same model, same task, same grader — different harness.** The model is
   the biggest confound in any harness comparison. Pin the model per
   comparison run (`PEKO_MODEL_ID` / `CODEX_MODEL`) or you are benchmarking
   models, not harnesses.
2. **n ≥ 3 reps per task × harness.** Real-LLM runs are noisy; a single
   run per cell is anecdote. The runner reports pass rate across reps.
3. **Every task has a deterministic grader.** No human judgment in the
   scoring path: graders run test suites, mutation checks, or node tests
   and emit a score. Human review is for *failure-mode classification*
   afterwards (read the transcripts), not for grading.
4. **Graders are hardened against gaming.** Where the task ships visible
   tests, the grader restores pristine copies before running; where the
   task is spec'd, the grading tests are hidden from the agent.
5. **Cost ceiling.** Every rep costs real tokens. Run single reps while
   iterating on the suite; reserve full matrices for milestone checks.

## Layout

```
tasks/<field>/<task-id>/
  task.toml      # id, field, prompt, timeout_secs
  fixture/       # the project the agent starts from (copied per run)
  grade.sh       # deterministic verifier → SCORE_JSON line
  setup.sh       # (optional) custom fixture preparation
  mutants/       # (testing tasks) buggy variants the agent's tests must catch
  grade_tests/   # (hidden-test tasks) tests the agent never sees
harnesses/
  peko.sh        # drives peko (peko-runtime repo) in an isolated HOME
  codex.sh       # drives the codex CLI
  lib/peko_isolate.sh
runner/run.py    # matrix runner: tasks × harnesses × reps → reports/
runner/continuity.py  # multi-turn continuity runner + deterministic scorer
runner/continuity_peko.py  # native adapter with isolated passphrase vault
runner/continuity_openclaw.py  # isolated native OpenClaw Gateway adapter
runner/continuity_proxy.py  # Anthropic accounting relay; optional common wire policy
runner/responsibility.py  # native unattended watch and continuation controls
runner/responsibility_simulator.py  # shared dependency world and action ledger
runner/responsibility_drivers.py  # native cron/heartbeat adapters
runner/responsibility_audit.py  # audit native messaging attempts during watch
runner/prompt_profile.py  # opt-in private request fingerprints and JSON sizes
runner/profile_usage.py  # offline phase usage and prompt-profile analysis
runner/memory_path_probe.py  # short native shared-memory write/read diagnostic
profiles/        # explicit provider configuration for continuity pilots
scenarios/continuity/ # sequential events; controller-owned expected actions
scenarios/responsibility/ # shared world timeline; controller-owned oracle
tests/          # offline grader mutation checks + adapter contracts
reports/         # one directory per benchmark run (gitignored)
```

## Quick start

```bash
# List available tasks
python3 runner/run.py --list

# One task, one harness, one rep (smoke test — cheap)
PEKO_BIN=~/workspace/ConekoAI/peko-runtime/target/debug/peko \
PEKO_API_KEY=$MINIMAX_API_KEY \
python3 runner/run.py --tasks bugfix/py-cache-invalidation --harnesses peko --reps 1

# Full comparison matrix (expensive — real LLM calls)
PEKO_BIN=~/workspace/ConekoAI/peko-runtime/target/release/peko \
PEKO_API_KEY=$MINIMAX_API_KEY \
OPENAI_API_KEY=... \
python3 runner/run.py --tasks all --harnesses peko,codex --reps 3 --tag pre-mvp
```

Results land in `reports/<timestamp>-<tag>/`: per-run transcripts,
`result.json`, `grade.txt`, plus aggregate `results.jsonl` and
`summary.md`.

## Task contract

`task.toml`:

```toml
field = "bugfix"          # bugfix | feature | testing | frontend | ...
description = "..."       # one line, for --list
timeout_secs = 600        # per-rep harness budget
prompt = """..."""        # the task as given to the agent
# prompt_file = "prompt.md"  # alternative to inline prompt
```

Runner → agent: the fixture is copied to a fresh `work/` dir per run, and
the runner appends a standard suffix to the prompt naming the absolute
`work/` path. The agent must make all changes inside it.

Runner → grader: `grade.sh <workdir>`; exit 0 = pass. The last stdout
line MUST be:

```
SCORE_JSON {"passed": true, "score": 1.0, "details": "..."}
```

`score` in [0,1] allows partial credit; `passed` is the binary gate.

Optional `setup.sh <task_dir> <workdir>` replaces the default
`cp -R fixture/ workdir/` (use it for tasks that need dependency
installation or git repo initialization).

## Harness contract

`harnesses/<name>.sh <workdir> <prompt_file> <out_dir> <timeout_secs>`:

- Runs the agent on `<workdir>` with the prompt from `<prompt_file>`.
- Writes the full transcript to `<out_dir>/transcript.txt`.
- Exit 0 = the harness ran to completion (regardless of task success);
  non-zero = harness failure (timeout, crash, auth). The runner grades
  the workdir either way and records `harness_completed`.

### peko.sh env

| Var | Default | Notes |
|---|---|---|
| `PEKO_BIN` | — (required) | path to the `peko` binary |
| `PEKO_API_KEY` | — (required unless `PEKO_SKIP_MODEL_ADD=1`) | provider key, stored via `peko model add --key` |
| `PEKO_API_FORMAT` | `anthropic_messages` | explicit adapter API format |
| `PEKO_BASE_URL` | `https://api.minimaxi.com/anthropic` | API endpoint prefix |
| `PEKO_MODEL_NAME` | `MiniMax-M3` | wire model id |
| `PEKO_MODEL_ID` | `minimax-MiniMax-M3` | catalog id the principal is pinned to |
| `PEKO_MODEL_SPEC` / `PEKO_MODEL_COMPAT` | — | optional capability/pricing and compatibility JSON |
| `PEKO_CONTEXT_WINDOW` / `PEKO_MAX_OUTPUT_TOKENS` | — | optional model limits |
| `BENCH_TMP_ROOT` | `/tmp/peko-bench` | isolation root (short path: Unix socket limit) |
| `KEEP_TEMPDIR` | — | keep isolated HOME for debugging |

### codex.sh env

| Var | Default | Notes |
|---|---|---|
| `CODEX_BIN` | `codex` (PATH) | |
| `OPENAI_API_KEY` | — (required) | |
| `CODEX_ARGS` | `exec --full-auto --skip-git-repo-check` | adjust to your installed codex version |
| `CODEX_MODEL` | unset | appended as `--model <id>` when set — **pin it for comparisons** |

## Adding a task

1. `mkdir tasks/<field>/<task-id>` with `task.toml` + `fixture/` + `grade.sh`.
2. Validate the grader both ways **without an LLM**: it must FAIL on the
   pristine fixture and PASS on a known-good solution. A grader that has
   never been seen to fail proves nothing.
3. Keep tasks small (5–15 min for a competent agent) and graders fast
   (seconds). Depth per task beats task count.

## Roadmap

- More fields: refactor, debugging-with-logs, docs, multi-file feature.
- SWE-bench Verified / Terminal-Bench subset adapter for instant
  comparability with published baselines.
- Browser-graded frontend tasks (playwright screenshot/DOM diff).
- Continuity and unattended responsibility pilots are implemented; multi-day
  workloads, mechanism controls, compaction and interrupted effects follow.
- Other peko-specific tasks: subagent delegation and workspace skills.
- OpenClaw continuity adapter is implemented; see its pilot report for setup,
  reproducibility and limits of the initial comparison.
- Native/provider token reconciliation and phase cost capture are implemented
  for the MiMo continuity and responsibility adapters.
