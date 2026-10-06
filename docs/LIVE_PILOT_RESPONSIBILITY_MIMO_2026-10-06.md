# Peko / OpenClaw ongoing responsibility pilot — 2026-10-06

**Both completed pilots passed the same unattended responsibility scenario.**
Each fulfilled three obligations on time, preserved all 16 memory facts,
avoided repeated or forbidden deliveries, recovered after a process restart,
and remained quiet during idle periods. This is one completed seed per
harness with a five-minute watch, not multi-day evidence or evidence of a
Peko advantage. Setup failures are retained below; larger runs are deferred.

## Experiment

The [method and metric definitions](RESPONSIBILITY_BENCHMARK.md) and
[`pilot.toml`](../scenarios/responsibility/pilot.toml) specify the scenario.
Both received the same seeded responsibilities, owner revision/cancellation,
and a separate tentative review conversation. During the watch the controller
silently made dependencies ready, including a cancelled release and a duplicate
readiness signal. It restarted the owned native process at 35 seconds. It sent
no dependency messages, wake requests, manual cron triggers, or rescue prompts.
Two releases and one justified blocked-input request had to occur through the
shared HTTP action ledger; prose claims could not fulfil them.

Both used `mimo-v2.6-flash` through the owner's China Token Plan Anthropic
endpoint, with the same effective wire settings: `max_tokens=4096`, thinking
disabled, no explicit temperature and no fallback model. Every forwarded call
was checked. Each run had a $0.10 PAYG reference admission ceiling, 60-request,
30,000-output and 2-million-uncached-input backstops. Neither completed pilot
hit a limit. The relay held the real provider key; the native agents received
disposable local relay credentials.

Peko completed native genesis with a creator-defined purpose and configured a
60-second `responsibility-monitor` cron. OpenClaw completed native baseline
setup and LLM persona onboarding, then used its native 60-second heartbeat in
the owner task session with internal-only output. `BOOTSTRAP.md` was removed
before its task clock began. Native schedules and transcripts are retained;
these are different product prompt stacks despite a common task and decoding
policy. OpenClaw also retained its stock daily memory-promotion and weekly
skill-review schedules; neither was due during this watch.

## Behavioral results

| Metric | Peko | OpenClaw |
|---|---:|---:|
| Completed / on-time obligations | 3/3 | 3/3 |
| Missed deadlines | 0 | 0 |
| Stale / cancelled / premature / repeated actions | 0 each | 0 each |
| Retained memory facts | 16/16 | 16/16 |
| Justified input requests | 1 | 1 |
| Human rescue interventions | 0 | 0 |
| Native outbound messaging attempts during watch | 0 | 0 |
| Actions in idle windows | 0 | 0 |
| Controller continuation prompts during watch | 0 | 0 |
| Verified native process restart | Yes | Yes |
| Watch world reads / consecutive unchanged reads | 5 / 1 | 5 / 1 |
| Atlas delivery latency from actual readiness | 40.917 s | 33.799 s |
| Cedar delivery latency from actual readiness | 22.913 s | 7.580 s |

Dogwood's required input request arrived at 230.745 seconds in Peko and
217.314 seconds in OpenClaw, within its 180–240 second window. It remained
blocked; Birch remained cancelled. The memory probe checked actual delivery
receipts as well as the final owner requirements. Both supplied one accurate
report after the watch. Neither used the probe to deliver late work.

## Usage

All completed provider calls reconcile with native assistant usage records in
request count, uncached input, cache reads/writes, and output. Peko's persisted
quota counters also agree. Its native quota USD counter uses the configured
uncached-input/output pricing hint; the table below additionally prices cache
reads from the relay, so those USD fields are not identical.

| Counter, including setup and probe | Peko | OpenClaw |
|---|---:|---:|
| Model calls | 38 | 32 |
| Uncached input tokens | 167,851 | 74,235 |
| Cache-read tokens | 961,152 | 472,448 |
| Cache-creation tokens | 0 | 0 |
| Cache-inclusive input tokens | 1,129,003 | 546,683 |
| Output tokens | 6,301 | 5,316 |
| PAYG reference cost | $0.02795465 | $0.01320423 |

| Phase | Peko calls / reference USD | OpenClaw calls / reference USD |
|---|---:|---:|
| Setup | 7 / $0.00215629 | 4 / $0.00171041 |
| Owner and review conversations | 13 / $0.00840475 | 9 / $0.00285983 |
| Active watch | 12 / $0.01338191 | 12 / $0.00408054 |
| Idle watch | 4 / $0.00247693 | 5 / $0.00307968 |
| Memory probe | 2 / $0.00153476 | 2 / $0.00147378 |

Phase is assigned when a call starts, including calls spanning a boundary.
Reference rates are $0.14/M uncached input, $0.28/M output and $0.0028/M cache
reads, inherited from the explicit MiMo profile. **These USD values are not
Token Plan deductions; actual credits for this experiment have not been
provided.** Earlier user-reported credits are not reused here.

