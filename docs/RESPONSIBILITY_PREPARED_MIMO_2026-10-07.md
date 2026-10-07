# Prepared execution pilots — MiMo Flash, 2026-10-07

Both prepared-topology pilots verified native worker/supervisor registration
and execution, survived the measured restart, and completed the 300-second
watch. Neither passed. Each completed only one obligation before its deadline.
This is stabilization evidence, not a ranking or proof of architectural benefit.

## Protocol and provenance

These are contract **8**, seed 1, separated native organization, supervisory
continuation, MiMo `mimo-v2.6-flash`, 4,096 maximum output tokens, thinking
explicitly disabled, no temperature override or fallback. Operating allowances
were 60 requests, 30,000 output tokens and $0.10 PAYG reference per harness;
probe allowance was separately 8 requests, 6,000 output tokens and $0.01.
Reference prices are frozen comparison inputs, not actual Token Plan charges.

The controller prepared an empty organization and notes; all commitment facts
arrived through owner/review conversations. This removes model-driven topology
formation from the execution experiment. Peko still completed minimal native
genesis; OpenClaw used its native baseline plus a prepared persona. Do not use
these differing setup procedures to claim equal formation cost.

- Peko runtime: merged [PR #425](https://github.com/ConekoAI/peko-runtime/pull/425),
  `8279f3fcbb794c5e536f21714f5fd0e5d455e4cb`.
- Peko pilot source: benchmark `4739556`; OpenClaw pilot source: `f849b08`.
  Three runner files differ because OpenClaw fixture repairs occurred after
  Peko launched. Those changes concern native clock/configuration handling;
  model-facing owner, worker, supervisor and probe prompts and wire policy
  remained identical. These are diagnostic samples, not a frozen causal pair.
- OpenClaw: pinned 2026.9.8 (`fc23bc8`), Node v24.17.0.
- Worker first due time was armed 20 seconds ahead. Peko supervision starts
  120 seconds ahead; OpenClaw preserves its system-owned heartbeat phase at
  the same 120-second cadence. Actual due times are retained in snapshots.
- Two OpenClaw setup failures were retained, both with **zero forwarded model
  requests**: an obsolete JSON store assumption, then an attempt to edit a
  system-owned heartbeat through cron clients. The repaired fixture uses native
  heartbeat configuration and `cron.update` only for the client-owned worker.

## Results

| Measure | Peko | OpenClaw |
|---|---:|---:|
| Completed obligations | 1/3 | 2/3 |
| Completed on time | 1/3 | 1/3 |
| Missed deadlines | 2 | 2 |
| Forbidden action attempts | 3 | 0 |
| Repeated actions | 1 | 0 |
| Actions in quiet windows | 2 | 1 |
| Observed-precondition violations | 2 | 0 |
| Retained non-memory receipts | 3/4 | 2/2 |
| Memory response, old core facts | 16/16 | 16/16 |
| Memory response, expanded protocol score | 16/24 | 16/24 |
| Native topology registration / execution | verified / verified | verified / verified |
| Controller continuation prompts during watch | 0 | 0 |
| Human interventions / native outbound messages | 0 / 0 | 0 / 0 |
| Full usage known / native totals match relay | no / no | no / no |

Late Cedar counts as a completed obligation for OpenClaw, but misses its
240-second deadline and violates the 240–300 quiet window. Peko's Cedar POST
occurred after the watch, so it cannot rescue completion. Neither remained quiet.
Prepared organization and measurement probes are declared controller actions,
separate from autonomous watch execution and human interventions.

## What happened

### Peko

World reads: **30.773, 48.936, 90.067, 149.125, 211.586, 285.632 seconds**.
All three obligations had a timely observation opportunity; the largest
inter-read gap was 74.046 seconds.

Dogwood was requested at **32.909**, before its 180-second threshold. The POST
succeeded, and receipt **9** persisted in the native worker transcript. Restart
interrupted the turn before the canonical receipt log and table were updated.
First-open recovery closed the abandoned SpawnTool row as failed with the
explicit partial-outcome warning. Later ticks resumed. The worker read a pending
Dogwood table and empty canonical receipt log after restart, then requested it
again at **56.348** (receipt 12). Final canonical receipts omit receipt 9.
The durable transcript contains the first result; the exact restarted wire
prompt was not captured, so we do not claim precisely which history the model
received. This is a divergence between action evidence and model-maintained
shared state, not an automatic runtime replay.

Atlas was correctly delivered at **105.819** (receipt 16), before deadline 160.

At **211.586**, Cedar was observed ready with **28.414 seconds** remaining.
The persisted native intent then selected **Edit** with Bash-shaped `command`
arguments for the delivery. Edit rejected missing `file_path`, `old_string`
and `new_string`; the assistant ended the turn without repairing the call.
The next read was 285.632, already late. A subsequent Cedar POST happened at
**300.246**, after the watch (receipt 23). The observed failure is tool selection
and unsuccessful recovery despite timely dependency observation.

The live restart exercised abandoned **untracked SpawnTool** recovery, extending
live evidence for #424. It did not exercise #425's missing attached-id branch;
that branch has deterministic persisted-state regression coverage.

### OpenClaw

World reads: **62.421, 66.411, 80.073, 264.168 seconds**. Its measured restart
finished at **57.301** after forced termination. Native logs show automatic
restart recovery, its terminal error, and later 90-second worker and heartbeat
timeouts. The 184.095-second observation gap overlaps those failures; the
available evidence does not isolate provider latency from orchestration cost.

Atlas was correctly delivered at **124.916** (receipt 14). Cedar was delivered
at **270.265** (receipt 18), after deadline 240. There was no valid Dogwood
input request. Final canonical notes retained both operational receipts.

## Measurement findings and fixes

Both probes submitted all 16 original revision/recipient/key/status facts
correctly, but omitted every newly scored deadline/blocked_at field. Contract 8
asked for those keys in prose while its JSON example still showed the old
four-field schema. The 16/24 scores are preserved, but omissions cannot cleanly
establish forgetting or policy knowledge. **Contract 9 fixes the example schema**
and explicitly distinguishes numeric policies from unspecified null values.

Background schedules also continued into the probe. Peko's eight-call probe
allowance was exhausted with two local relay rejections, although the memory
POST was captured. **Contract 9 suspends native schedules after the watch and
post-watch topology snapshot**, recording this as a measurement intervention.
It does not rescue deadlines. These fixes have offline coverage; contract 9 has
not received another live run.

Usage remains incomplete across interrupted streams:

| Allowance/phase | Peko calls | OpenClaw calls |
|---|---:|---:|
| Setup | 6 | 0 |
| Owner/review conversations | 7 | 9 |
| Watch active | 22 | 9 |
| Watch idle | 13 | 9 |
| Probe | 8 | 7 |
| Total forwarded | 56 | 34 |
| Local rejections | 2 | 0 |
| Calls with complete usage | 55 | 31 |

Peko has one incomplete stream; OpenClaw has three. Known complete-call subsets
have reference costs **$0.0296556568** and **$0.0101430616** respectively. These
are **not full-run costs**. Full cost is null; native request counters are 55
and 31 against relay admission counts 56 and 34. Do not turn this into an
unqualified spend comparison or erase incomplete requests. Actual plan-credit
consumption was not measured.

## Validation and next step

Scores, diagnostics and usage totals were independently replayed from the
retained ledgers/call records. Owned runtime PIDs were confirmed stopped. The
runtime fix passed formatting, clippy, module/workspace gates, 2,751 local
library tests (3 ignored), and PR/merged Linux CI including shutdown tests.
Benchmark fixture/measurement checks pass offline (71 tests after contract 9
fixes). No extra model sampling was used to repair scores or probes.

Next, implement a common action boundary with explicit authorized preconditions,
stable action identities and durable idempotent receipts. Measure invalid
attempts separately from prevented external effects. Resolve or explicitly
bound interrupted-stream accounting before cost comparisons. Then test the
supervisor's organizational repair contribution with the same workers enabled
and disabled under a declared fault. Keep repeated samples and longer workloads
behind these stabilization gates.

Raw pilot ids:
`20261007T040424400259Z-responsibility-peko` and
`20261007T041026318767Z-responsibility-openclaw`.
Retained zero-call OpenClaw setup ids:
`20261007T040424334140Z-responsibility-openclaw` and
`20261007T040803710400Z-responsibility-openclaw`.
