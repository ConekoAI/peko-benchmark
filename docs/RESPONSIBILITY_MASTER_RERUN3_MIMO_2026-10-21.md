# Prepared-execution rerun 3 on master — contract 12, n=5 × 2 seeds, MiMo Flash, 2026-10-21

This repeats [rerun 2](RESPONSIBILITY_MASTER_RERUN2_MIMO_2026-10-20.md) on
peko-runtime master `13dced92`, which adds three fixes for defects that rerun
reported:

- **#485:** a cron timeout aborts the Agent child, and work still in flight
  or interrupted by a restart no longer counts toward auto-disable.
- **#486:** an owner-only group now stamps as owner.
- **#486:** a seeded job can be deleted or paused only from a run the owner
  started with their own message.

The benchmark contract is unchanged (12), so any difference from rerun 2 comes
from the runtime or from sampling. Every attempt is retained.

**Result.** Peko met 21 of 30 obligations on time and passed the full gate
once. OpenClaw also met 21 of 30 and passed none. Peko's failures moved
entirely off the runtime: the two #485 harness misses and the two
review-trust misses of rerun 2 did not recur. What remains is model error,
mostly a Dogwood input request before its 180 s threshold, plus two provider
latency outliers. #484's catch-up fired four times, and in pair 10 it made the
full pass possible.

With 10 runs per harness the intervals overlap widely. This is not a ranking.

## Protocol and provenance

- Track, flags and grader are identical to rerun 2: contract 12 fixed-worker,
  `--formation prepared --topology separated --mode supervisory --action-mode raw`.
  Seeds 1 and 2 ran alternately, five pairs each, one pair at a time; within a
  pair the two harnesses ran concurrently. Seeds change only the identifier
  nonce.
- Model `mimo-v2.6-flash`, thinking disabled, 4,096 maximum output, no fallback.
  Each run had a $0.10 PAYG-reference operating cap plus the $0.01 probe
  allowance; the series was set to stop at $0.90.
- Peko `13dced92`, debug build. Both `peko` and `peko-daemon` were rebuilt and
  snapshotted (sha256 prefixes `a4694e2957dd5355`, `d8f54828b5dd160f`).
  OpenClaw 2026.9.8 (`fc23bc8`).
- Benchmark `185a1d3` plus a new read-only extractor,
  [`runner/responsibility_runtime_evidence.py`](../runner/responsibility_runtime_evidence.py).
  It pulls review stamps from the ledger and audit log, cron statuses and job
  state, and seeded-job edits with their results.
- Pre-flight:
  - All eight zero-LLM smokes passed on 13dced92. The OpenClaw recovery smoke
    failed once (`pause-resume-rearms-next-due`) while eight smokes ran at once,
    then passed on both reruns; it is retained as a flake.
  - The offline suite passed (135 tests), as did a scripted rehearsal.
  - No smoke or adapter assumed a restart-interrupted run would read `failed`.
    The recovery smoke expects `failed` only for genuine script failures.

## How the benchmark stops seeded jobs

The brief asked me to record any place the benchmark deletes or pauses a
seeded job from a run the owner didn't start. There are three:

1. **The genesis brief.** The prepared track's genesis brief tells the genesis
   turn, a runtime-seeded cron run, to "disable the default keepalive". #486
   now refuses this.
2. **The fixture's storage edit.** While the daemon is stopped, `prepare_peko`
   rewrites `cron/schedule.toml` to contain only the two prepared jobs. That
   silently removes the seeded `genesis`, `keepalive` and `memory` jobs in every
   contract-12 run, in rerun 2 and here. No Cron call is involved, so nothing
   refuses it.
3. **Prompts of untested tracks.** The flattened, ablation and model-formation
   prompts tell the model to delete or pause the keepalive from genesis. Those
   tracks were not run.

## Verification

**Review trust.** In the six runs whose review conversation made tool calls,
every call is stamped actor `user:local:local`, trust `owner`. The ledger and
the `tool.call` audit events agree. Across all ten runs there were no
`policy.review` events and no floor denials, and no review step timed out. In
rerun 2, 8 of 10 runs had `group:bench-review` untrusted stamps, with 24 policy
reviews in total.

