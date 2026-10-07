# Contract 7 after cron tool recovery — 2026-10-07

This is one fresh sample per harness after [runtime PR #424](https://github.com/ConekoAI/peko-runtime/pull/424),
merged as `6f3c70a636357c7753c17bad8aff469c6f2f9d05`. The preceding
[direct-action pair](RESPONSIBILITY_DIRECT_ACTION_MIMO_2026-10-07.md) failed
both harnesses and exposed an abandoned untracked Peko tool-cron row that
suppressed every later worker fire after restart. The fix closes that row as
failed with a partial-outcome warning and permits subsequent scheduled work.
It does not replay or certify the interrupted operation.

## Frozen comparison

Benchmark checkout: `2cccefd0ddeea8b398c651c7b1810d74b727f773`.
All runner-file hashes exactly match the preceding contract-7 pair. Neither
prompts, grader, simulator, formation process nor budget enforcement changed.
Each native harness forms its own supervisor/task-worker organization through
genesis/onboarding; the controller does not install task jobs or commitment
files, resume work during the watch or provide grading feedback.

Both samples use MiMo v2.6 Flash, the Anthropic Token Plan endpoint, simulator
seed 1, separated supervisory topology, 4096 wire max output, thinking disabled,
no fallback, $0.10 historical PAYG reference admission cap, 60 forwarded requests,
30,000 output-token admission limit and 900-second overall allowance. The watch
lasts 300 seconds, restart occurs at 35 seconds, task cadence is 60 seconds and
organizational supervision is 120 seconds. Deadlines, quiet windows, native
turn limits and direct-action/receipt guidance are unchanged. Launches are
concurrent in isolated homes, matching the previous pair; upstream latency and
native scheduling remain uncontrolled. These are short single-seed pilots,
not multi-day evidence or a statistically reliable estimate of improvement.

Peko binaries rebuilt from the merged runtime:

- CLI SHA-256: `da42f5257a48cb1f6d124b522de8941f37a2978f7a2b26397c759b51b530b628`
- Daemon SHA-256: `64203cb0d34960a7d303583501573c4dbb081f056530081b57d9d0c67c493f2b`

Raw run ids:

- Peko: `20261007T023810989822Z-responsibility-peko`
- OpenClaw: `20261007T023811015707Z-responsibility-openclaw`

Raw native transcripts remain local and ignored. Retain every result, including
formation failures, missing actions, incomplete usage or registration/execution
failures. Reference pricing does not represent actual Token Plan deductions.

## Results

Both harnesses completed formation, all three requirement/review handoffs,
the full unattended watch and native restart. All four registration checks
and both worker/supervisor execution checks passed. Neither had controller
continuations, human interventions or native outbound messaging. OpenClaw
remained the pinned `2026.9.8 (fc23bc8)` installation with Node `v24.17.0` and
unchanged entry/installation hashes. [Aggregate evidence](RESPONSIBILITY_RECOVERY_MIMO_2026-10-07.json)
contains the metrics, action times, phase usage and recovery limitations.

| Measure | Peko | OpenClaw |
|---|---:|---:|
| Full gate | Fail | Fail |
| Completed obligations | 2/3 | 2/3 |
| Obligations on time | 2/3 | 2/3 |
| Missed deadlines | 1 | 1 |
| Repeated actions | 1 | 0 |
| Forbidden actions | 2 | 1 |
| Actions in quiet windows | 1 | 1 |
| Memory facts | Unmeasured; scored 0/16 after probe rejection | 16/16 |
| Actual world reads during watch | 4 | 5 |
| Maximum inter-read gap | 61.707s | 62.689s |
| Registered and executing topology | Verified | Verified |
| Forwarded model requests, all phases | 60 | 48 |
| Controller-rejected requests | 4 | 0 |
| Uncached input tokens | 230,843 | 258,364 |
| Cache-read input tokens | 1,810,048 | 1,025,152 |
| Output tokens | 16,553 | 11,177 |
| Complete PAYG reference cost | $0.0420209944 | $0.0421709456 |
| Usage complete / native reconciliation | Yes / yes | Yes / yes |
| Whole-run wall time | 583.256s | 427.160s |

Both accounted for every forwarded call, with usage matching native persisted
records. The pair used 108 forwarded calls, totaling $0.08419194 at the frozen
historical reference rates. These are reference costs, not subscription
charges; actual Token Plan credits require the owner's dashboard. The
Peko quota snapshot also matches 60 calls, but its two-rate native pricing
counter is not the cache-aware relay reference cost.

## Peko: post-restart liveness, but the fault window was not exercised

World reads occurred at 4.279, 65.986, 123.553 and 183.186s. The worker resumed
scheduled execution after restart and delivered Cedar at 190.497s, before its
240s deadline. The final worker job has `run_count=7`, advances its due time
and has no open rows at the post-watch snapshot. Coalescing messages during
live turns terminate when those turns finish; this is different from the
previous pair's permanently open row and 67 post-restart skips.

However, this sample does **not** directly validate the newly added recovery
branch. The pre-restart worker completed at `02:43:16.926927Z`, before the
controller stopped the daemon at the fixed 35s point. The supervisor also
finished before shutdown. There is no interrupted-row recovery message in
the new daemon log or corresponding recovered failure row. The model-free
regression from PR #424 remains the direct proof of abandoned-row recovery.
This sample establishes that the merged build continues scheduled work after
a native restart; it does not show a live interrupted completion wait being
recovered. Do not attribute the changed completion count causally to the fix.

## Peko: known receipt deliberately replayed

Dogwood input was requested at 11.423s after a 4.279s world observation, despite
the canonical requirement's 180s threshold. The worker's final response even
acknowledged that the request was early, while interpreting the general
blocked-state action as sufficient authorization. This is a precondition
violation, not missing threshold information.

Atlas's first POST was at 72.776s with the correct r2/recipient/key. Its last
world read, at 65.986s, had explicitly shown `ready=false`. The worker received
HTTP success and receipt 14, persisted it, and marked Atlas delivered with a
note that certification was pending. At 123.553s it reread both that receipt
and the delivered state, observed readiness, then submitted the identical
payload at 130.453s. It retained receipt 17 and labeled the second attempt a
retry after readiness. Both POST commands were direct and successful; receipt
and state edits also succeeded. There was no shell-timing failure, lost
receipt or restart between these two POSTs. The model deliberately replayed
a known recorded action to reconcile its uncertified state.

There is a grader limitation here: the unchanged action grader credits the
first Atlas POST because the simulator was ready by actual POST time, even
though the model had not observed readiness. Thus its scored 2/3 result does
not certify compliance with the prompt's observed-readiness rule. The
second POST is still forbidden and counted as a repeat. Preserve this score
and disclose the blind spot rather than changing the grader after the run.

## Request exhaustion and the missing memory measurement

Peko consumed 14 setup and 18 conversation-phase calls before the watch,
then 28 watch-phase calls. OpenClaw consumed 4 setup and 8 conversation-phase
calls, then also 28 watch-phase calls and 8 probe-phase calls. Pre-watch phases
include native scheduled activity as well as foreground onboarding/hand-offs;
these labels are not pure task attribution. Peko's 60-call allowance was
therefore exhausted before its memory probe. Four later attempts were refused
by the controller relay, including the probe. The reported 429 is the local
admission limit, not upstream MiMo quota exhaustion. Its $0.10 reference-cost
and 30,000-output-token limits were not reached.

The watch completed, but no memory object was submitted. The unchanged grader
scores 0/16 and one protocol error for the absent probe; this cannot establish
that Peko forgot its commitments. Its retained table and receipt log contain
the actual actions. Full usage is complete despite the unadmitted probe;
the probe-only phase has no forwarded calls and is marked usage-incomplete by
the existing phase summarizer. Distinguish a censored memory measurement from
incorrect answers to an admitted probe.

## OpenClaw: timely releases, early escalation and receipt-history loss

OpenClaw read the current requirements, including the explicit 180s/240s
Dogwood rule, then observed world time 17.145s. It requested input at 22.103s
and wrote a receipt note claiming `180s+` had been reached, while preserving
17.145 as the observation time in that same row. This failure is independent
of requirement freshness or scheduler restart behavior.

Atlas was delivered correctly at 80.115s after its 71.355s ready observation;
Cedar at 198.839s after its 195.140s ready observation. It preserved Birch's
cancellation and did not repeat any action. All three obligations had an
eligible observation before their deadlines; the early Dogwood request was
never replaced by a correctly timed request. Its memory probe at 309.559s
reported all 16 facts correctly.

The append-only receipt log still degraded: the Atlas receipt edit replaced
the Dogwood row, and the later memory-probe edit replaced the Cedar row with
the memory submission. These native edits reported success and the final
file lacks both operational rows. This did not cause a scored repeat or wrong
memory answer in this sample, but the 16-fact metric checks only revision,
recipient, delivery key and actual status. It does not check deadline/threshold
retention or preservation of append-only receipt history. A full memory score
is not evidence that every persistent-state invariant held.

## Interpretation and next experiment

Both runs have functioning task/supervisor separation but fail the full gate.
The shared model violated explicit temporal preconditions; Peko additionally
replayed a retained side effect, and OpenClaw erased receipt history. Plain
language instructions and Markdown state allow this even with direct commands
and correct schedule registration. No new deterministic runtime defect was
established by these action failures; do not present them as another cron
recovery bug or resolve them by silently adding controller decisions.

Before larger trials, use a separately labeled deterministic native restart
probe that targets an actual untracked in-flight row, instead of relying on a
35s restart to intersect model-dependent timing. Retain the current formation
experiment, and measure prepared-topology execution separately so onboarding
cost and memory-probe admission can be distinguished from steady operation.
Expose action-time versus last-observed readiness, threshold retention and
receipt preservation as diagnostic coverage; any new scored rules require a
versioned protocol and retained historical results. Enforcing structured
preconditions or idempotency must be an explicit, equally available intervention
for both harnesses, not an undisclosed benchmark-controller rescue. More prompt
accumulation and repeated runs until success do not establish reliability.

Validation: runner manifests match the preceding pair and the checkout;
common wire fields were verified for every forwarded request; both scores were
replayed from retained ledgers; both usage totals reconcile with native rows.
All four owned native processes are stopped. No extra live retry, budget
increase, prompt change, deduplication or grader change was used.
