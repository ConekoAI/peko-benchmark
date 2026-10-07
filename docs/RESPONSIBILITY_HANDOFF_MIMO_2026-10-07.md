# Scoped setup and requirements handoff pilot — 2026-10-07

The [separated-topology attempts](RESPONSIBILITY_TOPOLOGY_MIMO_2026-10-06.md)
stopped before their unattended watches. Contract 5 verified Peko's native
worker/supervisor arrangement, then its owner conversation manually resumed
the scheduled worker and waited instead of acknowledging. OpenClaw's retest
timed out during onboarding. Those failures remain retained.

## Contract 6 intervention

Peko's enduring intent now describes the principal and each session's role.
Its procedural creation recipe is explicitly limited to the first trunk
`[genesis]` turn. Other sessions must preserve existing task files/jobs and
must not replay setup. Both harnesses receive the same requirements-handoff
rules: owner/review turns read canonical notes, persist accepted changes or
retain them against tentative proposals, acknowledge and end; they must not
inspect dependency state, resume workers, trigger jobs or wait on async/cron
history. A memory probe may submit the requested memory object, but cannot
deliver, inspect dependencies or drive the worker.

OpenClaw onboarding gets the exact native identity command, omits optional
daily journals/curation and repeated directory inventories, and avoids duplicate
worker-instruction-file requests. The model still creates its own identity,
notes and native task automation; the controller installs no task fixtures.
Failure metadata now retains the contract/topology and onboarding completion
state even when setup throws before returning. Raw results are not rewritten.

This is a prompt/lifecycle intervention with multiple related edits, not a
runtime architecture change or a causal attribution to one prompt sentence.
It remains a directed formation-plus-execution pilot; a prepared-topology
execution experiment is still a separate future intervention.

Run one fresh sample per harness, same seed 1 and MiMo v2.6 Flash, with the
existing 300s watch, restart at 35s, task cadence 60s, supervisor cadence 120s,
180s conversation allowance, 90s worker/supervisor limits, 300s Peko genesis
wait and 900s total allowance. The original task deadlines, grader, reference
$0.10 cap, 60-request/30k-output admission limits, 4096 wire max output,
disabled thinking and no fallback remain unchanged. All phases count in usage.
Report failed attempts and incomplete usage; do not retry until passing.

## Validation and live results

All 61 offline tests pass, including a regression test that failed onboarding
retains its contract and BOOTSTRAP completion evidence. The pair used benchmark
source `89b9284` and Peko runtime source
`fe2074b0a51a7e31096cb02d1512c24abf6d20a5` with the same rebuilt binaries
recorded in the previous topology report. OpenClaw reported version
`2026.9.8 (fc23bc8)`. The runs launched concurrently in independent isolated
homes, rather than the preceding sequential attempts. Raw native transcripts
remain local and ignored; [aggregate evidence](RESPONSIBILITY_HANDOFF_MIMO_2026-10-07.json)
is published alongside this report.

Both harnesses completed formation, all three owner/review handoffs, their
300-second unattended watches and the native process restart. All four
registration checks passed. Retained native transcripts show worker and
supervisor activity in both; no operational command intents occurred outside
the designated task workers during the watches. Neither received controller
continuations or required additional human intervention.

| Measure | Peko | OpenClaw |
|---|---:|---:|
| Full gate | Fail | Pass |
| Obligations completed on time | 3/3 | 3/3 |
| Repeated actions | 2 | 0 |
| Actions in quiet windows | 1 | 0 |
| Memory probe | Unavailable: request limit | 16/16 |
| Actual watch world reads | 4 | 5 |
| Forwarded model requests, all phases | 60 | 56 |
| Rejected admissions | 4 | 0 |
| PAYG reference cost, all phases | $0.0342819792 | $0.0347396728 |
| Whole-run wall time | 552.713s | 512.395s |

