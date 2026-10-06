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
at `1e84d66a8af8219d4242837317aa620e166d1334`.

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

Fresh live results will be recorded here when both runs finish. Further seeds,
longer watches and context optimization remain deferred during this check.
