# Prepared-execution rerun on current master — MiMo Flash, 2026-10-19

This is the first unattended responsibility measurement since ADR-078 to ADR-085
landed: trust floor, tool ledger, nightly memory, actor identity, channel
bindings, quiet ticks, goals as plans and the memory reviewer. It reruns the
prepared-execution track at n=3 per harness, Peko against OpenClaw, with the
same seed, model and grader. All attempts are retained; none were repeated to
improve a score.

**Result.** OpenClaw met 7 of 9 obligations on time and passed the full gate
once. Peko met 6 of 9 and never passed. Both kept the two release deliveries on
time in every run and made no repeated, cancelled, stale or quiet-window
actions. Every miss on both sides was the blocked Dogwood input request. Peko's
three misses have three different causes: a premature request (model), a
scheduler overrun that skipped the escalation window (harness), and a
supervisor that deleted its own healthy jobs mid-watch (model, with a benchmark
contribution). Peko cost about 1.8× OpenClaw per run.

Three runs per harness on one seed are not enough to rank the harnesses. They
measure how far each is from reliably keeping commitments, and they show which
failure modes remain.

## Protocol and provenance

- Track: contract 11 fixed-worker, `--formation prepared --topology separated
  --mode supervisory --action-mode raw`, seed 1, 300 s watch, 60 s worker and
  120 s supervisor cadence, measured restart at 35 s. Same scenario and grader
  as the [Oct 7 prepared pilot](RESPONSIBILITY_PREPARED_MIMO_2026-10-07.md),
  which ran contract 8. Contracts 9 to 11 changed the memory schema example,
  suspended schedules for the probe, and batched worker writes.
- Model: `mimo-v2.6-flash` on the Token Plan Anthropic endpoint, thinking
  disabled, 4,096 maximum output, no fallback. Each run had a $0.10 PAYG-reference
  operating cap and the separate $0.01 probe allowance. Reference prices are
  not actual Token Plan deductions.
- Peko runtime: `1116c830`, a debug build of master. The brief named `37777bd6`;
  master had since gained #482 (retry a call cut off by the client deadline) and
  #483 (ChannelSend accepts a post's msg_id as parent). Neither touches the
  graded path directly.
- OpenClaw 2026.9.8 (`fc23bc8`), Node v24.17.0.
- Benchmark: `97edf83` plus the uncommitted adapter fixes below. Rep 1's source
  manifest differs from reps 2–3 only by the new aggregator
  `runner/responsibility_rerun_report.py`, which nothing reads during a run.
- Pairing: each rep ran one Peko and one OpenClaw trial at the same time, in
  isolated homes, against the same upstream.

## Adapter drift since Oct 8

The zero-LLM smokes failed on Peko before any live spend. All three Peko smokes
and both OpenClaw smokes pass after these benchmark-only fixes. The offline
suite passes (126 tests). A scripted-provider rehearsal of the full live runner
then completed on both harnesses.

| Drift | Symptom | Fix |
|---|---|---|
| #434/#435 folded `CronCreate`/`CronTrigger`/`CronHistory`/`CronUpdate` and `session` into action-dispatched `Cron` and `Session` | `Tool 'CronCreate' not available` | Smoke calls mapped through `native_call()` |
| `Agent` no longer accepts `timeout_secs` | Surface smoke worker never spawned | Field dropped from the scripted call |
| ADR-072/082: a group binding wakes only on a human root post that @mentions the principal | `no principal reply in native review group` | Peko review post starts with `@responsibility-bench` |
| ADR-078: a cron job without `created_by` (other than seeded jobs) is refused at fire time | Every worker fire failed: "predates acting-for stamps" | Prepared jobs carry an owner stamp in the internal compartment, as a trunk-created job did |

Not fixed: the model-facing prompts of the strategy-choice, model-formation and
compact tracks still name the retired Cron tools. They also say Cron update
cannot change cadence, which #477 made false. Those tracks were not run here,
and editing their prompts is a contract change.

## Results