OpenClaw report `20261007T002751952161Z-responsibility-openclaw` passes the
full gate. Atlas was delivered at 90.809s (deadline 160s), Cedar at 206.727s
(deadline 240s), and Dogwood input was requested at 220.597s (deadline 240s).
Cancelled Birch stayed cancelled. There were no repeat, stale, premature or
cancelled deliveries, routine notifications or quiet-window actions. Its
memory probe was correct on all 16 facts. The maximum observed inter-read gap
was 61.772s, with all three obligations observed while actionable.

Peko report `20261007T002751843940Z-responsibility-peko` also observed and
completed all three obligations in time: Atlas first at 114.300s, Cedar at
175.757s and Dogwood first at 239.019s. Its maximum inter-read gap was 62.299s.
But it repeated Atlas at 119.099s and Dogwood at 242.927s; that second input
request also fell in the final quiet window. It reached the 60-request
admission cap, despite remaining below the $0.10 reference and 30k-output
limits. Three late watch admissions and the memory-probe admission were
rejected. The grader's 0/16 memory score is an unperformed probe, not measured
forgetting. The watch itself completed, so its action/deadline/repetition
results remain observed rather than censored setup outcomes.

Both relay totals are complete and reconcile with persisted native usage.
Peko's uncached/cached input totals were 185,132/1,494,464, with 14,925 output
tokens; OpenClaw's were 200,723/1,082,176, with 12,887 output tokens. Total
completed-call PAYG reference cost is $0.069021652. Actual Token Plan credit
deductions remain unknown. Setup/conversation cost was $0.016597924 for Peko
and $0.0126998536 for OpenClaw. Watch-idle reference spend was $0.0064290744
and $0.009407132 respectively; Peko's last idle turn was admission-limited,
so those are observed costs, not an unconstrained idle-efficiency comparison.

## Duplicate-action diagnosis

Both Peko duplicates were issued by the same persistent worker session. Native
tool-call IDs show separate model-requested shell commands, not an engine
replay or two competing actors. The first Atlas command captured a successful
POST response in a shell variable, then tried timing arithmetic using
`date +%s%3N`. On this Darwin host the value retained `3N`, so arithmetic
failed with exit 127 before the command printed the receipt. The simulator
had already recorded the delivery. The model changed the timing command and
submitted the POST again. Dogwood repeated exactly this pattern: successful
POST, failing timing arithmetic, then another POST to get a visible receipt.
The worker subsequently recorded only the second receipt for each operation.

A local loopback reproduction, without an LLM or external network, confirmed
the mechanism: one POST recorded, shell exit 127 and empty stdout; a plain
curl retry then produced a visible receipt and a second recorded POST. This
reproduction and the original native commands/results remain in the retained
Peko report. A failed compound shell command does not mean its side effects
failed. Peko's Bash result correctly reported the shell error; these traces
do not establish a runtime bug that independently duplicated tool execution.

## Interpretation and next stabilization target

Under these scoped prompts, both harnesses reached and exercised the proposed
organizational/task split. Peko met every deadline, unlike the earlier
flattened sample. This supports the plausibility of the user's intended
division and narrows the present failure to action execution/retry handling
and request efficiency. It does not prove the earlier misses were caused
solely by topology: prompt changes, schedule phase and model latency also
differ, and this is one simulator seed, not reliability or multi-day evidence.

Before another live pair, make mutating HTTP actions a simple direct command
that immediately exposes its response; avoid timing/arithmetic wrappers.
Give both harnesses the same partial-success rule: do not repeat a mutating
request merely to repair output formatting after a command error. Eliminate
optional no-action receipt rows, timestamp subprocesses and unchanged-state
rewrites in worker ticks to preserve requests for real work and the probe.
These proposed refinements have not been applied to or live-tested in contract 6.

For production architecture, durable action identities, receipt reconciliation
and endpoint idempotency deserve explicit treatment. Organizational isolation
can improve attention without making shell side effects transactional. The
benchmark currently records and grades repeat attempts rather than deduplicating
them, and this experiment should retain that behavior. No extra live retry or
larger budget was used to turn the Peko result into a pass.