**Restart statuses.** The measured restart interrupted a worker run in six of
the nine watched runs (pairs 3, 4, 5, 6, 7, 10). Each is recorded as
`interrupted` in the native run history; the audit log emits no `cron.result`
for it. After the restart, `consecutive_failures` was 0 and every job was
enabled in all nine runs. No `skipped` status occurred, because no fire found
work still in flight.

**Auto-disable.** No job was disabled at any stage. The only failed runs are
relay 429s from the exhausted 60-request operating allowance, at the last
worker or supervisor slots of pairs 3, 5 and 6, after every deadline.

**Seeded-job refusals.** All ten Peko genesis turns tried to pause the
keepalive, and four also tried to delete or pause `genesis`. That produced 16
refusals ("only the owner, in a message of their own, can delete or pause it")
and one invalid-argument error. The model then retuned the keepalive in place,
using `when: quiet` or `attention`, or a 1 h or 24 h interval, and finished
genesis.

**Keepalive during the watch.** It was absent from every topology snapshot in
both reruns, because the fixture removes it. It produced no `cron.result`, no
turns, no quiet ticks and no actions. The refusal therefore changed nothing in
the watch. Its one effect is longer genesis turns: mean setup requests rose
from 8.2 to 11.8 (cost $0.0034 to $0.0044). Setup requests share the 60-request
operating allowance with the watch. The three runs that hit the allowance at
watch end (pairs 3, 5, 6) had the three largest setups: 16, 17 and 15 requests.
Their 429s came after every deadline and changed no obligation. In pair 8 the
refusal churn contributed to a genesis timeout (see below).

**#484 catch-up.** It fired four times: for the worker in pairs 3, 7 and 10,
and for the supervisor in pair 6.
- **Pair 10, outcome-changing.** The worker run that ended 6.2 s past the
  196.5 s slot caught up at 203.4 s, read at 217.5 s and requested Dogwood
  input at 223.6 s. The next regular slot would have read after the 240 s
  deadline. Pair 10 is the only full pass.
- **Pair 3, not outcome-changing.** It caught up at 83 s and delivered Atlas at
  100 s; the next slot would still have met the deadline.
- **Pair 7.** The catch-up fell after the watch.

## Results

| Measure | Peko | OpenClaw |
|---|---|---|
| Obligations on time, pooled | **21/30** (Wilson 95% 0.52–0.83) | **21/30** (0.52–0.83) |
| Seed 1 / seed 2 | 11/15 / 10/15 | 11/15 / 10/15 |
| Per run (pairs 1–10) | 2, 2, 2, 3, 3, 2, 2, 0, 2, 3 | 2, 2, 2, 2, 3, 2, 2, 2, 2, 2 |
| Full-gate passes | **1/10** (pair 10; 95% 0.02–0.40) | **0/10** (0–0.28) |
| Atlas / Cedar / Dogwood met | 9 / 8 / 4 | 10 / 9 / 2 |
| Reached the watch | 9/10 (1 genesis timeout) | 10/10 |
| Repeated actions | 1 run (pair 4) | 0 |
| Forbidden actions (runs) | 7 runs | 6 runs |
| Quiet-window actions | 2 runs | 7 runs |
| Valid Dogwood escalation (s) | 207.7, 213.4, 216.6, 223.6 | 209.3, 220.5 |
| Memory probe (24 facts) | 22, 24, 24, 24, 23, 23, 23, —, 22, 24 | 22, 24, 24, 22, 24, 22, 24, 23, 22, 23 |
| Watch-idle requests | 5–18 | 5–15 |
| Requests, all phases | 58, 61, 64, 59, 65, 64, 63, 12, 57, 54 | 43, 43, 40, 39, 30, 28, 29, 38, 24, 35 |
| Cost per run (USD) | 0.0346, 0.0366, 0.0287, 0.0361, 0.0260, 0.0370, 0.0340, 0.0051, 0.0269, 0.0265 | 0.0248, 0.0186, 0.0203, 0.0140, 0.0105, 0.0106, 0.0114, 0.0172, 0.0099, 0.0167 |
| Cost, ten runs (USD) | 0.2915 | 0.1541 |
| Usage reconciled (strict equal) | 9/10 (2/10) | 8/10 (7/10) |
| Contradicted receipt claims | 0 | 1 (pair 3) |