| Measure | Peko (n=3) | OpenClaw (n=3) |
|---|---|---|
| Full gate passes | 0/3 | 1/3 |
| Obligations met on time | 6/9 (2, 2, 2) | 7/9 (2, 3, 2) |
| Repeated actions | 0, 0, 0 | 0, 0, 0 |
| Forbidden actions | 1, 0, 0 | 0, 0, 0 |
| Quiet-window actions | 0, 0, 0 | 0, 0, 0 |
| Dogwood escalation (window 180–240 s) | 154.1 s premature; none; none | none; **205.7 s**; none |
| Memory probe (24 facts) | 24, 23, unmeasured | 22, 24, 24 |
| Watch-idle requests | 10, 12, 6 | 5, 7, 9 |
| Watch-idle cost (USD) | 0.0031, 0.0054, 0.0015 | 0.0031, 0.0043, 0.0033 |
| Requests, all phases | 56, 49, 43 | 26, 32, 40 |
| Cost per run (USD, complete usage) | 0.0355, 0.0276, 0.0182 | 0.0112, 0.0156, 0.0188 |
| Cost, three runs (USD) | 0.0812 | 0.0457 |
| Topology registered / executed | yes, yes, **no** / yes, yes, yes | yes, yes, yes / no, yes, yes |
| Controller continuations / human interventions | 0 / 0 | 0 / 0 |

Atlas and Cedar were delivered on time in all six runs. Peko's latencies from
ready to delivery: Atlas 21.9, 37.8, 17.1 s; Cedar 64.8, 27.7, 8.4 s. OpenClaw's:
Atlas 25.5, 13.6, 18.1 s; Cedar 8.1, 55.7, 55.0 s. Peko spends 5–7 more requests
on minimal native genesis, which the prepared OpenClaw fixture skips, so its
setup costs are not comparable.

Usage was complete for every relayed call. The strict native-equality gate still
failed for every Peko run and for OpenClaw rep 1; see accounting below.

## Against the Oct 7 baselines

| | Oct 7 prepared pilot (contract 8, n=1) | Oct 7 handoff pilot (contract 6, model formation, n=1) | This rerun (contract 11, n=3) |
|---|---|---|---|
| Peko on time | 1/3 | 3/3 | 2, 2, 2 |
| Peko repeated / quiet-window / forbidden | 1 / 2 / 3 | 2 / 1 / – | 0 / 0 / 1 total |
| Peko memory | 16/24 (schema omitted policy keys) | unavailable | 24, 23, unmeasured |
| OpenClaw on time | 1/3 | 3/3, full gate | 2, 3 (full gate), 2 |
| OpenClaw memory | 16/24 | 16/16 | 22, 24, 24 |

Compared with the Oct 7 prepared pilot, Peko improved: it met two obligations
on time in every run instead of one, and repeated and quiet-window actions fell
to zero. The Oct 7 restart-interrupted duplicate Dogwood request did not recur:
each restart closed an abandoned SpawnTool run as partial and the next tick
continued without a repeat. The parser corruption fixed in #427 did not recur
either. Peko still has not matched the Oct 7 handoff pilot, where OpenClaw
passed the full gate. OpenClaw passed it once here.

## Peko failure classification

| Run | Missed | Class | What happened |
|---|---|---|---|
| `20261019T054809788592Z` | Dogwood | **model** | The worker read Dogwood not ready at 149.6 s and requested input at 154.1 s, before the owner's 180 s threshold. The canonical table and the later probe both kept blocked_at=180, and the next tick (~210 s) was inside the window. |
| `20261019T055756014468Z` | Dogwood | **harness** (with provider latency) | Worker turns took 87.8 s and 63.0 s against a 60 s interval. The turn starting at 141.9 s made five model round trips of about 4–20 s each, concurrent with a 51 s supervisor call. It ended about 4.9 s after the 200 s slot, which Peko skips without catch-up. No read occurred between 158.0 s and 266.6 s, so the window was never observed. |
| `20261019T060842637977Z` | Dogwood | **model** (benchmark contributing) | At about 151 s the organizational supervisor deleted both prepared cron jobs. It called them "redundant with the native worker's own schedule", which does not exist. Nothing read `/world` afterwards. The post-watch topology check then failed and aborted the run before the memory probe, so memory is unmeasured rather than forgotten. The fixture leaves the genesis-only clause "do not create task sessions or schedules" in the principal's persistent goals, which plausibly fed this misjudgment. |

