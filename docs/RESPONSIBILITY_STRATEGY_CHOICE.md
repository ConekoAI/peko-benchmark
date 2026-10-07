# Responsibility strategy choice — contract 1

This is a separate experiment from the fixed-worker contract 11. Historical
results remain frozen. The same simulator obligations, owner/review ingress,
watch duration, restart, action service, model, quotas and scoring apply.
Operational cadence and implementation are chosen by the model rather than
prescribed as a 60-second LLM turn.

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
```

These controller-scripted probes test conversational code execution, SDK tool
callbacks, recurring/one-shot native dispatch, process restart, unchanged chosen
job anchors, probe isolation and native history collection. They make zero real
LLM calls and must never be reported as model-authored strategy successes.
