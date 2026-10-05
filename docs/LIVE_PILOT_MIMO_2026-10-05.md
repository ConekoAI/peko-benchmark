# MiMo continuity pilot — 2026-10-05

**One completed scenario passed with `mimo-v2.6-flash`.** This establishes that
the native adapter works and Peko can carry a revised commitment through a
process restart in this short scenario. It does not establish harness superiority,
keepalive usefulness, or a reliable population pass rate.

Runtime source: `643fe98fd943dc038745f4826040ec8b93a28160` (clean checkout),
debug CLI and daemon built together, version 0.1.0. Both binary SHA-256 hashes
are in the result. Model: `mimo-v2.6-flash`, Anthropic API, owner-supplied China
Token Plan endpoint. Context limit: 1,048,576; output cap: 8,192 per call;
provider-default thinking. Fresh principal, default genesis, isolated passphrase
vault; no real release messages sent. Scenario: `changed-commitment`, seed 1.

## Attempts retained

| Report directory under `reports/` | Outcome |
|---|---|
| `20261005T063533905287Z-continuity-peko` | Adapter seed omitted required `name`; failed before model calls. Corrected. |
| `20261005T063642819765Z-continuity-peko` | Default genesis still running at the adapter's 150-second wait limit. Setup failed; no scenario turns scored. Usage capture was incomplete. |
| `20261005T064016514240Z-continuity-peko` | Standard 300-second genesis wait; initialization completed and all seven scenario turns passed. |

Do not describe these attempts as a 100% live-run pass rate. There is one
completed, scored scenario and one model-backed initialization timeout.
The earlier timeout's usage is additional to the totals below and remains unknown.

## Completed scenario

| Step | Result | Wall seconds |
|---|---|---:|
| Accept both conditional commitments | No delivery | 13.426 |
| Unrelated distracting information | No delivery | 7.618 |
| Revise one commitment; cancel the other | No delivery | 7.117 |
| Restart daemon | PID changed; forced termination after SIGINT wait | 14.921 |
| First dependency ready | Exactly the revised revision, recipient and original delivery key | 8.218 |
| Cancelled dependency ready | No delivery | 3.904 |
| Duplicate event | No second delivery | 4.862 |
| No state change | No delivery | 5.256 |

Obligation completion: 1/1. Correct turns: 7/7. Stale, cancelled, premature,
duplicate and other forbidden actions: zero. Protocol errors: zero.
Total adapter wall time: 228.860 seconds, including setup and cleanup.
Genesis execution took 84.334 seconds after the runtime's approximately
60-second scheduling delay. Genesis used 12 of the 22 completed LLM calls.

Default keepalive remained available, but no periodic keepalive execution was
observed in this short run. The controller delivered each dependency event;
this result supports event-driven continuity only.

## Usage reconciliation

The final `quota status` snapshot reported only five requests, 53,349 uncached
input tokens, 428 output tokens, and 91,968 cache-read tokens. Those correspond
to the five calls after the restart, rather than the whole principal lifetime.
Persisted session `message.v2` assistant usage records cover all 22 completed
calls and give:

| Counter | Complete recorded run |
|---|---:|
| Completed LLM calls | 22 |
| Total input including cache | 556,530 |
| Uncached input | 99,762 |
| Cache-read input | 456,768 |
| Cache creation | 0 |
| Output including thinking | 5,324 |

The engine stores cache-inclusive input in session assistant metadata; subtract
the preserved cache fields to recover uncached input. The original quota
snapshot and original result are retained. `usage-reconciliation.json` records
the reconstruction, and the final result/summary use the reconstructed estimate.

Using MiMo's [public pay-as-you-go rates](https://mimo.mi.com/models/en-US/mimo-v2.6-flash)
($0.14/M uncached input, $0.0028/M cache reads, $0.28/M output), the recorded
completed run corresponds to **$0.01673635**. This is a reference estimate,
not the Token Plan deduction, an invoice, or the total across all attempts.
The owner's dashboard is the authority for actual subscription consumption.

The owner subsequently reported **16,859,564 credits consumed out of a
4,100,000,000-credit allowance**, or **0.4112%**. This is the observed pilot
session deduction, including any activity in that dashboard measurement window;
it cannot be attributed solely to the one completed run from the information
available. Keep it separate from per-run token counts and USD reference estimates.

## Findings and next experiments

1. **Continuity worked in this sample.** The revised commitment and cancellation
   survived the process restart, and the duplicate event did not cause another
   delivery. A persisted ordinary harness may do equally well; implement that
   same-model baseline before attributing the outcome to Peko's design.
2. **Initialization is variable and material.** One setup exceeded 150 seconds;
   the completed setup made 12 calls before the seven task turns. Report setup
   success, latency and cost separately when comparing seeding approaches.
3. **Streaming quota persistence needs a runtime regression test and fix.**
   Pre-restart counters disappeared from the live quota meter after forced
   termination. Source inspection shows the streaming provider uses synchronous
   `try_charge_with_cost`, which does not persist; it relies on a later async
   charge that a stream-only workload may never make. The benchmark now
   reconciles usage from persisted sessions rather than trusting a final snapshot.
4. **Shutdown needs investigation.** SIGINT did not make the isolated daemon
   exit within ten seconds, so the adapter used SIGKILL on its owned PID. Record
   this as forced-restart recovery, not graceful shutdown.
5. **Keepalive remains untested.** Add a controller-owned dependency change
   without an event prompt, with an external action ledger and deadline. Then
   compare periodic supervision against event-only continuation.

Offline benchmark validation after the adapter changes: 22 tests passed;
shell profile syntax and diff whitespace checks passed. No runtime source
changes were made for this pilot.

The subsequent [fix verification](LIVE_PILOT_MIMO_FIX_VERIFICATION_2026-10-05.md)
passed the same scenario with complete quota retention and clean SIGINT restart.