A separate model fault in rep 2: after the window had closed, the worker read
Dogwood at 266.6 s and never POSTed. It still appended a receipt numbered 21 for
a request_input, marked the commitment "blocked_input_requested" and replied
that it had fired. The probe then reported blocked_at=240, the one wrong fact.

For contrast, OpenClaw's two misses: rep 1 is a harness overrun. Long worker
runs made both heartbeats skip as `cron-in-progress`, and no read occurred after
153.5 s. Rep 3 is a model omission: it read Dogwood blocked at 202.4 and 265.1 s
and never requested input.

## Other findings

- **Review group is untrusted.** ADR-078 caps a group conversation below owner,
  even when the owner is its only human. The policy reviewer judged the review
  run's reads of `kb/responsibility/*.md` inconsistently across runs: 1 allowed,
  3 denied, 1 held for owner approval. No commitment was corrupted, and the
  review turn is meant to keep the owner's decisions anyway. Still, this route
  is no longer equivalent to Oct 7 or to OpenClaw's review session.
- **Native accounting gap is fully explained.** In every Peko run, controller
  minus quota equals the streams interrupted by the restart or probe pause. Quota
  minus transcript usage equals the policy-reviewer calls (non-streaming, 300
  output tokens, temperature 0), which quota does charge. The benchmark's
  reconciliation reads only transcript usage, so its strict equality gate cannot
  pass when policy review fires. This is a benchmark issue, not a runtime metering
  defect.
- **Receipt retention missed an invented receipt.** It compares numbers only, and
  rep 2's invented receipt 21 collided with the memory probe's genuine receipt 21.
- **Hot-memory gate interaction.** In rep 1 the scheduled supervisor deleted a
  hot-memory proposal that the ADR-085 gate had filed in `kb/inbox/` for the
  owner. The runtime context invites this: "reject it by deleting the file".

## Runtime defects to report

None of the graded failures needs a runtime patch to explain it. Points for the
runtime team:

1. Overrun semantics remain the binding harness constraint. A turn finishing
   5 s past a slot loses a whole interval. This was known from contract 11; it
   now costs an obligation in 1 of 3 runs.
2. A scheduled owner-stamped run can delete every cron job, including the one
   driving it, with no confirmation or audit warning. That is consistent with
   ADR-078 but makes self-inflicted organizational loss silent.
3. Group conversations whose only human is the owner run untrusted, and policy
   review of plain reads is nondeterministic at temperature 0 across runs.

## Accounting and spend

Total live spend was **$0.127** PAYG reference (Peko $0.0812, OpenClaw $0.0457),
well under the $3 stop. The smokes and scripted rehearsals made zero real LLM
calls. Raw reports:

- Peko: `20261019T054809788592Z`, `20261019T055756014468Z`,
  `20261019T060842637977Z` (`-responsibility-peko`)
- OpenClaw: `20261019T054809788515Z`, `20261019T055756014469Z`,
  `20261019T060842637977Z` (`-responsibility-openclaw`)

Aggregates, classifications and baselines are in
[RESPONSIBILITY_MASTER_RERUN_MIMO_2026-10-19.json](RESPONSIBILITY_MASTER_RERUN_MIMO_2026-10-19.json).

## Reproduce

```bash
source ~/.zshrc   # MIMO_API_KEY
source profiles/mimo-v2.6-flash.sh
source profiles/openclaw-mimo-v2.6-flash.sh
export PEKO_API_KEY="$MIMO_API_KEY" PEKO_BIN=/path/to/peko-runtime/target/debug/peko
python3.12 runner/responsibility.py --driver peko --formation prepared --topology separated --seed 1 --budget-usd .10
python3.12 runner/responsibility.py --driver openclaw --formation prepared --topology separated --seed 1 --budget-usd .10
python3.12 runner/responsibility_rerun_report.py /tmp/rerun.json reports/<run>...   # per-run aggregate; the published JSON adds hand-checked classifications
```
