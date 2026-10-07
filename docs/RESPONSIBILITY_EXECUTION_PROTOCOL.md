# Responsibility execution protocol — contract 11

This stabilization protocol separates organization formation from execution. It
is not a new result or evidence of superiority. Contract 7 scores stay frozen.

## Formation tracks

`--formation model` retains model-driven native genesis/onboarding. All its
calls remain in the operating allowance, and phase costs report formation
separately. It assesses whether a harness can organize the work itself.

`--formation prepared --topology separated` is a declared controller intervention
for execution-only trials. Native Peko genesis still establishes identity and
memory scaffolding, then the controller installs an empty persistent child,
worker role, two native jobs and empty shared notes while its daemon is stopped.
OpenClaw uses native baseline workspace setup and automation registration, with
an empty instruction/identity fixture. No old transcript, obligations, receipt,
expected status or future dependency state is copied. Owner chat supplies every
requirement through the normal conversation route.

Prepared schedules are delayed until owner/review conversations finish, then
armed with a first worker tick after 20 seconds and organizational supervision
at a 120-second cadence (60-second worker cadence). Peko starts supervision
120 seconds after arming; OpenClaw retains its native heartbeat phase, recorded
in topology snapshots. Its system-owned heartbeat is disabled through native
configuration during preparation and enabled through configuration when arming. The 20-second lead permits native readiness/registration checks before the task
clock starts. Peko restarts its native daemon when arming; OpenClaw enables native heartbeat
configuration and restarts its gateway, then uses cron.update for its client-owned
worker only. No native storage paths or system-owned jobs are edited. These are preparation, separate from the measured restart
at 35 seconds. Registration and actual execution remain required. Schema fixtures
are pinned by the source manifest; registration failures are retained.

These tracks answer different questions and must never be pooled as a pass
rate or used as a clean formation-cost comparison: prepared OpenClaw skips LLM
persona onboarding while Peko still runs a minimal native genesis.

## Allowances and measurement

The operating allowance remains 60 forwarded requests, 30,000 output tokens,
and the supplied PAYG reference cap per harness. Probe requests have a separate
8-request, 6,000-output-token, $0.01 reference allowance. This allowance does not
restore operating calls, hide rejections, or retroactively rescue deadlines.
All requests and costs, including probe, remain in aggregate/native accounting.
After the watch and post-watch topology snapshot, the controller disables
native schedules and restarts the owned runtime before sending the memory
probe. This declared measurement intervention is recorded outside the watch;
it cannot rescue missed obligations. It prevents background tasks from spending
the probe allowance. Any interrupted usage remains unknown; suspension does not
repair accounting. The policy keys are present in the example JSON schema.
Contract 8 pilots lacked this isolation and showed the old four-field example;
those results remain frozen and policy omissions are not evidence of forgetting. Reference amounts are not actual
Token Plan deductions. Peko's native cost backstop includes the probe allowance.

## Diagnostics

- Every new GET records its returned snapshot in the controller ledger.
- Observed-precondition diagnostics distinguish readiness at POST time from a
  matching ready build the worker actually read. Blocked-input observations
  must reach the owner-specified threshold. Historical ledgers can be replayed
  using their read world-version and recorded changes, without changing scores.
- Receipt retention compares non-memory action receipts with the final native
  receipt file. It reports missing numeric references, without claiming proof
  of semantic correctness or an append-only mutation history.
- Memory measurement explicitly distinguishes missing probes from invalid
  probes and valid measured facts. Missing measurement is not forgetting.

Contract 9 CLI runs require these diagnostics for a pass, and the memory probe
also measures explicit deadline and blocked_at values (null where unspecified):
24 facts rather than 16. These requirements are explicit scenario flags; replay
of older scenarios retains its old grade. A missing receipt file is unmeasured
and cannot satisfy the new gate. Observed compliance measures policy use;
recall alone cannot prove compliance.

## Gates before the next experiment