Peko's total reference cost was approximately 2.12 times OpenClaw's; its idle
reference cost was approximately 20% lower in this sample. There is one
completed seed, failed attempts may have warmed provider caches, scheduling
phases differ, and setup/native context differ. These observations do not
establish comparative efficiency. The larger Peko active-phase uncached input
is a useful prompt/cache diagnostic before expanding the experiment.

## Failures and fixes retained

All report IDs below are directories under local, gitignored `reports/`.
No pre-watch failure is counted as a completed watch or silently discarded.

| Report ID | Outcome | Observed calls | Reference USD |
|---|---|---:|---:|
| `20261006T045032698230Z-responsibility-peko` | Noninteractive shell lacked the API key; failed before any provider call | 0 | $0 |
| `20261006T045039653397Z-responsibility-peko` | Native genesis completed; owner assignment exceeded macOS's default Unix datagram send buffer | 8 | $0.00455899 |
| `20261006T045423225580Z-responsibility-openclaw` | Onboarding completed; first assignment repeatedly polled inactive world state and timed out before watch | 29, incomplete | Unknown |
| `20261006T045817244103Z-responsibility-openclaw` | Completed watch and probe; passed | 32 | $0.01320423 |
| `20261006T050439805663Z-responsibility-peko` | Assignment worked; successful daemon channel creation was decoded incorrectly and retried locally, causing a collision | 20 | $0.00781679 |
| `20261006T051351457203Z-responsibility-peko` | Completed watch and probe; passed; offline result recovery described below | 38 | $0.02795465 |

The failed OpenClaw attempt observed 25,149 uncached-input, 451,328 cache-read
and 3,334 output tokens. An in-flight call was aborted, so complete consumption
and cost are unknown. The common prompt was strengthened for **both** harnesses:
at most one world GET per turn, finish immediately when inactive, and tool
`yieldMs` is not a polling timer. Both completed watches used those instructions.

[Runtime PR #421](https://github.com/ConekoAI/peko-runtime/pull/421) fixes both
Peko CLI issues. The Unix datagram client now uses a larger send buffer, paired
with a daemon receive buffer. Channel commands explicitly decode their native
response payloads and only fall back locally when the daemon cannot be
connected; an error after connection no longer repeats a mutation. This PR
merged as `5713266e2123d2e688d194d475ba4f4c1a052b97` after the latest Linux unit
and boundary CI passed. Local validation passed formatting, clippy with warnings
denied, all 2,746 library tests (3 ignored), 126 CLI tests, dependency/module
boundary checks, and an isolated no-LLM channel CRUD smoke test. Regression
coverage includes a 58 KB native IPC request and channel response decoding.

Peko's completed live run then encountered a **benchmark postprocessing bug**:
the outbound audit parser treated a non-message JSONL audit row as an object.
All model work, probe, usage capture and native cleanup had already finished.
The parser was fixed and covered by a regression. `result.json` was regenerated
offline from the preserved action ledger, provider ledger, native transcripts,
persisted quota and saved source/configuration evidence. There were no further
LLM calls or changed stimuli. Exact final run wall time is unavailable; the
last reply was 485.919 seconds after the run-folder timestamp. OpenClaw's
measured total run wall time was 402.643 seconds; these are not comparable
timing measurements. The runner now saves a recovery record before scoring.

OpenClaw's native outbound audit was also added offline from retained canonical
transcripts. Its native schedule snapshot was captured read-only during the
watch, exporting only schedule tables; the final adapter captures schedules
through the CLI. The final adapter and audit additions were not rerun against
the provider. All **43 offline benchmark tests** passed after these repairs.

## Provenance and limits

Peko ran binaries built from `7307cbc01302975e238a17c524c3d034d03f6885`, the
final PR head whose code merged in #421. CLI SHA-256:
`e7b787bd7d0e6d2ec68a20e88c96532d73fc2ed477bde1288eb4c46054e1965b`;
daemon SHA-256:
`73669ddc5fa988e70e4084c9ead73eb3dbdc4258a0d128cc2f36d1f9195aaf46`.
Its run directory retains the runner source manifest from before the audit
repair. OpenClaw was npm release `2026.9.8` (`fc23bc8`), Node `v24.17.0`, entry
SHA-256 `aa8606ca0d62ff133ef5b7bd2323ec8ff3f8eb384404399cd5e742918d63b0a1`.
Both used seed 1, nonce `91b72265b1f5`, and the same scenario.

Raw reports retain command logs, world/action ledgers, usage-only provider
ledgers, native transcripts, durable notes and schedule evidence. They remain
local because transcripts contain model reasoning and internal state. No
provider key, vault, private identity keys or native database auth tables are
published. Both owned processes were stopped after their runs; no OS service
was registered.

The separate review conversation is an owner-forwarded tentative proposal,
not a test of an untrusted peer or permission enforcement. Quietness covers
the simulator ledger and native messaging tools during the watch, not proof
against arbitrary shell network I/O. Ordinary persistence and event-driven
control modes are implemented but not live validated. The scalable fixture
can run for real days, but a decisive experiment still needs more obligations,
mid-watch requirement changes, longer dependency chains, repeated restarts,
paired seeds and explicit mechanism ablations. This pilot establishes that
both native supervisory mechanisms can do the small unattended workload;
it does not isolate principal seeding or establish novelty.
