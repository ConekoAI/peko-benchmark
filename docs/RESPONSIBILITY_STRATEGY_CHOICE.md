# Responsibility strategy choice — contract 2

This is a separate experiment from the fixed-worker contract 11. Historical
results remain frozen. The same simulator obligations, owner/review ingress,
watch duration, restart, action service, model, quotas and scoring apply.
Operational cadence and implementation are chosen by the model rather than
prescribed as a 60-second LLM turn.

Contract 2 adds the same offline preflight and failed-job recovery instructions
to both harnesses. Contract 1 samples remain frozen. Before registering or
repairing generated code, the model must author and run bounded local tests of
the active parser/action branch, inactive return, policy changes, blocked
thresholds, unchanged state, response rejection/replay and uncertain receipt
reconciliation. Tests use fictional facts and mocked HTTP. No operational
solution, test implementation or hidden scoring facts are supplied. Native tool
outputs and retained test sources permit auditing; the instruction alone does
not certify that tests actually ran or covered every branch.
Each workspace receives `NATIVE_AUTOMATION.md` containing the same public native
capability instructions supplied to conversations, so supervision can retrieve
the recovery interface without relying on another session's transcript.

The common contract explicitly documents `action_key` and numeric `receipt`
fields and requires actual response bodies in the append-only receipt log.
The supervisor may run offline tests and repair native job eligibility, but
may not execute the operational procedure or force a live fire. It must inspect
next due time/history and replace a job through native scheduling when necessary,
disabling/removing the previous job to prevent duplicates. File edits alone do
not reset failure state. This remains a test of model behavior, not a controller
repair of its strategy.

## What the model chooses

Both Peko and OpenClaw may author Python or other saved procedures, register
native recurring code jobs, choose LLM worker cadence, and arrange one-shot
tool/code jobs. All operational work must belong to native durable scheduling;
detached processes, OS cron and raw provider API calls are excluded. At most
eight enabled operational jobs are allowed, with intervals of at least five
seconds. Scripts must be bounded and serialize operational effects and durable
receipt/state writes. Tight timing does not imply an exact-time guarantee.

The controller prepares empty shared notes and independent organizational
supervision at 120 seconds in the default pilot. Peko also receives an empty
task session/role as a possible coordinator, and the stdlib Workflow SDK with
file hashes recorded in metadata. No operational procedure, task job or
obligation fact is controller-installed. Owner conversations supply the facts
and the model creates or updates automation from them. Reviewer proposals
cannot override accepted owner requirements.

Peko uses `CronCreate` → `Workflow`, `Bash` or `Agent`. One-shot `at`/`delay`
jobs delete after firing, including failed fires; this is advertised. The daemon
poll interval in the fixture is five seconds. Workflow scripts must explicitly
add the provisioned `.benchmark-sdk` directory to `sys.path` before importing
`peko_workflow`; package discovery is not automatic. Use absolute `file_path`
for Read/Write/Edit SDK calls.

Peko disables jobs after three consecutive failures in this fixture.
`CronUpdate enabled=true` resets that budget without changing `next_run`;
changing cadence requires delete/recreate. OpenClaw applies five-minute backoff
after three failures. Enabling an already-enabled job at the same interval
resets its error counter but preserves its delayed `nextRunAtMs`. Explicit
`automations edit <id> --disable --json` followed by
`automations edit <id> --enable --every <duration> --json` re-arms eligibility;
verify next due time and replace the job if still too late. Native probes verify
these exact routes, including scheduled success after restart.

OpenClaw's pinned native CLI supports `--command-argv`, `--every`, `--at` and
`--delete-after-run`, as well as agent-turn and headless-script jobs. Native
command jobs execute without an LLM response. API history collection uses the
read-only Gateway `cron.runs` method with `scope=all` and pagination: the
`automations runs` CLI requires a job id and is unsuitable for collecting reaped
one-shots across the experiment.

## Scoring and evidence

Completion, deadlines, cancellation/revision correctness, repetitions, policy
attempts, memory, retained receipts, quietness, restarts, human intervention and
provider/native usage reconciliation keep their existing gates. Strategy choice
does not forgive an early action, late effect, missing receipt or accounting gap.
The guarded service still evaluates caller-declared preconditions; it does not
enforce hidden owner thresholds. An authored script must preserve those rules.

Registration verification accepts code jobs and one-shots instead of insisting
on a fixed Agent job. Startup arms only organizational supervision and preserves
the model's operational job times. OpenClaw HTTP readiness precedes asynchronous
heartbeat declaration reconciliation; arming waits up to 20 seconds for the
configured native heartbeat before starting the watch. Measurement isolation disables every chosen
operational job before the memory probe. Native completed job history is required
as execution evidence; source-file presence or an LLM claim is insufficient.
Script/data artifacts are retained with hashes; bundled SDK and credentials are
excluded. Peko timing measures the chosen operational job IDs, rather than only
the historical `responsibility-monitor` label.

Native job execution does not establish the origin of every HTTP effect. The
latest-read diagnostic lacks causal attribution across concurrent scripts;
operational jobs must serialize, and this limitation is stated in each result.
Script-internal side effects also have no corresponding provider tool-call
intent hash. These are distinct from decoding/dispatch failures in model-issued
tool calls. The common simulator ledger grades actual effects independently.

The short pilot provides an initial strategy-selection test, not multi-day
maintenance evidence, a provider latency guarantee or a novelty claim. Keep
setup/generation cost in total spend; moving reasoning into code must not make
that cost disappear from the comparison.

## Commands

Use the same MiMo Flash profile and allowances as the fixed-worker trial:

```sh
export PEKO_API_KEY="$MIMO_API_KEY"
export PEKO_BIN=/absolute/path/to/peko-runtime/target/debug/peko
source profiles/mimo-v2.6-flash.sh
source profiles/openclaw-mimo-v2.6-flash.sh
python3.12 runner/responsibility.py --driver peko \
  --execution-policy strategy-choice --formation prepared --topology separated \
  --action-mode guarded --mode supervisory --seed 1 --scale 1 \
  --profile-prompt --budget-usd .05 --timeout-secs 900
# Repeat once with --driver openclaw when native surface checks pass.
```

For an installed Peko binary outside the development checkout, also set
`PEKO_WORKFLOW_SDK_SOURCE` to the SDK package directory containing `client.py`.

Before live inference, verify native execution and the empty strategy fixture:

```sh
python3.12 runner/responsibility_automation_smoke.py --driver peko
python3.12 runner/responsibility_automation_smoke.py --driver openclaw
python3.12 runner/responsibility_recovery_smoke.py --driver peko
python3.12 runner/responsibility_recovery_smoke.py --driver openclaw
```

These controller-scripted probes test conversational code execution, SDK tool
callbacks, reuse of Peko's listed trunk address through native session reads,
recurring/one-shot native dispatch, process restart, unchanged chosen
job anchors, probe isolation and native history collection. They make zero real
LLM calls and must never be reported as model-authored strategy successes.

The recovery probes reproduce the contract-1 active-parser error with a
controller-authored marker procedure, observe three native errors, inspect
history and failure eligibility, patch through the real file tool, self-test
offline, restore scheduling and restart. A healthy run is never manually forced;
the probe requires recurring native success with no model calls during the wait.
