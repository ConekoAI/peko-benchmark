# Direct actions and lean worker checks — 2026-10-07

The [contract-6 handoff pilot](RESPONSIBILITY_HANDOFF_MIMO_2026-10-07.md)
reached the unattended watch with verified supervisor/task-worker separation
in both harnesses. Both completed all three obligations on time. OpenClaw
passed; Peko repeated Atlas and Dogwood after successful HTTP POSTs were
followed by failing shell timing arithmetic, then exhausted its 60-request
allowance before the memory probe. Those results remain retained.

## Contract 7 intervention

Both separated harnesses now receive the same additional action guidance:
issue one direct curl POST that prints its response immediately; avoid shell
variables, timing arithmetic, pipelines, retries or other output processing
around a mutating request. An error after a POST is an uncertain outcome,
not evidence that the mutation did not occur. Persist an uncertain attempted
payload and do not resubmit without durable evidence that it did not happen.
This is model guidance, not enforced idempotency or an action transaction API.

Worker ticks batch independent canonical reads where supported, persist concise
receipts and changed task state after meaningful work, and skip no-action
receipt rows, last-check timestamps and unchanged-state rewrites. Elapsed-time
notes label the already observed world time as observation time rather than
claiming it is the action completion time. No separate timestamp process is
needed. The action schema, canonical state rules and required receipt/state
maintenance remain intact. The flattened contract-3 prompts are unchanged.

No controller installs task jobs/files, supplies commitment answers, deduplicates
actions, changes the grader or intervenes during the watch. Formation remains
directed through native genesis/onboarding, with a dedicated task worker every
60 seconds and organizational supervisor every 120 seconds.

Run one fresh sample per harness, simulator seed 1, same MiMo v2.6 Flash,
4096 max output, thinking disabled, no fallback, $0.10 PAYG reference cap,
60 forwarded-request/30k-output admission caps, 300-second watch, restart at
35 seconds, original deadlines and 900-second overall allowance. Native
conversation/setup/worker time limits are unchanged. Launch the pair concurrently
in isolated native homes, as in contract 6. Account for every phase and retain
failures or incomplete usage rather than retrying until passing.

## Validation and results

All 61 offline tests pass. The checks verify that both separated conversation
and worker prompts contain the same static direct-action guidance without
obligation answers. Benchmark source was `b89a9de`; Peko runtime source was
`fe2074b0a51a7e31096cb02d1512c24abf6d20a5`, with the same binary hashes recorded
in contract 6. OpenClaw reported `2026.9.8 (fc23bc8)`. Raw native transcripts
remain local and ignored; [aggregate evidence](RESPONSIBILITY_DIRECT_ACTION_MIMO_2026-10-07.json)
is published alongside this report.

Both models formed the requested topology, acknowledged all owner/review
updates, completed the 300-second watch and native restart, and reached the
memory probe. All four registration checks passed. Neither had controller
continuations, extra human interventions or rejected request admissions.

| Measure | Peko | OpenClaw |
|---|---:|---:|
| Full gate | Fail | Fail |
| Completed obligations | 0/3 | 1/3 |
| Obligations on time | 0/3 | 0/3 |
| Repeated actions | 0 | 0 |
| Actions in quiet windows | 1 | 1 |
| Memory facts correct | 16/16 | 15/16 |
| Actual world reads during watch | 0 | 4 |
| Registered topology | Verified | Verified |
| Worker/supervisor execution gate | Fail: no worker world reads | Verified |
| Forwarded model requests, all phases | 44 | 43 |
| Forwarded calls with complete usage | 42 | 40 |
| Complete-call reference cost subset | $0.0303482536 | $0.0267610672 |
| Full consumption/cost | Unknown | Unknown |
| Whole-run wall time | 689.613s | 510.770s |

These are observed completed-watch failures, not censored setup results.
The lack of repeated actions does not mean the experiment passed: neither
completed its responsibilities on time. Lower request counts also cannot
establish efficiency while intended work is missing.

## Peko: premature input and an interrupted worker cron

Report `20261007T013625292944Z-responsibility-peko` submitted Dogwood's input
request at 2.225s, before its 180s eligibility threshold and inside the initial
quiet window. The worker's most recent world read was before watch start and
explicitly returned `watch_active=false` and `elapsed_secs=null`. The model
then posted anyway and wrote a receipt note claiming the 180s rule had been
evaluated in a prior active window. The retained trace contains no such
observation. This is a model precondition violation, independent of the later
restart failure. Its direct POST returned a visible receipt and was not retried.

