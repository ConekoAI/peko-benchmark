# Directed supervisor/task separation pilot — 2026-10-06

The previous pilot replaced Peko's default keepalive with a release-monitor Send
job in the trunk, discouraged delegation at genesis, and prohibited delegated
monitors in every task prompt. It therefore measured a flattened configuration,
not the intended supervisor/task-worker division. Its failures remain valid
for that configuration; they do not establish failure of the intended design.

## Protocol

Contract 4 introduced `--topology separated` while preserving flattened contract 3.
Contract 5 repairs its setup instructions after the retained failures below.
Keep the same MiMo v2.6 Flash model, seed 1, 300-second watch, 35-second restart,
60-second task cadence, action API, obligations, deadline windows, grader and
$0.10 PAYG reference budget per harness. Wire admission remains 60 requests and
30k output tokens, max output 4096, thinking disabled and no fallback.

Peko genesis receives a directed organization task: create organizational
keepalive every 120 seconds before removing the old 10-minute default; create a focused
release-watch role and persistent child; register a separate native 60-second
Cron job that invokes Agent directly in that child. The worker checks dependency
state, acts and maintains task receipts/current state. The trunk tends general
memory/skills/session organization and repairs worker organization when needed.
No trunk LLM call dispatches each worker tick. Owner/review chats share canonical
requirements and cancellation/revision decisions with the worker.

OpenClaw receives the same division and permission to create workers/schedules:
its configured organizational heartbeat is 120 seconds, and its model registers
a native 60-second agent-turn automation in a persistent custom release-watch
session with no delivery. Native built-in memory/skill schedules are retained
and recorded. Any calls they make also count against the shared run budget.

The controller does not write roles, commitment answers or native task jobs.
Formation is directed by explicit setup instructions, not autonomous discovery
of the best topology. Read-only snapshots verify registration after setup, before the watch,
after restart and after the watch. Retained transcripts identify actual worker
and supervisor activity, including operational tool intents outside the worker.
The extended full gate requires verified registration and both execution lanes;
original obligation/quietness/memory grades are unchanged. Command-intent
attribution is diagnostic evidence, not proof of every HTTP caller identity.

This intervention changes topology and role prompts together. A comparison to
the retained flattened pair is exploratory, sequential and unpaired in model
latency, not a causal architecture experiment. Do not discard failures or rerun
until passing. Run one sample per harness, retain full costs, then decide the
next stabilization step. Deadline enforcement and latency risks still apply to
the task worker after isolation.

## Validation

All 60 offline tests pass, including rejection of a renamed trunk job, incorrect
worker routing, extra custom schedules, loss of the independent supervisor,
and operational tool intents in the supervisor. Live validation follows below.
Raw transcripts/native schedule snapshots remain local and gitignored.

A first preflight (`20261006T114903952151Z-responsibility-peko`) stopped because
local Peko binaries had been removed. It forwarded no model requests. Source
inspection corrected a setup instruction before live model execution: CronUpdate
only toggles enabled/completion subscription, so cadence/message replacement
must use CronCreate followed by CronDelete. This is not a model failure.

## Initial contract-4 formation attempts (retained)

Both runners used source `302616fd41d68853c075f4ebf6e3926eb957782e`.
Neither reached an unattended watch; there is no valid task-performance pair.
Strict grades fail, but their zero completions/memory are censored setup results,
not evidence of three deadlines being observed and missed or facts forgotten.

Peko report `20261006T115240268235Z-responsibility-peko` failed the native
300-second genesis wait, wall time 318.573s. It authored a focused role and both
correct job kinds/cadences. Initialization searched many speculative note paths
because the shared operational files had not yet been created. A task fire
collided with initialization and failed with an active-run refusal; a later
fire was rejected after measurement closed. The worker's initialization finally
completed, but trunk genesis was still finishing setup when the wait expired.
All 17 forwarded calls completed ($0.00762414 PAYG reference), with one rejected
late admission. The quota snapshot counts all 17; persisted assistant usage
contains only 16, so native reconciliation fails. The successful relay drain
does not erase that mismatch. No watch, restart or probe occurred.

OpenClaw report `20261006T115939691840Z-responsibility-openclaw` created the
custom-session task automation and 120s organizational heartbeat, completed
onboarding and the two owner updates, then hit the 90-second CLI/provider limit
in the review conversation (wall 292.193s). Its supervisor heartbeats were
skipped while requests were in flight. There were 21 forwarded calls, of which
20 completed ($0.01124707 reference subset); call 21 has no final usage and
full-run consumption/cost remain unknown. Matching native observed counters
cannot certify completeness. No watch, restart or memory probe occurred.

These traces identify setup problems before they can test the proposed
execution split. They are retained, not rerun-until-passing samples.

## Contract-5 setup repair and bounded retest protocol

Specify the same non-oracle canonical file paths to both harnesses:
`kb/responsibility/commitments.md` and `kb/responsibility/receipts.md`. Their
models create empty files before any worker starts; owner chat still supplies
all commitment facts. Peko initializes the child by reading only that empty
file and acknowledging the assignment, then registers the recurring worker
job after initialization completes. No setup world reads, discovery scans or
role/journal rewrites are needed in that child turn. This addresses the observed
ordering collision and speculative lookup cost without controller-written jobs.

