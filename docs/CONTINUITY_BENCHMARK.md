# Peko continuity benchmark

The hypothesis to test is: **a principal reliably carries responsibilities across
turns and interruptions, with less repeated instruction and acceptable spend.**
Measure observable outcomes before attributing them to identity, seeding,
knowledge, or keepalive. Existing coding tasks remain the capability baseline.

The [first live MiMo pilot](LIVE_PILOT_MIMO_2026-10-05.md) passed one completed
scenario and exposed initialization latency and quota persistence findings.
The [runtime fix verification](LIVE_PILOT_MIMO_FIX_VERIFICATION_2026-10-05.md)
passed with complete quota retention and clean signal shutdown.
The [OpenClaw pilot](LIVE_PILOT_OPENCLAW_MIMO_2026-10-06.md) passed the same
scenario/model/seed with complete native/provider usage agreement. The two
selected configurations currently show parity on the scored outcomes.

## 1. First runnable scenario: changed commitment

`scenarios/continuity/changed-commitment.toml` contains seven agent turns and one
controller-owned process restart:

1. Accept two conditional release commitments; neither dependency is ready.
2. Receive unrelated information containing distracting revision/recipient values.
3. Change one commitment's revision and recipient; cancel the other commitment.
4. Restart the daemon while preserving its principal and on-disk state.
5. Receive a dependency-ready event without repeating the commitment.
6. Receive the cancelled project's dependency-ready event.
7. Receive a duplicate of the first dependency-ready event.
8. Receive an event with no changed state.

There must be exactly one delivery: the revised commitment, to its current
recipient, at step 5. Early, stale, cancelled, duplicate, or unrelated deliveries
fail the scenario. Doing nothing throughout also fails.

Project names, revisions, recipients, and delivery keys vary deterministically
with the repetition seed. Future events and expected actions stay in the
controller; the adapter receives only the current message. Repetitions use new
isolated principals, not a previously trained-up workspace.

The simulated environment treats each final JSON action as a delivery request:

```json
{"actions": [{"kind": "send_release", "project": "release-id", "revision": "r2",
              "recipient": "recipient@example.invalid", "delivery_key": "delivery-id"}]}
```

`{"actions": []}` requests no external action. The runner records every request,
including duplicates. No real email or messaging is sent. Claims such as "done"
are not delivery evidence. Malformed responses are protocol failures, including
on turns that require no action. The output contract is repeated per event;
the actual obligations are not repeated.

This is an **event-driven continuity pilot**. The restart occurs between completed
turns; it does not test recovery of an in-flight side effect. It does not yet test
cross-peer memory, compaction, unattended scheduled work, or seven-day behavior.
The live Peko adapter leaves default genesis/keepalive behavior enabled and
captures principal-wide counters. It cannot yet attribute cost to individual
background turns.

Genesis uses the CLI's standard 300-second wait within the scenario's 600-second
wall-clock allowance. Setup timeouts remain in the report history; changing the
wait budget while validating the adapter does not erase earlier attempts.

## 2. Metrics and pass gates

Report the vector below. Do not collapse it into an arbitrary weighted score:
an agent that completes the requested delivery and sends unwanted releases is
not reliable, and an agent that never acts is not useful.

| Metric | Definition | Direction / gate |
|---|---|---|
| Obligation completion rate | Eligible, exact deliveries / required deliveries (one in this pilot) | 1.0 required |
| Forbidden action count | Delivery requests not authorized by that event's oracle, including extras | 0 required |
| Stale delivery count | Requests using obsolete revision/recipient after the update | 0 required |
| Cancelled action count | Requests for the cancelled project after cancellation | 0 required |
| Duplicate delivery count | Repeated project + revision + recipient, even with a changed delivery key | 0 required |
| Premature delivery count | Requests during acceptance/distraction/revision, before any build-green event | 0 required |
| Recovery success | Exact eligible delivery after a verified process restart | true required |
| Correct turn rate | Exact action arrays / all seven expected agent turns | Diagnostic; a silent agent scores 6/7 but fails completion |
| Protocol error count | Missing/malformed final JSON action replies | 0 required |
| Response latency | Wall time of the successful dependency-ready turn | Diagnostic; null if unsuccessful |
| Principal input/output/cache tokens and requests | Runtime quota snapshot after the scenario, including initialization/background activity | Report separately |
| Estimated USD per completed obligation | Reconciled recorded-call reference cost / completed obligations | null if pricing/usage incomplete or none completed |

