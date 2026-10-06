# Responsibility state reconciliation and cadence coverage — 2026-10-06

This stabilization step addresses the stale statuses and timing blind spot in
the [previous pair](RESPONSIBILITY_INTERFACE_PARITY_2026-10-06.md). Contract
version 3 clarifies state maintenance for both harnesses; new controller-side
coverage diagnostics identify whether an obligation had a timely observation.
The simulator's action semantics, grader, deadlines and timing are unchanged.
This is iterative debugging on seed 1, not an independent reliability sample.

## Changes and validation

Both harnesses now receive instructions to maintain one canonical commitment
table, record each exact action/time/receipt, update current state before ending
the turn, and reconcile requirements with receipts before the memory probe.
An old pending cell cannot override a later matching release receipt. A receipt
alone does not certify a correct payload; unsupported/stale/cancelled/premature
actions still fail grading. Requests for input leave releases blocked.

The controller does not create, repair, or return commitment states for agents.
No status answers or hidden future state appear in these instructions. The
change is a shared task-prompt clarification, not an enforced state ledger or a
runtime storage fix. Native Peko genesis may organize the instructions into
shared memory and cron; OpenClaw receives its configured heartbeat prompt.
Results across contract versions must not be combined as one unchanged task.

`cadence_coverage` reconstructs present dependency states in ledger order and
records eligible read times and deadline slack for each positive obligation.
It reports actual read gaps, first-read offset, unobserved watch portions, and
complete versus censored horizon. Cancelled commitments are excluded. Ready
builds must match the accepted revision; blocked-input observations require a
not-ready dependency within the stated time window. This never changes scores
or tells the agent the expected action. A zero-slack observation or a long tool
call can still be insufficient to finish before the deadline.

All **56 offline tests passed**. New tests cover revision changes, actual
observed changes, censored/empty watches, boundary reads, lack of inspection
versus inaction after inspection, and parity of supplied state instructions.
Existing tests cover malformed actions, stale/cancelled/premature/duplicate
attempts, unknown usage and the bounded relay drain. The runtime is unchanged
in the initial diagnostic at `1e84d66a8af8219d4242837317aa620e166d1334`.

## Previous pair, diagnosed without new model calls

The coverage extractor was applied to retained version-2 traces; their result
files and grades were not rewritten. Existing scalar grading metrics match.

| Coverage diagnostic | Peko | OpenClaw |
|---|---:|---:|
| First watch read | 27.432s | 58.560s |
| Maximum inter-read gap | 71.359s | 67.557s |
| Atlas eligible reads | 80.253s, 151.612s | 124.175s |
| Cedar eligible reads | 151.612s, 204.298s | 174.360s |
| Dogwood eligible reads | 204.298s | None |
| Maximum Dogwood deadline slack | 35.702s | None |
| Required obligations observed in time | 3/3 | 2/3 |

OpenClaw had no observation within Dogwood's 180–240-second window. The prior
failure therefore includes a coverage gap, while Peko's status inconsistency
occurred despite timely observations and deliveries. Coverage does not fully
separate scheduling, transport/model latency, or subsequent model decisions.

## Live validation protocol

Run one fresh sample per harness sequentially, with `mimo-v2.6-flash`, seed 1,
300-second watch, 60-second cadence, unchanged deadlines, $0.10 PAYG reference
ceiling, `max_tokens=4096`, thinking disabled, no temperature or fallback,
60-request/30k-output admission backstops, and prompt profiling. No rescues,
extra timer calls, readiness notifications or controller continuations occur
inside the watch. Native process restart remains at 35 seconds.

The previous cleanup repair is enabled: after the probe, close relay admission,
wait boundedly for forwarded handlers, stop native processes, then refresh
final observed accounting. A successful drain alone cannot establish complete
provider usage or native reconciliation. Missing final counters keep full-run
cost unknown and the gate failed. PAYG prices are not actual Token Plan credit
deductions.

## Initial version-3 diagnostic: restart interrupted supervision

Local report `20261006T094801358835Z-responsibility-peko` uses benchmark runner
sources committed as `023a230` and the previously merged runtime binaries.
The complete 300-second watch failed: 0/3 completed/on-time obligations, three
missed deadlines, no forbidden/repeated/idle-window/native messaging actions,
no rescues or controller continuations, and a verified process replacement.
The sole watch read arrived at 25.072 seconds; the maximum unobserved gap was
275.069 seconds. No positive obligation received a timely eligible observation.
Overall wall time was 546.430 seconds.

The scheduled run began before the planned restart, which interrupted provider
call 24. Its Send history row remained `running` with no finish time. After
restart every due tick logged that the job already had a run in flight and
skipped it. Source inspection confirmed the periodic reconciler leaves rows
without an async task id untouched; Send turns have no such id. This exposes
a runtime recovery defect, not evidence that the new state protocol succeeded
or failed at updating delivered statuses: no deliveries occurred.

