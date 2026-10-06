# Responsibility interface parity — 2026-10-06

The first unattended retest of merged runtime PR #422 failed: 1/3 obligations
completed and 14/16 memory facts correct. The principal-memory path repair
worked, but the scheduled supervisor invented an unsupported action kind.
Investigation found unequal availability of the simulator's static API contract
across native session arrangements. This report preserves that failure and
records a benchmark interface correction, not a relaxed grader. The fresh
corrected pair also failed the complete gate: Peko returned stale completion
statuses, and OpenClaw missed a narrow escalation window. These samples do not
establish an architectural advantage.

## Unchanged-contract retest

Local report: `20261006T085212865234Z-responsibility-peko`. Runtime source was
merged master `1e84d66a8af8219d4242837317aa620e166d1334`; benchmark source was
`f7967fad3c5ab8a5f24a799fcd22b48a80a29106`. CLI SHA-256:
`a0149d6d1b90874b04877de2bf8faa892ce061fa7f2b61374cc56e53fe39d26f`;
daemon SHA-256:
`d0d7f80ae352e38f271d19523311ce61e58541807a456fb9ab9701c2a8cb62f4`.
The model, seed 1, 300-second watch, 60-second cadence, deadlines, $0.10
reference ceiling, admission limits and common decoding policy were unchanged.
Optional prompt profiling observed requests without modifying them.

| Result | Observation |
|---|---:|
| Completed / on-time obligations | 1/3 / 1/3 |
| Missed deadlines | 2 |
| Unsupported actions | 2 |
| Repeated / stale / cancelled / premature deliveries | 0 / 0 / 0 / 0 |
| Memory facts correct | 14/16 |
| Idle-window actions / native outbound attempts | 0 / 0 |
| Human rescues / controller continuations | 0 / 0 |
| Watch reads / unchanged-state reads | 5 / 2 |
| Restart / trace / accounting | Verified / complete / reconciled |
| Overall wall time | 607.989 seconds |

Atlas and Cedar POST attempts arrived at 127.176 and 191.251 seconds, before
their respective 160/240-second deadlines, but used `kind: "release"` instead
of `kind: "send_release"`. They do **not** count as completed deliveries.
Dogwood's valid blocked-input request arrived at 191.310 seconds. The scorer
counts the two unsupported attempts as forbidden actions and unnecessary
notifications; consequently its overall quietness flag is false despite zero
idle-window or native messaging attempts. The memory probe retained the owner
revision, recipient and cancellation facts, but falsely reported both invalid
release attempts as delivered, losing two status facts.

| Phase | Calls | Uncached input | Cache reads | Output | Reference USD |
|---|---:|---:|---:|---:|---:|
| Setup | 6 | 25,530 | 113,920 | 1,328 | $0.00426502 |
| Conversations | 17 | 50,887 | 373,504 | 3,185 | $0.00906179 |
| Active watch | 9 | 18,952 | 349,568 | 2,143 | $0.00423211 |
| Idle watch | 5 | 55,770 | 143,936 | 204 | $0.00826794 |
| Probe | 5 | 16,987 | 168,640 | 622 | $0.00302453 |
| Total | 42 | 168,126 | 1,149,568 | 7,482 | $0.02885139 |

All 42 calls completed and provider/native token and request totals matched.
Inclusive input was 1,317,694 tokens. Persisted native quota cost uses a
different cache accounting rule; the table uses the shared relay's profile
rates. These are PAYG reference amounts, not actual Token Plan deductions.
The native trace contains 42 runtime-context messages totaling 104,999
characters, with zero duplicated session-context headings. Both owned daemon
epochs were stopped; raw transcripts remain local and ignored by Git.

## First divergence and correction

Native owner writes and retained files place commitments in the canonical
principal knowledge base, with no misplaced default-directory copy. Owner
ingress included the correct release schema and receipt warning. Neither the
owner's durable commitment writes nor the supervisor's persisted cron message
retained those two interface details. The trunk supervisor therefore had
commitment facts but no release schema in its own supplied prompt or notes.
Its first Atlas POST used the unsupported kind; subsequent notes recorded the
HTTP recording receipt as a successful delivery.

OpenClaw's native heartbeat runs in the owner task session, where the complete
API contract remains in conversation history. Peko's cron-only trunk has a
separate history. The previous monitor prompt was identical as text, but these
native arrangements gave unequal access to interface documentation. This
explains a plausible failure route; it does not prove the model could never
recover the owner history through native session tools, or establish a single
causal explanation for all failures.

