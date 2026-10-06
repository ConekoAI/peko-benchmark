# Responsibility interface parity — 2026-10-06

The first unattended retest of merged runtime PR #422 failed: 1/3 obligations
completed and 14/16 memory facts correct. The principal-memory path repair
worked, but the scheduled supervisor invented an unsupported action kind.
Investigation found unequal availability of the simulator's static API contract
across native session arrangements. This report preserves that failure and
records a benchmark interface correction, not a relaxed grader.

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
owner/review prompts and **both** native supervision prompts. It includes the
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

Context-growth optimization and additional seeds remain deferred pending
behavioral stabilization. A single repaired pair would establish a smoke-test
result, not an architectural advantage or a reliability estimate.