The full trace must contain all steps in order and a verified restart. Driver
errors, timeout, or cleanup errors fail the run, including when the last useful
action happened to succeed. Missing telemetry stays null; it is never called zero.
The adapter reconciles final quota counters against persisted assistant usage;
the live pilot found that a forced restart can lose pre-restart quota counters.
Session usage is cache-inclusive; the quota snapshot's wire input is separate
from its cache counters. Preserve both views. Cost is a reference estimate,
not billed spend. When cache pricing is absent, full cost remains unknown.
The USD quota can overshoot by an in-flight call; request and
token caps additionally bound the pilot. Validate hints before interpreting cost.

## 3. Run it

Python 3.11+ and its standard library are sufficient. On hosts where `python3`
is 3.9, use an installed `python3.12`; no Python packages are needed.

```bash
# Grader validation: no model, daemon, keychain, or credentials.
python3.12 -m unittest discover -s tests -v
python3.12 runner/continuity.py --driver oracle --reps 3
python3.12 runner/continuity.py --driver empty  # expected nonzero / failed obligation
```

Oracle and empty runs are labeled `grader_self_test`. They test the scorer and
reporting; never include them in capability pass rates. Mutation tests cover
stale, cancelled, early, duplicate, missing, reordered, malformed, and unverified
restart traces.

For a live pilot, build **both** `peko` and `peko-daemon` from the same runtime
checkout. Set `PEKO_BIN`, `PEKO_API_KEY`, `PEKO_API_FORMAT`, `PEKO_BASE_URL`,
`PEKO_MODEL_NAME`, and `PEKO_MODEL_ID` to the intended binary and model. Supply
`PEKO_MODEL_SPEC` as a JSON capability descriptor with both pricing rates;
`PEKO_CONTEXT_WINDOW`, `PEKO_MAX_OUTPUT_TOKENS`, `PEKO_MODEL_COMPAT`, and
`PEKO_CACHE_READ_USD_PER_MILLION` are optional.
Model templates are retired in the current runtime. Then:

```bash
python3.12 runner/continuity.py --driver peko --reps 1 --seed 1 --budget-usd 1
```

For the owner-authorized MiMo Token Plan pilot:

```bash
export PEKO_BIN=/absolute/path/to/peko-runtime/target/debug/peko
export PEKO_API_KEY="$MIMO_API_KEY"
source profiles/mimo-v2.6-flash.sh
python3.12 runner/continuity.py --driver peko --reps 1 --seed 1 --budget-usd 10
```

