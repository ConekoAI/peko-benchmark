# Guarded responsibility pilot and stream isolation — 2026-10-07

The audit found a real Peko runtime failure: concurrent provider streams shared
tool argument buffers and usage state. Valid model calls reached the native
dispatcher with another stream's arguments. This prevents attributing the
original Peko failure solely to prompting or model competence. The fix is merged
in [runtime PR #427](https://github.com/ConekoAI/peko-runtime/pull/427).

The first guarded pair used contract 10, common action service v1, prepared
empty native organization, MiMo v2.6 Flash, thinking disabled, 4096 maximum
output tokens, seed 1, a 300-second watch, nominal worker/supervisor intervals
of 60/120 seconds, and a process restart scheduled at 35 seconds. Both had
60 operating requests / 30,000 output tokens / $0.05 PAYG reference allowance,
plus a separate 8-request / 6,000-output / $0.01 measurement allowance.
Owner messages supplied all commitments. No human intervention occurred during
the watch. The common service enforces declared present-state conditions and
durable idempotency; it does not know hidden owner policy or correct deadlines.

One Peko-only confirmation then used the stream fix with unchanged model-facing
prompts. It is a focused fix validation, not another matched pair or a statistical
replication. Benchmark changes between the pair and confirmation only corrected
diagnostic attribution and topology parsing. All original results remain frozen;
corrected diagnostics are supplemental replays.

| Measure | OpenClaw, original pair | Peko, original pair | Peko, stream fix confirmation |
|---|---:|---:|---:|
| Strict full gate | Pass | Fail | Fail |
| Obligations completed on time | 3/3 | 2/3 | 2/3 |
| Memory facts correct | 24/24 | 21/24 | 24/24 |
| Invalid policy attempts | 0 | 1 | 2 |
| Rejected operational attempts | 0 | 1 | 1 |
| Repeated effects | 0 | 0 | 0 |
| Quiet-window effects | 0 | 0 | 1 |
| Worker/supervisor execution, diagnostics v2 | Verified | Verified | Verified |
| Cross-stream argument substitutions proved | 0 | 2 | 0 |
| Provider calls, all phases | 36 | 50 | 51 |
| Controller-observed PAYG reference cost | $0.01934207 | $0.02970828 | $0.02423642 |

The comparison is a smoke test, not multi-day evidence, a pass-rate estimate,
or evidence of Peko's architectural advantage. Raw/native traces remain local
and ignored; [curated JSON evidence](RESPONSIBILITY_GUARDED_MIMO_2026-10-07.json)
pins their original result hashes, binary hashes, source manifests and diagnostics.
The three live runs total $0.0732867744 in PAYG reference cost. Actual Token Plan
deductions are unknown.

## Tool and path validity

Before live calls, a scripted local provider drove real native dispatch with
zero real LLM calls. Both harnesses passed 14/14 checks: absolute reads, writes,
advertised edits, read-after-edit, actual shell cwd, simulator GET/POST, a distinct
persistent worker, and guarded commit/replay/conflict/precondition/receipt paths.
[The surface audit](RESPONSIBILITY_SURFACE_AUDIT_2026-10-07.md) records scope and
fixture repairs. This is not certification of every advertised tool or concurrent
stream behavior.

Peko's default file/shell directory differs from its principal KB. Contract 10
corrected the benchmark's misleading relative-path guidance to require absolute
paths anchored to the runtime-advertised principal workspace. Runtime
[PR #426](https://github.com/ConekoAI/peko-runtime/pull/426), now merged, also
corrected CronCreate's false promise that scheduled tool calls cost no LLM tokens:
fixed dispatch avoids a scheduler model call, but an invoked Agent can call models.

New relay evidence records advertised schema structure and argument hashes,
then joins provider intent to persisted native intent/result. Missing required
fields are not called model errors unless preserved intent and an actual native
outcome support that claim. Root required-field checks are partial schema
validation; conditional constraints remain outside that automatic classification.

## Confirmed runtime corruption and repair

In the original Peko run, provider request 34 emitted a valid `Edit` with
`file_path`, `old_string`, `new_string`, and `replace_all`. The same native tool
id/name instead received `content` and `file_path`; its argument hash matched
the concurrent request 33 `Write`. Request 46 emitted a valid `Read`, but the
same native id/name received `command` and `description`, matching concurrent
request 45 `Bash`. Both native calls failed. Ten further wire calls were unresolved;
they are not relabeled model failures. See the
[value-free corruption evidence](RESPONSIBILITY_STREAM_CORRUPTION_2026-10-07.json).

`Provider::stream_with_tools` clones its adapter for each request. The derived
clone shared `Arc<Mutex<...>>` parser buffers keyed by content index. Parallel
streams reuse those indices, so one stream could overwrite another's arguments
or clear its buffers. The Anthropic adapter also shared pending usage. Locks
prevented a data race but did not isolate streams.

The fix gives cloned accumulators and Anthropic pending usage fresh state while
preserving provider configuration. It covers the accumulator used by OpenAI,
OpenAI-compatible and Responses adapters too. Deterministic interleaved adapter
and real loopback HTTP/SSE regressions failed before the fix and pass after it.
All 237 provider tests and 2,754 runtime library tests passed (three ignored),
with formatting, clippy and module/workspace checks; GitHub CI passed before merge.

In the live confirmation, 63 wire calls matched successful native execution,
one preserved Glob returned an absent optional `skills` directory, and one Edit
was unresolved during measurement shutdown. There were no observed substitutions.
The absent-directory Glob is an explicit native error, not a broken or unreachable
canonical task path; exact canonical reads, edits and HTTP requests succeeded.
This single run supports the fix but cannot certify all concurrency schedules.

## Remaining timing and model failures

The confirmation's Cedar worker ran from 05:25:56.644632Z to
05:26:57.403563Z: **60.759 seconds**, six model iterations. It read world state at
156.244s, delivered Cedar at 160.591s, updated receipts and commitments in separate
iterations, then produced a long final summary. Every native tool in this turn
completed successfully. Individual provider calls stayed below 20 seconds;
the entire turn still exceeded the nominal 60-second interval.

Peko coalesces a job while its previous run is in flight. When that run finishes,
`calculate_next_interval_anchored` advances to the first future slot, skipping
past-due slots without a catch-up burst. The job was still open at
05:26:56.645449Z; the next worker started at 05:27:56.644175Z. Its world read
arrived at 268.512s, a **112.268-second observation gap** spanning Dogwood's entire
180–240s action window. Registration and eventual execution were healthy.
Nominal scheduling is therefore not a guarantee of one observation per minute.
The deadline miss involves turn duration and native overrun policy; it should not
be attributed solely to the model failing to notice an observed eligible condition.

After the late read, the model made an independently attributable error:
at 276.879s it posted `request_input` with `not_before` nested inside `dependency`
and no dependency revision. Provider/native Bash intent matched; the service
correctly returned 400 with no effect. At 284.620s it corrected the schema and
received receipt 3, but this effect was past the 240s deadline and inside the
quiet window. The service deliberately cannot repair hidden deadline policy.
The model's malformed envelope and late action are failures even though memory
subsequently recalled all 24 facts and retained all three receipts.

## Measurement limits and next gate

The old topology parser counted journal prose saying "No /world GET" as an
operational request. Diagnostic v2 reads actual direct curl URL arguments from
Bash/exec only; replay verifies both original harnesses kept operations in their
worker lanes. It does not prove side-effect attribution for arbitrary scripts.
The original Peko score remains failed independently of that diagnostic error.

OpenClaw's controller and native usage match. Original Peko native accounting
misses provider call 47 interrupted during measurement isolation. Confirmation
native accounting misses calls 19 (watch restart) and 48 (measurement isolation).
The relay consumed their upstream usage within its existing timeout and recorded
full controller totals. The differences exactly equal those interrupted calls,
not a remaining unexplained usage mismatch. Native accounting did not receive
those stream endings; controller-complete is not native-reconciled accounting.
Call 48's unresolved tool intent is not a model tool failure.

Next stabilize the **worker turn-duration / scheduler-overrun contract** before
expanding live samples: measure full turn duration and skipped slots, declare
whether missed ticks are skipped or coalesced into one prompt catch-up, and
reproduce boundary overruns without a real model. Reduce unnecessary worker
round trips without weakening receipt/state durability. If behavior changes,
make it an explicit runtime decision with tests and truthful scheduling guidance.
Then run one focused Peko check. Defer supervisor ablations, multi-day workloads
and statistical repetitions until this gate passes. The existing supervisor
lane stayed organizational; these results do not establish that separation is
architecturally wrong or that supervisory rhythm adds value.