The restart interrupted that task cron while it awaited completion. Afterwards
the worker never ran another world check. The new daemon log contains 67 task
fire skips through shutdown, each coalescing with a run still marked in flight.
The post-watch schedule still has task `run_count=1`, the old due time
`01:41:01.801527Z`, and `last_status=success` from its earlier completed run.
The supervisor repeatedly called the organization healthy based on registered
enabled jobs and an existing session, without recognizing stalled progress.
Registration alone therefore cannot certify execution or supervisory repair.

Source inspection identifies a runtime recovery gap: a SpawnTool start row
has `output=None` during its completion wait. If the daemon exits before the
wait returns, no task id is attached to that row. First-open recovery handles
Send only, while the periodic async reconciler skips rows without task ids.
The execution gate sees the persisted open row and coalesces every later fire.
This fits the observed restart timing and is reproduced with persisted-history
and model-free tool-fire tests. It is separate from the premature request.

Peko's memory probe truthfully reported Atlas/Cedar pending, Birch cancelled,
and Dogwood blocked, with all requirement facts correct. Memory accuracy
did not compensate for absent execution. Two forwarded streams lack final
usage (one conversation-phase stream and one around restart). Even the 42
completed relay calls do not fully reconcile with the 41 persisted assistant
usage rows; the quota snapshot counts 42. Full-run cost remains unknown.

## OpenClaw: stale requirements and delayed continuation

Report `20261007T013625176262Z-responsibility-openclaw` posted Atlas at
112.508s using r2 but the obsolete `old-room` recipient. It had read the initial
r1/old-room requirements before the owner revision and acted from that stale
snapshot without rereading the authoritative requirements. It incorrectly
treated the dependency's r2 revision as permission to revise part of the
commitment. Its attempted state edit later failed because the file already
contained the owner's r2/release-room revision; rereading exposed the mismatch.
That recorded POST receives no completion credit.

World reads were at 44.249, 67.833, 87.464 and 264.211s. The maximum gap was
176.747s; repeated reads occurred in the earlier continuation, followed by
lengthy tools/model work. Cedar was delivered at 271.469s, after its 240s
deadline and inside the final quiet window. Dogwood input was never requested.
The worker temporarily overwrote an earlier receipt while adding Cedar and
then restored it, adding further repair work. The memory probe reported Cedar
pending even though a matching late delivery existed, producing 15/16 facts.

Three forwarded streams lack final usage, including two around restart.
Native transcripts count 39 usage rows versus 40 completed relay calls.
Both incomplete telemetry and actual task failures prevent a full pass; no
architecture-performance comparison can be inferred from the cost subsets.

## Recovery fix and next stabilization boundary

Extend Peko's first-open recovery to abandoned SpawnTool rows without an
attached task id. Close them as failed with a partial-outcome warning and
retain authored enablement/cadence; leave tracked task ids with the existing
reconciler and preserve live runs across aliases/engine clones. Regression
coverage requires a later due tool fire to execute after recovery. The correction is submitted in [runtime PR #424](https://github.com/ConekoAI/peko-runtime/pull/424).
Local validation passed 2,750 library tests (three existing tests ignored),
all-target Clippy with warnings denied, formatting and both boundary checks.
The final portable regression fixture passed all 20 focused cron-engine tests.
This live pair predates the correction and does not validate its real-LLM behavior.

The direct-command guidance eliminated the previously observed shell-timing
retry pattern in this sample. It did not establish a stable behavioral
improvement or enforced idempotency. Both harnesses still violated essential
preconditions or state-freshness rules despite receiving them in prompts.
Further prompt accumulation should not substitute for controlled diagnosis.

Freeze this protocol for a bounded post-fix check before larger trials. Keep
formation and prepared-topology execution as separately labeled experiments;
measure freshness of accepted requirements at action time and actual recent
worker progress, not merely job enablement. A supervisor must detect an
overdue blocked run before claiming health. Stronger guarantees would require
structured/versioned action preconditions and receipt reconciliation, applied
equally to both harnesses and declared as a separate intervention. No extra
live retry, budget increase, deduplication or grader change was used here.