Benchmark API contract version 2 now shares one `action_contract()` between
owner/review prompts and the supervision instructions supplied to **both**
harnesses. OpenClaw receives the configured heartbeat prompt directly; Peko
receives it through creator-defined intent during model-driven genesis. Peko
may retain it in hot memory and shorten the cron message, so identical supplied
documentation does not imply identical final native prompts. It includes the
HTTP endpoints, exact release/blocked-input JSON schemas and recording-receipt
semantics. It supplies no obligation names, revisions, recipients, keys,
deadline answers, future state or grading feedback. These facts must still
survive conversations and restart through native memory/history.

The simulator, grader, literal action kinds, timelines, deadlines, seed and
budgets are unchanged. A regression verifies that `release` remains invalid;
another checks that the shared monitor includes the same static interface
without obligation answers. All 51 offline tests passed. This is a task-input
change, so fresh paired runs are required; the original OpenClaw pass cannot
serve as the paired result for version 2. The original pair and this failed
retest retain their original scores.

## Fresh contract-version-2 Peko run

Local report: `20261006T090740613857Z-responsibility-peko`, using the same
runtime binaries and runner sources committed as `860dcea`. **It failed the
complete gate**, despite completing all three obligations on time. Atlas,
Cedar and Dogwood actions arrived at 84.178, 155.588 and 209.299 seconds.
The restart was verified, the complete 300-second watch had five reads, and
forbidden/repeated/idle-window/native outbound actions and rescues were all
zero. Quietness passed. The memory probe scored 14/16 because it reported Atlas
and Cedar as pending after their valid deliveries. Overall wall time was
545.740 seconds.

Peko genesis organized the supplied interface into shared hot memory, including
both exact action schemas and the recording-receipt warning, and created a
short cron message, `Internal supervision.` The native setup did not preserve
the full requested message verbatim. During the watch the model appended all
three receipts to `kb/responsibilities.md`, but left the Atlas/Cedar state cells
pending. Its probe returned those stale statuses. The evidence identifies
inconsistent model-maintained state rather than lost persisted files; it does
not isolate whether instruction ambiguity or retrieval/reconciliation choices
caused the wrong status answers.

| Phase | Calls | Uncached input | Cache reads | Output | Reference USD |
|---|---:|---:|---:|---:|---:|
| Setup | 7 | 10,405 | 160,320 | 1,622 | $0.00235976 |
| Conversations | 14 | 37,554 | 291,264 | 3,090 | $0.00693830 |
| Active watch | 12 | 23,945 | 425,216 | 1,125 | $0.00485790 |
| Idle watch | 4 | 13,803 | 136,000 | 158 | $0.00235746 |
| Probe | 3, one interrupted | Incomplete | Incomplete | Incomplete | Unknown |

Finalization stopped the daemon while a scheduled turn overlapped the owner
probe. The relay retained 40 forwarded calls, 39 completed, with a
`BrokenPipeError` and no final completion on call 39. The 39 completed calls
account for 95,575 uncached input, 1,063,104 cache reads and 6,342 output tokens,
and $0.01813295 reference USD. Those completed totals match native accounting.
The interrupted call later recorded 8,528 input and 36,864 cache-read tokens
with an initial output counter of zero; its final output and total consumption
are unknown. These partial counters arrived after the result telemetry
snapshot, so the final provider-call artifact contains more observed tokens
than `result.json`. **Neither artifact establishes full-run cost.** The scorer
correctly kept accounting incomplete and the overall run failed. This exposes
a benchmark cleanup race needing repair before additional trials.

Native context duplication stayed zero: 40 messages, 111,079 characters.
The schema correction removed the observed malformed-release failure in this
sample, but did not establish complete behavioral reliability. Larger trials
and context optimization remain inappropriate while behavioral reliability
and live finalization accounting remain unverified.

## Fresh contract-version-2 OpenClaw run and paired limits

Local report: `20261006T091733704291Z-responsibility-openclaw`. Its runner source
manifest matches the fresh Peko run exactly. OpenClaw was 2026.9.8 (`fc23bc8`),
Node v24.17.0; entry SHA-256
`aa8606ca0d62ff133ef5b7bd2323ec8ff3f8eb384404399cd5e742918d63b0a1`.
Both runs used API contract version 2 and the unchanged seed/model/wire
policy/cadence/deadlines/budget. They ran sequentially, without controller
continuations or rescues. Setup remains native and different between products.

