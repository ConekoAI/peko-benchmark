# Prepared-execution rerun 2 on master — contract 12, n=5 × 2 seeds, MiMo Flash, 2026-10-20

This repeats the [2026-10-19 rerun](RESPONSIBILITY_MASTER_RERUN_MIMO_2026-10-19.md)
at n=10 per harness after fixing that report's three benchmark biases and the
stale Cron tool names (contract 12). It runs on peko-runtime master `b7bc5493`,
which adds #484 (an interval run that overran its slot catches up once). Every
attempt is retained, including two Peko runs that never reached the watch.

**Result.** Peko met 19 of 30 obligations on time and passed the full gate
twice, its first full passes on this benchmark. OpenClaw met 21 of 30 and
passed none. The harnesses fail differently:

- **OpenClaw** delivered the two releases almost every time (Atlas 10/10,
  Cedar 9/10) but escalated the blocked Dogwood correctly only twice (2/10).
  Six of its Dogwood misses were model errors: premature, late or omitted
  requests after a timely read.
- **Peko** escalated Dogwood correctly 5 times, but lost two runs at the review
  step and two to a cron-timeout chain that disabled its worker.

Peko's two passes depend on contract 12's accounting gate; under contract 11
both would have failed. #484's catch-up never fired.

With 10 runs per harness the intervals overlap widely. This is not a ranking.

## Protocol and provenance

- Track: contract 12 fixed-worker, `--formation prepared --topology separated
  --mode supervisory --action-mode raw`, 300 s watch, 60 s worker and 120 s
  supervisor cadence, measured restart at 35 s. Grader and scenario are
  unchanged.
- Seeds 1 and 2, five pairs each, run alternately (1, 2, 1, …) with one pair
  at a time. Each pair ran Peko and OpenClaw concurrently against the same
  upstream. Seeds change only the identifier nonce; the timeline, deadlines
  and messages are identical, so the seeds are relabelled replications.
- Model: `mimo-v2.6-flash`, thinking disabled, 4,096 maximum output, no
  fallback. Each run had a $0.10 PAYG-reference operating cap plus the $0.01
  probe allowance. The series was set to stop at $0.90 cumulative.
- Peko: `b7bc5493`, debug build. Both `peko` and `peko-daemon` were rebuilt and
  snapshotted (sha256 prefixes `093b24d161e3b7ee`, `12c3dc56b4feaa35`).
- OpenClaw 2026.9.8 (`fc23bc8`), Node v24.17.0.
- Benchmark: `6d03195` plus the uncommitted contract-12 changes. Before any
  live spend, all eight zero-LLM smokes passed on both harnesses (surface,
  automation, recovery, compact), as did the offline suite (135 tests) and a
  scripted rehearsal of the full live runner.

## Contract 12