Run one prepared, unguarded pilot per harness to validate registration, native
execution, restart, usage reconciliation and these diagnostics. Retain failures;
do not spend repeated samples on an unstable fixture.

Only after execution stabilization, add a separately versioned common action
service with explicit preconditions, durable receipts and idempotency. Measure
invalid attempts separately from prevented external effects. Then compare the
same workers with organizational supervision enabled/disabled under a declared
organizational fault. Supervisor value means faster truthful recovery or more
completed obligations after accounting for its cost. Intentional pause and
cancellation must not be repaired away. Expand workload and repetitions only
after those gates pass.

## Contract 10: interface evidence and common action service

Contract 10 corrects canonical-file path guidance: Peko's native file/Bash
working directory is `<data>/workspaces`, while its principal KB lives in the
principal workspace. Resolve the advertised principal KB anchor to absolute
paths. OpenClaw's default file/exec directory is its configured agent workspace.
The same logical filenames are used by both. Prepared Peko jobs now obtain the
stable principal id from `principal.toml`, even when genesis deleted all jobs.

Run `python3.12 runner/responsibility_surface_smoke.py --driver peko|openclaw`
with the native binary/entry profile. It uses a local scripted Anthropic server,
zero real LLM calls, and real native decoding and dispatch. It checks absolute
and relative reads, writes/edits, cwd, HTTP world/action calls, distinct persistent
worker-session execution, and the guarded commit/replay/conflict/precondition
and receipt-lookup routes. A relative Peko read is expected to fail; the corrected
instructions require absolute paths. Failure of that expected negative case does
not count as a working path. Retain fixture failures as fixture failures.

Provider evidence now records advertised tool names, schema hashes, root required
keys and property types; response tool ids/names, argument keys/hashes and stream
completeness; and subsequent request tool-result ids/errors/content hashes.
Argument values and prompt text are not captured in this evidence. Native intent
and result must match the provider evidence before a missing required argument
is attributed to a model choice. Valid-looking calls that fail remain unresolved
native errors requiring investigation. Root-key checks are not full JSON Schema
validation, and the smoke test proves only the covered surfaces. Historical runs
lack provider tool-call evidence and cannot be retroactively given this stronger
attribution.

The relay continues bounded upstream consumption after a downstream disconnect,
retaining completion/usage if actually received. This improves controller spend
accounting, not proof of native receipt or native quota attribution. Missing
usage stays unknown; aggregate native/controller discrepancies still fail the
accounting gate.

`--action-mode guarded` is a separate action-service-v1 experiment; default `raw`
preserves unguarded behavior. Operational POST bodies are `{action,preconditions}`.
The service checks active watch and an explicit dependency readiness/revision
against current public world state. Blocked-input requests also supply a finite
`not_before` threshold. It does not know hidden owner obligations, cancellations,
recipients, deadlines, future changes or the correct threshold. Those remain
model responsibilities. Incorrect owner policy can therefore still commit an
invalid effect, and the grader still penalizes it.

Committed effects and their responses are one SQLite transaction with FULL
synchronous durability. Keys are `send_release:<delivery_key>` and
`request_input:<project>`. Exact committed-envelope retries return the original
receipt without another effect, including after service reopen or watch end.
Different envelopes under a committed key return 409. Invalid schemas return 400;
unsatisfied declared conditions return 412. Neither commits an effect. Rejected
keys remain eligible for a later valid attempt. `GET /receipts` exposes only past
committed receipts, never future state or grading answers. Memory probes retain
the plain memory schema.

Every attempt, response, rejection and replay remains in the audit ledger.
Operational completion/latency use committed effects. The report separately
measures invalid policy attempts, boundary rejections, idempotent replays and
committed effects. Invalid attempts fail the guarded pass gate even if the service
prevented their effects. Receipt retention uses durable service receipt ids in
this track. The SQLite file is authoritative for effects; the JSONL ledger is
an audit mirror. Controller-crash recovery of the entire benchmark clock/ledger
is not implemented or claimed; the measured restart is of the native harness.