The owner probe posted the same complete memory facts twice. Each individual
payload truthfully reported both releases pending, Birch cancelled and Dogwood
blocked, but the exact-once memory protocol rejects duplicate probes. The
official score remains 0/16 with one protocol error; this is not proof that
the requirements were forgotten. No duplicate is removed or credited.

Of 29 forwarded requests, 28 completed. The completed subset accounts for
124,630 uncached input, 613,056 cache-read and 6,550 output tokens, matching
native counters; its PAYG reference amount is $0.02099876. Call 24 has
`BrokenPipeError`, no final completion and no observed usage counters. Full-run
consumption and cost remain unknown. The post-probe relay drain completed,
but correctly did not turn the earlier interrupted call into complete usage.
Both owned daemon epochs were stopped; transcripts remain local and ignored.

## Runtime restart repair

[Runtime PR #423](https://github.com/ConekoAI/peko-runtime/pull/423) repairs
first-open recovery in the daemon cron engine. An abandoned running Send is
recorded as failed, with an explicit warning that its outcome may be partial.
This releases the in-flight guard so the authored cadence can resume. Recovery
does not repeat the interrupted action, certify its side effects, or change the
job's enabled flag, next due time or run count. Completed history and SpawnTool
async-task recovery remain intact.

Recovery runs once per physical schedule path in each daemon lifetime. This
also protects a current live Send when the same principal is looked up through
its generated id and DID. Two regression tests verify persisted recovery,
history/disabled-job preservation, alias safety and subsequent firing. Local
validation passed formatting, clippy with warnings denied, both boundary gates,
and **2,749 library tests with three ignored**. The tested/built runtime source
is `609d7e8570f7ce5132f50abf9e1c0592ef4df3a2`. CI passed the Linux unit and
both lint gates; Windows and integration tiers were path-gated/skipped. PR #423
was squash-merged as `fe2074b0`; its source tree is identical to the tested head.
The fresh live Peko run uses the binaries built from that tested head, not a
post-merge rebuild (CLI SHA-256
`a707dc5a908b6f45e019731090423274d8744b547132d05e53333e33a1e1e2bd`,
daemon `2a82921e24f03e33adde9ffff6f7a21e8fb56aa3c505b792f68d12deaab46fa0`).

The failed attempt remains diagnostic history. The corrected Peko run and one
OpenClaw sample retain version 3 and the original restart timing. Further
seeds, longer watches and context optimization remain deferred during this
check.

## Version-3 OpenClaw sample

Local report `20261006T100554285874Z-responsibility-openclaw` passed the full
gate: 3/3 obligations completed on time, memory 16/16, verified restart, no
forbidden/repeated/idle-window/native messaging actions, no interventions and
no controller continuations. All 37 forwarded requests completed and matched
native counters. The post-probe drain completed; full PAYG reference cost was
$0.02449479 (793,017 inclusive input, of which 653,888 were cache reads, and
11,378 output tokens). Wall time was 440.067 seconds.

Its reads were 59.505, 119.276, 180.202 and 238.187 seconds. Atlas was delivered
at 122.354 seconds, Cedar at 183.909 seconds, and Dogwood input was requested
at 200.440 seconds. All three obligations had a timely observation. The first
eligible Dogwood read had 59.798 seconds of slack; unlike the previous sample,
this read fell just inside the 180-second threshold. One passing sample does
not establish scheduling reliability or a causal effect of the new prompt.

## Corrected Peko sample and paired result

Local report `20261006T101756069175Z-responsibility-peko` completed with the
merged restart repair. The runner source manifest is identical to OpenClaw's;
both use benchmark source commit `023a2302a8878516c111d66ad6019ccee740e7fe`.
Neither grader nor task deadlines were changed. The pair is one sample per
harness under contract 3, following the retained initial Peko diagnostic.

| Strict metric | Peko | OpenClaw |
|---|---:|---:|
| Full gate | **Fail** | **Pass** |
| Completed obligations | 2/3 | 3/3 |
| On-time obligations | 1/3 | 3/3 |
| Missed deadlines | 2 | 0 |
| Memory facts | 16/16 | 16/16 |
| Forbidden actions | 1 | 0 |
| Repeated actions | 0 | 0 |
| Idle-window actions | 2 | 0 |
| Remained quiet | No | Yes |
| Native outbound attempts | 0 | 0 |
| Human interventions / controller continuations | 0 / 0 | 0 / 0 |
| Process restart verified | Yes | Yes |
| Timely dependency observations | 3/3 | 3/3 |
| Maximum inter-read gap | 91.222s | 60.926s |
| Complete / native-matched provider calls | 50 / 50 | 37 / 37 |
| PAYG reference cost | $0.03323206 | $0.02449479 |
| Wall time | 563.639s | 440.067s |

Peko's configured schedule was genuinely `every_ms=60000`. After restart,
its reads arrived at 58.312, 147.419 and 238.641 seconds. Atlas was delivered
at 152.615 seconds, before its 160-second deadline. Cedar was delivered at
244.861 seconds and Dogwood input requested at 244.917 seconds, after their
240-second deadline and inside the idle window. The grader counts the late
Cedar delivery as completed but not on time; late Dogwood escalation is a
forbidden action and does not fulfill that obligation. Memory correctly
reports actual deliveries and blocked/cancelled state; 16/16 memory is not
proof that those actions met deadlines.

The native Send starting at 10:23:31.825 UTC lasted 69.432 seconds. Its first
provider call took 31.698 seconds before the GET; four further calls completed
the action and durable state maintenance. The daemon skipped due fires while
this turn was running, then advanced to the next future scheduled boundary.
The subsequent turn's eligible GET had only 1.359 seconds of slack, followed
by a 6.100-second provider call before posting. Native output incorrectly
claimed these actions were inside their windows; the simulator timestamps,
not the model's narrative or stored observation time, determine the grade.

This is a demonstrated latency/overrun path, not evidence that the schedule
was configured to 90 seconds. Source already anchors interval jobs to scheduled
boundaries and coalesces missed ticks; this sample does not justify parallel
turns or immediate replay of side effects. The fresh restart landed between
Send turns, so post-restart supervision is verified, while recovery of an
actually interrupted Send is established by the earlier failure and the two
new regression tests, not by an interrupted call in this successful-accounting
sample.

Both post-probe drains completed. All forwarded requests settled with final
usage and matched native counters, with no rejected admissions or controller
errors. No daemon epochs owned by either run remain alive. This live pair
verifies the cleanup repair; the earlier interrupted-call diagnostic still
retains unknown full-run cost. Native traces and model output remain ignored
local evidence.

### Accounting by request-start phase

Amounts are PAYG reference dollars, not subscription credit charges. A request
crossing a boundary stays assigned to its start phase; watch-idle spend includes
late action/state-maintenance work and is not a pure measure of doing nothing.

| Phase | Peko calls | Peko reference $ | OpenClaw calls | OpenClaw reference $ |
|---|---:|---:|---:|---:|
| setup | 6 | 0.00245913 | 4 | 0.00184062 |
| conversation | 20 | 0.01509089 | 11 | 0.00470616 |
| watch_active | 7 | 0.00472017 | 13 | 0.01088082 |
| watch_idle | 7 | 0.00553329 | 4 | 0.00310694 |
| probe | 10 | 0.00542858 | 5 | 0.00396025 |

Peko totals: 1,838,024 inclusive input (177,032 uncached, 1,660,992 cache-read)
and 13,560 output tokens. OpenClaw totals: 793,017 inclusive input (139,129
uncached, 653,888 cache-read) and 11,378 output tokens. No cache-creation tokens
were reported. The full pair costs $0.05772684 by the reference tariff; adding
the initial failed Peko attempt yields a known completed subset of $0.07872560,
with total across all attempts still unknown because that attempt interrupted
one call.

### Interpretation and next stabilization target

The shared state protocol produced correct current-state probes for both
samples. This supports continuing investigation; it does not prove a robust
runtime memory primitive or identify the prompt's causal effect. Restart
recovery has a concrete runtime fix and tests. Observation coverage now exposes
an additional distinction: being able to see a dependency just before a deadline
does not mean there is enough time to act.

The immediate target is a shorter, deadline-aware supervision path: inspect
before optional bookkeeping, reduce model round trips after delivery, and
validate action time rather than treating a GET timestamp as a delivery time.
Profile data helps locate overhead: Peko's active-watch tool catalog averaged
62,209 JSON bytes and message history 120,001 bytes, versus 8,774 and 41,150
for OpenClaw. These are JSON bytes, not tokenizer counts or a demonstrated
cause of the 31.698-second provider latency. Peko has zero duplicate persisted
session-context messages; the earlier renderer defect did not recur. Provider
cache reads were substantial for both, and do not remove model latency.

Do not begin a multi-seed or multi-day comparison yet. Peko still fails the
strict deadline/quietness gate under this unchanged task. Preserve these
results, isolate supervision latency in a bounded follow-up, and rerun the same
pair only after a concrete improvement. This iteration provides no evidence
of Peko outperforming OpenClaw or of an architectural advantage.

## Interpretation correction: the intended topology was constrained away

The owner clarified that trunk keepalive is organizational supervision, while
periodic task attention belongs in separately scheduled task sessions. The
version-3 benchmark explicitly replaced default keepalive with a task-monitor
Send, discouraged delegation, and prohibited delegated monitors. Its observed
overrun is valid for this flattened configuration, but does not establish an
architectural defect in Peko's intended separation. The
[directed topology pilot](RESPONSIBILITY_TOPOLOGY_MIMO_2026-10-06.md) tests that
separation before proposing scheduler redesign. The runtime restart defect and
its regression tests remain independent of this interpretation correction.