The profile uses the China Anthropic endpoint and caps output at 8,192 tokens
per call. MiMo defaults thinking to enabled when the field is omitted; the
pilot leaves that provider default in place. See the [Anthropic API docs](https://mimo.mi.com/docs/en-US/api/chat/anthropic-api).
Its $0.14 input / $0.28 output per million rates are public
[pay-as-you-go reference prices](https://mimo.mi.com/models/en-US/mimo-v2.6-flash),
**not subscription charges**. Peko's two-rate hint cannot express the cache-hit
discount. Keep raw cache counters and compare actual credit deduction in the
owner's dashboard; do not interpret the USD ceiling as a plan-credit ceiling.

`--budget-usd` is per repetition and required for live runs. The adapter refuses
models without both pricing rates before any LLM call. It also seeds caps of
100 requests, 2 million input tokens, and 50,000 output tokens. Each repetition
uses a fresh short-path temp home, passphrase vault (`PEKO_UNLOCK_METHOD=passphrase`),
catalog, principal, and daemon. Only that isolated daemon's PID is signaled;
there is no global process-name cleanup. Two binary hashes and the model
configuration are recorded. Genesis must succeed before events begin.

Artifacts under `reports/<timestamp>-continuity-<driver>/` include per-run
`scenario.json`, `observations.jsonl`, `result.json`, model configuration, native
command logs, per-process daemon logs, persisted JSONL conversation/audit traces and quota
snapshot and `usage-reconciliation.json`, plus aggregate `summary.json` and
`summary.md`. API keys and
passphrases are redacted from command logs. The adapter never receives the
scenario/oracle file path. As with the existing local harness, agents run under
the same OS account: this is not an adversarial isolation benchmark.

## 4. Evidence ladder and comparison plan

The OpenClaw driver is now implemented. Install the pinned release with
`sh harnesses/lib/openclaw_install.sh`, export `PEKO_API_KEY`, source both
`profiles/mimo-v2.6-flash.sh` and `profiles/openclaw-mimo-v2.6-flash.sh`, then run
`python3.12 runner/continuity.py --driver openclaw --reps 1 --seed 1 --budget-usd 10`.
It uses an isolated native Gateway with default workspace bootstrap and
heartbeat, a stable conversation across a process restart, and an unchanged-body
Anthropic relay to the same MiMo endpoint. The relay enforces admission caps
between calls and records effective wire settings and usage. It drains the
Gateway before final accounting and reconciles usage with native transcripts.
Transcript exports omit credential tables. Full persona onboarding and effective
thinking settings differ from the initial Peko configuration; see the report.

| Stage | Work | Decision it supports |
|---|---|---|
| Now | One live pilot; inspect every reply and failure | Is the scenario and adapter usable? |
| Next | At least 10 paired seeds on one pinned model/configuration, repeat on a second model | Does continuity hold consistently, and is it model-dependent? |
| Mechanism comparison | Implement the conditions below; use identical events and budgets | Which Peko mechanism adds measurable benefit? |
| Scheduled autonomy | Add external state changes followed by no human/event prompt | Does supervision find and complete work on its own? |
| Soak | 24 hours, then seven days with interruptions and changing goals | Is ongoing responsibility economical and stable? |

Ten seeds are an initial estimate, not a significance guarantee. Report sample
counts and confidence intervals; expand the sample when uncertainty could
change the decision. Keep failed runs in denominators. Do not selectively rerun
bad seeds without retaining the original results.

Further comparison conditions (not implemented by the current pilot):

- Ordinary harness with persisted conversation, the same model/tools, and replay
  after restart. This is the credible baseline; a deliberately forgetful agent
  is only a negative control.
- Peko with event-driven continuation and no periodic supervisory turns.
- Peko with its default supervisory rhythm.
- Peko with default initialization versus a minimal deterministic scaffold,
  holding available tools and task information constant.
- For cross-session scenarios, shared principal knowledge enabled versus
  conversation persistence alone. This first same-session scenario cannot
  establish the incremental value of the knowledge base.

Add one mechanism at a time. Include setup/initialization cost in total spend;
report marginal task cost separately once attribution is available. Record model,
provider, decoding/thinking settings, context window, cache accounting, binary
versions, scenario seed, and budget. The current adapter records the model catalog
configuration, pricing, and binary hashes; effective per-call decoding-setting
capture is a follow-up.
The OpenClaw adapter permits external comparisons, but the initial single-seed
pilot does not establish cross-harness superiority.

## 5. Next scenarios

| Scenario | Observable outcome | Additional metrics |
|---|---|---|
| Scheduled dependency watch | A runner-owned file changes while no message is sent; agent acts by the deadline | Deadline completion, idle requests/cost, unsolicited notifications |
| Cross-peer commitment | One conversation learns a fact; another needs it without rebriefing | Correct recall, prohibited disclosure, repeated human instructions |
| Compaction continuity | Force compaction between update and dependency readiness | Constraint retention and recovery success |
| Interrupted side effect | Interrupt around action acceptance; restart and replay the event | Missing/duplicate effects, verified idempotency |
| Genesis usefulness | Initialize, then grade navigation and first useful task | Setup success/time/cost, first-task completion; no prose-quality judge |

For scheduled autonomy, the controller must own the clock, external state and
action ledger. An agent's statement that it woke or completed work is not proof.
Count all interventions, including corrective prompts. Introduce longer gaps
only after the short controlled cases pass; more wall time alone is not evidence
of more autonomy.