Separated OpenClaw conversations now use a 180-second CLI allowance, matching
Peko's command allowance; worker and supervisor turns remain limited to 90s.
Peko's 300-second genesis wait, overall 900-second scenario timeout, 300-second
watch, deadline windows, 60/120-second cadences, model and $0.10/reference and
60-request admission limits remain unchanged. A new registration snapshot runs
immediately after setup, so a later conversation failure cannot conceal whether
the topology formed. Run one fresh sample per harness after this concrete repair.
Contract 4 and 5 are different setup/task-input interventions, not reliability
repetitions of an unchanged protocol.

## Contract-5 results

Both retests used benchmark source `5b33f7680f88ff3bb01f7fd826b0a3dd045c816b`.
Peko used runtime source `fe2074b0a51a7e31096cb02d1512c24abf6d20a5`
(merged restart repair), version 0.1.0. Its rebuilt CLI SHA-256 is
`1df3735028765d5dbcdeac1e1149a9438d3cc2ff2a36302f67960aa8305f11c3`,
and daemon SHA-256 is
`1894517171ed8e4ae3aea0b59f468928d84ecc2815b97a9416b176b56218c89c`.
OpenClaw reported `OpenClaw 2026.9.8 (fc23bc8)` in both contracts.

| Contract | Harness | Last observed stage | Unattended watch |
|---|---|---|---|
| 4 | Peko | Genesis exceeded 300s; initialization overlapped a task fire | Not started |
| 4 | OpenClaw | Registered worker; review conversation exceeded 90s | Not started |
| 5 | Peko | Registration verified; first owner conversation exceeded 180s | Not started |
| 5 | OpenClaw | Onboarding exceeded 180s; custom task job absent | Not started |

Peko report `20261006T120921466884Z-responsibility-peko` completed genesis
and passed the post-setup registration check: an independent 120s organizational
Send job, a 60s Agent job routed to `/release-watch` with the focused role,
and an initialized persistent child of the trunk. This establishes that the
runtime can form the requested arrangement under directed setup instructions.
It does not establish the worker/supervisor execution gate during the watch.

The first owner update then exceeded the 180-second command allowance
(whole-run wall time 480.252s). The owner session wrote commitment state, but
also resumed the worker twice and polled async output/cron history instead of
finishing its acknowledgement. The worker read the inactive pre-watch world;
the unattended phase never started. Manual driving and waiting during the
handoff is a concrete remaining behavior problem. The trace does not isolate
whether shared principal instructions, onboarding instructions or model choices
caused it. All 33 forwarded calls completed, with one rejected late admission;
relay and persisted native usage reconcile. The PAYG reference cost is
$0.022093428 (121,765 uncached input, 812,160 cached input, 9,901 output tokens).

OpenClaw report `20261006T121904260239Z-responsibility-openclaw` exceeded the
180-second onboarding allowance (whole-run wall time 200.678s). It created the
shared task files and worker instructions, but BOOTSTRAP remained present and
the final schedule snapshot contained no custom task automation. No owner
conversation or registration check was reached. Five calls were forwarded;
four completed, costing $0.0024743264 in PAYG reference terms. The fifth has
partial input usage and no final usage, so full-run consumption and cost are
unknown and native reconciliation fails. Contract metadata is assigned after
onboarding, so this failed result lacks that field; its pinned source manifest
and scenario identify the contract-5 intervention. Both retests drained
telemetry before closing; a successful drain cannot supply missing final usage.

Across the four live attempts, 76 requests were forwarded and 74 completed.
The completed-call reference subtotal is $0.0434389592; the full total is
unknown because two OpenClaw calls lack final usage. These figures do not
estimate actual MiMo Token Plan credit charges. No attempt reached a watch,
restart or memory probe. Reported strict failures are retained, but obligation,
deadline, memory, idle-spend and quietness outcomes are unavailable for this
experiment. Zero actions before a watch are not proof of correct quietness.

## Interpretation and next experiment

The user's proposed separation is implementable with existing native runtime
primitives. Peko's successful directed formation is supporting evidence for
that narrower claim. These runs neither confirm its performance advantage nor
refute the architecture. OpenClaw's earlier flattened success also cannot be
treated as success under this separated protocol.

The next stabilization target is lifecycle prompting and handoff, before any
larger trial. Scope procedural creation instructions explicitly to genesis;
keep ongoing principal purpose separate from setup recipes. Once the worker
is registered, owner/review conversations should update shared facts and
acknowledge, without manually resuming the worker or waiting for scheduled
execution. Treat this as a testable prompt hypothesis, not a proven diagnosis.

Separate two subsequent experiments: a prepared-topology execution test and
a model-created organization test. If a controller installs topology fixtures
for the former, label that intervention explicitly and score formation only in
the latter. This would let the unattended watch evaluate task isolation without
censoring every metric on onboarding. Retain the present failures; do not
increase deadlines, budgets or retries silently to obtain a passing pair.