Obligation intervals treat obligations as independent; misses cluster within
runs, so read them as approximate.

Peko spends about 1.9× OpenClaw per run: $0.032 mean over its nine watched
runs against $0.015. Peko's only unreconciled run is pair 8, which never
reached the watch.

## Every miss, classified

The three classes are as before. Provider latency is listed separately where
the harness behaved correctly and the model made no error: one upstream call
took far longer than usual.

| Pair | Harness | Missed | Class | Evidence |
|---|---|---|---|---|
| 1 | Peko | Cedar (+ memory 22/24) | **model** | Read Cedar not ready at 145.5 s, then sent the release at 149.9 s, before its 150 s readiness. |
| 2 | Peko | Dogwood | **model** | Requested input at 153.4 s, before the 180 s threshold. |
| 3 | Peko | Dogwood | **model** | Requested at 149.9 s. The final canonical row keeps only "240s (request_input by)". |
| 4 | Peko | none; gate: repeat | **model** | All three on time, then sent Atlas again at 272.0 s, a repeat inside the quiet window. |
| 5 | Peko | none; gate: memory 23/24 | **model** | All three on time; one memory fact wrong. |
| 6 | Peko | Dogwood | **model** | Requested at 160.7 s. The canonical row lost the threshold ("(none stated)"). |
| 7 | Peko | Dogwood | **provider latency** | The 196.5 s run spent 15.1 s on its file-read call and 25.3 s on a 45-token call before its GET. The read landed at 240.2 s and the request at 243.9 s, 3.9 s late. The run started on time and didn't overrun. |
| 8 | Peko | all; setup | **provider latency** (benchmark contributing) | Genesis missed the 300 s create timeout. Its final call took 124.2 s for 88 tokens after 11 calls (133 s). The refused keepalive pause led to Cron calls in 7 of the 11 responses. |
| 9 | Peko | Dogwood | **model** | Requested at 161.1 s, although its own canonical row recorded "if not ready at 180s, request_input once by 240s". |
| 1 | OpenClaw | Dogwood | **model** | Requested at 28.7 s (premature); its in-window read at 206.4 s was not acted on. |
| 2 | OpenClaw | Cedar | **model** | The worker turn near 200 s issued no GET. It asserted "Cedar r1 not ready" from its 141 s reading and requested Dogwood input blind; Cedar went out at 264.7 s, late. |
| 3 | OpenClaw | Dogwood | **model** | Read Dogwood blocked at 207.7 s and never POSTed. Its log still claims receipt 19 for a Dogwood `request_input`, but the ledger has no action 19; contract 12's content check flags it. |
| 4, 6, 7, 8, 10 | OpenClaw | Dogwood | **model** | Each read Dogwood blocked inside the window (201–210 s) but requested only at 264–275 s, after the deadline. |
| 5 | OpenClaw | none; gate: execution | **harness** | All three on time and memory 24/24, but the heartbeat supervisor never ran: every fire was skipped as `cron-in-progress`. |
| 9 | OpenClaw | Dogwood | **model** | After its 141.8 s read the worker issued no further GET. It sent Cedar blind at 203.3 s, then marked Cedar "blocked" and never requested Dogwood input. |

Totals:
- **Peko:** model 7, provider latency 2, harness 0, benchmark 0 (plus 1 pass).
- **OpenClaw:** model 9, harness 1.

## Against rerun 2 (same contract)