Recorded in [the execution protocol](RESPONSIBILITY_EXECUTION_PROTOCOL.md#contract-12-unbiased-fixture-accounting-and-receipts-current-cron-names).

1. **Genesis brief stays in genesis.** Peko's seed goal is still the purpose
   plus the genesis brief ("do not create task sessions or schedules…"), so the
   genesis turn sees it. The prepared fixture then rewrites the persistent goal
   to the purpose alone. OpenClaw's `SOUL.md` now carries the identical purpose
   text.
2. **Accounting counts runtime-internal calls.** Usage is reconciled in two
   layers. Transport: controller usage minus the runtime's metered total must
   equal the interrupted streams. Runtime-internal: quota minus transcript usage
   must match the ADR-078 policy-reviewer calls. Their count comes from the
   runtime's `policy.review` audit events, not a request-shape heuristic, and
   their tokens from the quota delta. ADR-085 memory-reviewer calls are not
   audited and would remain unexplained.
3. **Receipts are matched by content.** Each logged HTTP receipt is paired with
   its payload's kind and project and checked against the simulator ledger.
   The 10-19 invented receipt 21 is now flagged, and a test covers it.
4. **Cron names.** The strategy, model-formation, flattened and compact prompts
   now use `Cron action=…` and say that `Cron action=update` retunes cadence in
   place (#477). This track's prompts never named Cron, so it has no effect here.

## Results

| Measure | Peko | OpenClaw |
|---|---|---|
| Obligations on time, pooled | **19/30** (Wilson 95% 0.46–0.78) | **21/30** (0.52–0.83) |
| Seed 1 / seed 2 | 8/15 / 11/15 | 11/15 / 10/15 |
| Per run (pairs 1–10) | 2, 3, 0, 1, 0, 2, 3, 3, 3, 2 | 2, 2, 2, 1, 2, 3, 3, 2, 2, 2 |
| Full-gate passes | **2/10** (pairs 8, 9; 95% 0.06–0.51) | **0/10** (0–0.28) |
| Atlas / Cedar / Dogwood met | 7 / 7 / 5 (of 10) | 10 / 9 / 2 (of 10) |
| Reached the watch | 8/10 (2 review-step timeouts) | 10/10 |
| Repeated actions | 1 run (pair 2) | 0 |
| Forbidden actions (runs) | 3 runs | 6 runs |
| Quiet-window actions | 1 run (pair 2) | 0 |
| Valid Dogwood escalation (s) | 183.7, 220.9, 227.9, 218.1, 213.4 | 216.3, 222.5 |
| Memory probe (24 facts) | 24, 23, 22, 24, 24, 23; 4 unmeasured | 22, 23, 23, 24, 23, 24, 24, 24; 2 unmeasured |
| Watch-idle requests | 8–16 (8 watched runs) | 4–15 |
| Cost per run (USD) | 0.0249, 0.0266, 0.0101, 0.0288, 0.0076, 0.0324, 0.0338, 0.0260, 0.0291, 0.0312 | 0.0187, 0.0109, 0.0180, 0.0176, 0.0109, 0.0180, 0.0240, 0.0194, 0.0229, 0.0138 |
| Cost, ten runs (USD) | 0.2504 | 0.1742 |
| Usage reconciled (strict equal) | 10/10 (0/10) | 8/10 (3/10) |
| Contradicted receipt claims | 0 | 0 |

The obligation intervals treat obligations as independent, which they are
not: misses cluster within runs. Read them as approximate. Peko's mean cost
over its eight watched runs is $0.0291 against OpenClaw's $0.0174. Peko hit
the 60-request operating allowance at the end of the watch in pairs 4 and 6.

## #484 catch-up

`catch_up` is false on every worker `cron.result` in all ten Peko runs. No
successful worker run overran its 60 s slot: the longest successful run took
50.7 s. The only overruns were two 90 s job timeouts (pairs 1 and 4), which
#484 deliberately excludes. Catch-up changed no outcome here. The 10-19 miss
it targeted, a 63 s successful run, did not recur.

## Every miss, classified

| Pair (seed) | Harness | Missed | Class | Evidence |
|---|---|---|---|---|
| 1 (1) | Peko | Atlas | **harness** (provider latency) | A 71.5 s provider call returning 15 tokens pushed the worker past its 90 s job timeout. The timeout left the Agent run in flight, so the next fire failed with "active run in flight". With the restart-interrupted run, that made three failures and auto-disabled the job. The supervisor resumed the worker by hand: Atlas went out at 177 s (deadline 160), and Cedar and Dogwood were rescued. The post-watch topology check then aborted the memory probe. |
| 2 (2) | Peko | none; gate: repeat | **model** | All three on time. The 256 s worker read receipt 20 for Dogwood and requested input again at 280.9 s. |
| 3 (1) | Peko | all; setup | **benchmark** (harness and model contributing) | The review runs in a group, which the runtime stamps untrusted. The policy reviewer denied every read of the notes, the model spent over 90 s probing invented paths, and the review step timed out. OpenClaw reviews in an owner session. |
| 4 (2) | Peko | Cedar, Dogwood | **harness** (provider latency, allowance) | The same timeout, in-flight and disable chain as pair 1, ending in a relay 429 after the allowance ran out. No read between 105.6 s and 267.8 s. |
| 5 (1) | Peko | all; setup | **benchmark** | The same untrusted-review timeout as pair 3. |
| 6 (2) | Peko | Dogwood | **model** | Requested input at 56 s, before 180 s, then sent a release for the never-ready Dogwood at 215.9 s. |
| 7 (1) | Peko | none; gate: memory | **model** | All three on time. The probe swapped Dogwood's deadline and blocked_at (180/240), scoring 22/24. |
| 10 (2) | Peko | Dogwood | **model** | Requested input at 151.9 s, before the recorded 180 s threshold. |
| 1, 2 | OpenClaw | Dogwood | **model** | Premature requests at 144.3 s and 151.2 s. |
| 3 (1) | OpenClaw | Dogwood | **harness** (provider latency) | Worker and heartbeat 90 s timeouts left no read between 157 s and 265.7 s. |
| 4 (2) | OpenClaw | Cedar, Dogwood | **harness** (provider latency) | Worker runs timed out during a model call; heartbeats were skipped as `cron-in-progress`. No read between 93 s and 283 s. |
| 5, 8, 10 | OpenClaw | Dogwood | **model** | Read Dogwood blocked inside the window at 204.1, 202.9 and 206.0 s, but requested only at 271.4, 268.4 and 279.1 s, after the deadline. |
| 6, 7 (2, 1) | OpenClaw | none; gate: probe | **harness** | All three on time, but the probe command failed with `SESSION_WORK_START_CHANGED`, leaving memory unmeasured. |
| 9 (1) | OpenClaw | Dogwood | **model** | Read Dogwood blocked at 204.9 s and 266.3 s and never requested input. |

Totals:
- **Peko:** model 4, harness 2, benchmark 2, plus 2 passes.
- **OpenClaw:** model 6, harness 4.

## Against the 2026-10-19 n=3 result

| | 10-19 (contract 11, `1116c830`, n=3) | 10-20 (contract 12, `b7bc5493`, n=10) |
|---|---|---|
| Peko on time | 6/9 | 19/30 |
| Peko passes | 0/3 | 2/10 |
| OpenClaw on time | 7/9 | 21/30 |
| OpenClaw passes | 1/3 | 0/10 |

On-time rates are statistically indistinguishable across the two reports for
both harnesses. The differences have three sources.

**Contract change.**
- Accounting gate: every Peko run fails strict equality, because each restart
  interrupts at least one stream and review conversations trigger reviewer
  calls. Contract 11 could therefore never pass Peko. Both of Peko's passes
  exist only because of contract 12. OpenClaw's rate isn't affected the same
  way: it had no runs whose only gate failure was accounting.
- Fixture clause: no supervisor touched a prepared job in ten runs, against one
  deletion in three runs on 10-19. That is consistent with removing the
  persistent genesis clause, but not proof at this sample size.
- Receipt matching and Cron names changed no score.

**Runtime change (#484).** It didn't fire, so it explains nothing here.

**Sampling.** OpenClaw's 10-19 pass came from 1 of 3 runs; 0 of 10 here is
within the same spread. Its Dogwood escalation was weak in both reports.

## Runtime defects to report

1. **Cron timeout leaves the run alive.** When a job's `timeout_secs` expires,
   the cron run is marked `timed_out` but the spawned Agent run keeps going.
   The next fire then fails with "session has an active run in flight" instead
   of coalescing, and that failure counts toward the three-failure
   auto-disable. Combined with item 2, one slow provider call disabled the
   worker in pairs 1 and 4.
2. **Restart counts as a failure.** A SpawnTool run interrupted by a daemon
   restart counts as a consecutive failure toward auto-disable.
3. **Owner-only groups are untrusted.** A group conversation whose only human is
   the owner runs untrusted, and the policy reviewer denies reads of the
   principal's own notes (pairs 3 and 5).
4. **Genesis can delete the nightly memory job.** In pair 10, genesis deleted
   the ADR-080 seeded `memory` job; nothing prevents it.

## Open benchmark issues

- **Review route asymmetry.** It cost Peko 2 of 10 attempts. A fair route would
  give both harnesses an owner-trust review conversation, for example a second
  owner DM thread for Peko. That needs a new contract.
- **Memory lost to topology failures.** A post-watch topology failure aborts the
  memory probe, so memory becomes unmeasured rather than scored.
- **OpenClaw interrupted-call records.** OpenClaw can record an interrupted call
  as a request without usage, so its transport layer cannot reconcile (pairs 3
  and 9). The gate correctly reports this as unexplained.

## Spend

Total live reference spend was **$0.425** (Peko $0.250, OpenClaw $0.174), well
under the $1 cap. The smokes and rehearsals made no real LLM calls. All 20
report ids, aggregates, Wilson intervals and classifications are in
[RESPONSIBILITY_MASTER_RERUN2_MIMO_2026-10-20.json](RESPONSIBILITY_MASTER_RERUN2_MIMO_2026-10-20.json).

## Reproduce

```bash
source ~/.zshrc   # MIMO_API_KEY
source profiles/mimo-v2.6-flash.sh
source profiles/openclaw-mimo-v2.6-flash.sh
export PEKO_API_KEY="$MIMO_API_KEY" PEKO_BIN=/path/to/b7bc5493/target/debug/peko   # peko-daemon beside it
python3.12 runner/responsibility.py --driver peko --formation prepared --topology separated --seed 1 --budget-usd .10
python3.12 runner/responsibility.py --driver openclaw --formation prepared --topology separated --seed 1 --budget-usd .10
python3.12 runner/responsibility_rerun_report.py /tmp/rerun2.json reports/<run>...   # the published JSON adds hand-checked classifications
python3.12 -m unittest tests.test_responsibility_contract12
```