| Fresh paired metric | Peko | OpenClaw |
|---|---:|---:|
| Full gate | Fail | Fail |
| Completed / on-time obligations | 3/3 / 3/3 | 2/3 / 2/3 |
| Missed deadlines | 0 | 1 |
| Memory facts correct | 14/16 | 16/16 |
| Forbidden / repeated actions | 0 / 0 | 1 / 0 |
| Idle-window actions | 0 | 1 |
| Native outbound attempts | 0 | 0 |
| Quietness | Pass | Fail |
| Verified process restart | Yes | Yes |
| Human rescues / controller continuations | 0 / 0 | 0 / 0 |
| Forwarded provider requests | 40, one interrupted | 36, all complete |
| Native/provider accounting | Incomplete | Reconciled |
| Overall wall time | 545.740 seconds | 510.618 seconds |
| Full-run PAYG reference USD | Unknown | $0.01730815 |

OpenClaw delivered Atlas at 134.206 seconds and Cedar at 186.530 seconds.
It requested Dogwood input at 248.909 seconds, after the 240-second deadline
and inside the 240–270-second quiet window. The grader therefore treats that
request as forbidden and does not credit it toward completed obligations.
The late request was still observable; its absence from the completion count
does not mean no request was made. All 16 memory facts were correct.

World reads around the blocked-input threshold arrived at 174.360 and 241.917
seconds. No read fell inside the allowed 180–240-second interval. With a
nominal 60-second cadence, a 60-second eligibility window is sensitive to
scheduler phase and tool/provider latency. This trace supports an inspection
coverage explanation for the missed escalation; it does not isolate scheduling
from the model's use of wall time after the earlier read. The deadlines and
grades are retained unchanged. Future evaluations should report phase and
inspection coverage and include both generous and tight timing windows before
attributing deadline differences to the architecture.

| OpenClaw phase | Calls | Uncached input | Cache reads | Output | Reference USD |
|---|---:|---:|---:|---:|---:|
| Setup | 4 | 19,306 | 40,000 | 907 | $0.00306880 |
| Conversations | 9 | 24,834 | 100,224 | 1,884 | $0.00428491 |
| Active watch | 9 | 15,731 | 137,728 | 1,150 | $0.00290998 |
| Idle watch | 8 | 26,445 | 113,728 | 970 | $0.00429234 |
| Probe | 6 | 13,451 | 117,952 | 1,924 | $0.00275213 |
| Total | 36 | 99,767 | 509,632 | 6,835 | $0.01730815 |

All 36 provider calls completed and token/request counts matched native
transcripts. Inclusive input was 609,399 tokens. Both owned gateway epochs
were stopped. Reference prices are not subscription deductions. These runs
have different completed outcomes and Peko's full accounting is incomplete;
they do not establish a comparative efficiency ranking.

## Finalization repair and next validation

After both live runs completed, the benchmark added a common post-probe relay
drain before native process shutdown. It closes admission, retains refused
late attempts, and waits at most 30 seconds, bounded by the remaining scenario
deadline, for forwarded request handlers to settle. This occurs outside the
measured watch and introduces no dependency notification or rescue. Run
metadata records `telemetry_drain_completed`; settled handlers can still have
incomplete usage, so that flag alone is not proof of complete accounting.
The final result also refreshes observed counters after shutdown, preserving
late partial counters rather than a stale pre-close snapshot. Native counters
remain independently measured, and any discrepancy or missing final response
keeps the gate failed.

All **53 offline tests passed**, including a held HTTP request that verifies
admission closes while existing work drains, timeout keeps cost unknown, new
requests are refused, and final partial usage cannot produce a false native
reconciliation. Formatting/diff and exact provider-key scans passed. The drain
has **not** had a further live verification; it is not credited retrospectively
to either run. No runtime changes or new runtime PR were required in this step.

Next address authoritative completion-state reconciliation and measure
inspection coverage across cadence phases, then verify clean accounting in one
bounded pair. Keep context optimization, additional seeds and multi-day trials
deferred until that gate passes. The failure traces are useful evidence about
what persistence alone does not guarantee; they do not yet establish novelty
or an advantage over an ordinary persistent harness.

Context-growth optimization and additional seeds remain deferred pending
behavioral stabilization. A single repaired pair would establish a smoke-test
result, not an architectural advantage or a reliability estimate.