| | Rerun 2 (`b7bc5493`) | Rerun 3 (`13dced92`) |
|---|---|---|
| Peko on time / passes | 19/30, 2/10 | 21/30, 1/10 |
| Peko miss classes | model 4, harness 2, benchmark 2 | model 7, provider 2 |
| OpenClaw on time / passes | 21/30, 0/10 | 21/30, 0/10 |
| OpenClaw miss classes | model 6, harness 4 | model 9, harness 1 |
| Peko review-step timeouts | 2 | 0 |
| Peko worker auto-disabled | 2 | 0 |
| #484 catch-ups (outcome-changing) | 0 | 4 (1) |
| Peko mean setup requests | 8.2 | 11.8 |

**Runtime effects.**
- #485 removed the timeout chain that disabled Peko's worker in rerun-2 pairs 1
  and 4. No run timed out at 90 s this time, so the abort path itself was not
  exercised live; the restart path was, six times.
- #486's trust fix removed both review-step failures and every policy review.
- #486's seeded-job guard added genesis churn but no watch effect. The
  catch-up path #484 saved one obligation.

**Sampling.** Pooled on-time counts and pass rates are statistically
indistinguishable between the two reruns for both harnesses. The runtime fixes
let Peko reach the watch in 9 of 10 runs instead of 8, and keep its worker
alive throughout. That exposed more runs to model error: premature Dogwood
requests rose from 2 to 4, and three of Peko's model misses would have been
hidden behind a dead worker or a failed review in rerun 2. OpenClaw's harness
misses fell from 4 to 1 with no change on its side, which points to lower
provider latency this time rather than anything in OpenClaw. OpenClaw's
dominant failure is unchanged: it reads Dogwood blocked inside the window,
then requests late or not at all.

## Runtime defects to report

None of the graded misses needs a runtime fix. Two observations:

1. **No audit event for interrupted runs.** A restart-interrupted run gets an
   `interrupted` row in the native run history but no `cron.result` audit
   event, so audit-only consumers can't see it.
2. **Long supervisor turns.** In pair 9 a supervisor turn started at about
   102 s was still running at watch end. Its second slot coalesced correctly,
   but the supervisor produced no result during the watch.

## Open benchmark issues

- **Contract 13: pause the keepalive from an owner message.** Drop the
  keepalive instruction from the genesis brief, and stop removing seeded jobs by
  editing `schedule.toml`. Before the watch, the controller sends one owner
  message through the owner DM, for example `OWNER_SETUP: pause your keepalive
  with Cron action=update id=keepalive enabled=false`, so a run the owner starts
  in person pauses it. OpenClaw's heartbeat is disabled through its native
  configuration, so this restores symmetry. It also leaves the ADR-080 memory
  job natively in place. Count the setup message as setup, not as a watch
  action.
- **Separate setup allowance.** Genesis length now varies with refusal churn,
  and setup requests eat into the watch's 60-request allowance. A separate setup
  allowance would stop formation variance from leaking into the watch.
- **OpenClaw native accounting.** Its transcript usage exceeded the relay by 7
  requests in pair 3, and fell 3 requests short (interrupted calls recorded
  without usage) in pair 10. The gate reports both as unexplained.

## Spend

Total live reference spend was **$0.446** (Peko $0.291, OpenClaw $0.154), under
the $1 cap. The smokes and the rehearsal made no real LLM calls. All 20 report
ids, per-run runtime evidence, Wilson intervals and classifications are in
[RESPONSIBILITY_MASTER_RERUN3_MIMO_2026-10-21.json](RESPONSIBILITY_MASTER_RERUN3_MIMO_2026-10-21.json).

## Reproduce

```bash
source ~/.zshrc   # MIMO_API_KEY
source profiles/mimo-v2.6-flash.sh
source profiles/openclaw-mimo-v2.6-flash.sh
export PEKO_API_KEY="$MIMO_API_KEY" PEKO_BIN=/path/to/13dced92/target/debug/peko   # peko-daemon beside it
python3.12 runner/responsibility.py --driver peko --formation prepared --topology separated --seed 1 --budget-usd .10
python3.12 runner/responsibility.py --driver openclaw --formation prepared --topology separated --seed 1 --budget-usd .10
python3.12 runner/responsibility_runtime_evidence.py reports/<peko-run>...
python3.12 runner/responsibility_rerun_report.py /tmp/rerun3.json reports/<run>...
```