Do not pool guarded/raw scores, model/prepared formation, or different contract
versions. Organizational-supervisor ablation remains behind execution, interface
and accounting stability gates.

## Diagnostics replay v2 after the first guarded pair

The first guarded pair used frozen benchmark commit `f7c68f3`. Wire/native
comparisons revealed Peko parser corruption: Edit got Write arguments, and Read
got Bash arguments from concurrent responses. Matching argument hashes prove
these substitutions; unmatched/missing calls remain unresolved. Runtime PR
[#427](https://github.com/ConekoAI/peko-runtime/pull/427) isolates cloned stream
buffers and Anthropic pending usage. Successful sequential surface tests do not
prove concurrent correctness. Interleaved adapter and actual concurrent HTTP/SSE
regressions both reproduced the defect without LLM calls.

Diagnostics v2 also fixes a benchmark false positive: a journal command saying
"No /world GET" was classified as an operational request by substring search.
Only direct Bash/exec curl URL arguments count now; prose and a corrupted Read
with a command argument do not. This matcher covers the declared direct-command
contract; complex shell forms require separate investigation. Historical result
files are preserved. A supplemental replay records corrected diagnostics,
without silently changing their score or attributing every missing action to
one cause. The Peko-only confirmation uses unchanged model-facing contract 10
with v2 diagnostics and the fixed runtime; it is a fix validation, not another
sample pooled into a parity claim.

## Scheduling evidence after the stream fix

Configured intervals are nominal schedule slots, not guaranteed observation
frequency. Peko coalesces in-flight jobs and advances to the first future slot
after completion; it skips past-due slots without a catch-up burst. A 60.759s
worker turn in the confirmation skipped a 60s slot and left a 112.268s gap in
world observations. All tools in that turn succeeded. A registered healthy job
can therefore still miss an entire deadline window.

Keep full-turn duration, native run history, actual observation gaps and eligible
observations separate. A deadline miss without a timely observation is not the
same failure as choosing incorrectly after reading eligible state. Specify and
test overrun/catch-up semantics before changing them, then stabilize the worker
before supervisor ablation or statistical samples. See the
[guarded pair and confirmation](RESPONSIBILITY_GUARDED_MIMO_2026-10-07.md).

## Contract 11: fewer worker response rounds, unchanged cron policy

The worker prepares receipt and changed commitment writes in the same model
response and requests a single brief final sentence. Native writes may still
execute serially; this is fewer model round trips, not parallel file mutation
or a transaction spanning files. Exact receipts, action payloads and required
state updates remain durable. There is no shorter hard timeout, wider deadline,
extra polling, catch-up policy, or hidden obligation answer.

Both separated harnesses receive this static guidance. One Peko-only follow-up
checks the known overrun, not cross-harness parity under a new contract. The
runtime now advertises nominal intervals and records scheduled/finish/next times
plus skipped interval slots. New `native_cron_timing` diagnostics read these
Peko audit fields, deduplicate runs, measure whole-turn durations and preserve
open runs as censored. Legacy or OpenClaw evidence without this native format
is unmeasured, not zero overruns. These diagnostics do not change score gates
or forgive missed deadlines or incomplete native usage reconciliation.

`native_reconciliation_diagnostic` checks whether a complete controller-minus-
native usage difference exactly equals complete upstream calls whose client
disconnected. Interrupted/incomplete usage remains unknown. This attribution
does not change the strict native equality gate or count as a native quota fix.

The [one focused contract-11 pilot](RESPONSIBILITY_LEAN_WORKER_MIMO_2026-10-07.md)
failed with clean wire/native intent and exact usage reconciliation. The model
lowered an owner threshold after a 412; a later provider response took longer
than Cedar's remaining deadline headroom. Batched writes and a brief final
response did not bound that turn. Keep policy adherence, upstream response
latency and scheduler skips separate; more live samples remain deferred.
