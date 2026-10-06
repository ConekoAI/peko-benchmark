# OpenClaw / MiMo continuity pilot — 2026-10-06

**OpenClaw passed the same seven-turn scenario and real process restart as
Peko.** The initial pilot and a final adapter-verification repetition both used
seed 1 and passed. These are two repetitions of one seeded scenario, not two
independent scenario variants. The scenario currently demonstrates parity on
event-driven continuity; it does not establish a Peko advantage or test
unattended keepalive.

## Configuration and evidence

- OpenClaw npm release **2026.9.8**, CLI source identifier `fc23bc8`;
  Node.js `v24.17.0`. Dedicated installation outside both repositories; no
  global CLI installation or OS daemon registration.
- Wire model `mimo-v2.6-flash`, using the owner's exact China Token Plan
  Anthropic endpoint: `https://token-plan-cn.xiaomimimo.com/anthropic`.
- Context window 1,048,576; output cap 8,192. Every captured request used the
  intended model and cap. No fallback models or unrelated provider keys.
- OpenClaw's default thinking resolved to `medium`. All ten requests sent
  `thinking: {type: "enabled", budget_tokens: 7168}`. Peko's previous pilot
  left thinking at the MiMo provider default. This difference is retained,
  not described as identical decoding settings.
- Fresh temporary home, native `setup --baseline`, default workspace files,
  default heartbeat cadence, one Gateway-owned conversation. The adapter
  passes only the current event, never future events or expected actions.
- Same unchanged scenario, contract and deterministic grader; seed 1,
  600-second scenario allowance, $10 reference ceiling, 100-request,
  2-million uncached-input and 50,000-output admission caps. These are checked
  between provider calls and can overshoot by in-flight calls; they do not
  represent subscription credit limits.

Artifacts: `reports/20261006T034059947532Z-continuity-openclaw/run1/`.
They include the observations, final result, command and Gateway logs,
usage-only provider call ledger, native transcript exports and agent-written
workspace notes. Native SQLite transcript records were exported losslessly,
including one compressed record, without copying database auth tables.
Raw artifacts remain local and gitignored.

The loopback relay forwards request bodies unchanged to MiMo. The real key
stays in the controller; the Gateway gets a disposable relay credential. The
relay captures model/decoding fields and cumulative Anthropic usage, without
logging upstream credentials or prompt bodies. This remains a same-OS-account
benchmark, not adversarial isolation.

## Results

| Metric | OpenClaw pilot | Peko fix-verification pilot |
|---|---:|---:|
| Correct turns | 7/7 | 7/7 |
| Eligible delivery | Exactly once, revised recipient/revision | Exactly once, revised recipient/revision |
| Forbidden/stale/cancelled/duplicate/premature actions | 0 each | 0 each |
| Protocol errors | 0 | 0 |
| Verified process restart | Yes; clean SIGINT, exit 0 | Yes; clean SIGINT |
| Restart wall time, including startup | 6.331 s | 4.984 s |
| Eligible-turn response latency | 10.290 s | 14.148 s |
| Total run wall time, including setup/cleanup | 70.358 s | 313.033 s |
| Recorded model calls, including setup/background activity | 10 | 22 |
| Uncached input tokens | 21,355 | 80,635 |
| Cache-read tokens | 133,504 | 470,016 |
| Cache-creation tokens | 0 | 0 |
| Cache-inclusive input tokens | 154,859 | 550,651 |
| Output tokens, including thinking | 1,091 | 6,853 |
| Pay-as-you-go reference cost | $0.00366899 | $0.01452378 |

Peko reference: [fix verification](LIVE_PILOT_MIMO_FIX_VERIFICATION_2026-10-05.md).
The provider ledger's ten completed calls agree with all ten native assistant
usage records in every token field. The final provider ledger is unchanged
after Gateway shutdown, so no late call was omitted from this run's totals.
The report's usage reconciliation was added after the run by reading the
preserved native database; subsequent runs produce it directly in the adapter.

OpenClaw wrote `release-commitments.md`, revised its recipient and revision,
marked the second commitment cancelled, and recorded the first as delivered.
The scorer uses actual final JSON actions, independently of those notes.

## What the comparison supports

Both runtimes correctly carried the obligations through revision, distraction,
restart, cancellation and a duplicate event. An existing persistent assistant
can pass this scenario without reproducing Peko's principal architecture.

OpenClaw's observed total usage was lower in this sample. The totals include
each runtime's setup, but the initialization paths differ: OpenClaw baseline
setup created configuration/workspace files without a separate LLM genesis
turn. Its conversational persona bootstrap remained unfinished (`BOOTSTRAP.md`
still existed). Peko completed its default genesis before the events. Prompt,
tool surfaces and thinking settings also differ. These numbers are useful
observations of the two selected configurations, not a controlled efficiency
estimate or an attribution to any one mechanism.

The native Gateway logged unavailable semantic embeddings and skipped two
bundled browser/canvas skill symlinks under its filesystem guard. Filesystem
commitment storage worked. This run does not evaluate semantic recall or those
skills. Default heartbeat was enabled, but the short run does not demonstrate
unattended work or comparative supervision quality.

USD values use the same profile's published reference rates, including cache
reads. Actual Token Plan credits for this run have not been supplied. The
owner's earlier 16,859,564-credit measurement belongs to the initial Peko pilot
session and is not reused as an OpenClaw cost.

Next: test a controller-owned dependency change without a new user message,
then paired seeds and mechanism ablations. For strict decoding comparisons,
first align effective wire thinking settings across both adapters.

## Final adapter verification

The final adapter was rerun after adding automatic Gateway drain, native
compressed-transcript export and usage reconciliation. All seven turns passed,
with zero forbidden actions or protocol errors and a clean SIGINT restart.
Artifact directory: `reports/20261006T034724310795Z-continuity-openclaw/run1/`.

| Counter | Provider ledger | Native transcript |
|---|---:|---:|
| Calls | 10 | 10 |
| Uncached input | 28,792 | 28,792 |
| Cache reads | 127,680 | 127,680 |
| Cache writes | 0 | 0 |
| Output | 1,351 | 1,351 |

Cache-inclusive input was 156,472 tokens; reference cost $0.00476666. Total
wall time was 62.678 seconds, and eligible-turn latency was 8.847 seconds.
Persona bootstrap remained unfinished in this repetition as well. Both runs
are retained; neither is selectively substituted for the other in the table
above. Actual subscription credits remain unknown.

## Reproduce

```bash
sh harnesses/lib/openclaw_install.sh
export PEKO_API_KEY="$MIMO_API_KEY"
source profiles/mimo-v2.6-flash.sh
source profiles/openclaw-mimo-v2.6-flash.sh
python3.12 runner/continuity.py --driver openclaw --reps 1 --seed 1 --budget-usd 10
```

`OPENCLAW_ENTRY` can point to another dedicated installation. The adapter
creates and removes its own home, runs a foreground Gateway on an ephemeral
loopback port, and signals only its owned process. No messaging channel is
connected and no real delivery is sent. Native setup validation and all 31
offline benchmark tests passed. The relay's unchanged-body forwarding,
cumulative-usage accounting, budget/model admission, and auth-free compressed
transcript export have offline regression coverage.

OpenClaw entry SHA-256:
`aa8606ca0d62ff133ef5b7bd2323ec8ff3f8eb384404399cd5e742918d63b0a1`.
Installation lock SHA-256:
`f0aaf18317523f89b3de38599126fdf530f1f570992503320b75bd4850be4263`.
The npm package integrity is retained in the run's `installation.json`.

Relevant upstream documentation: [custom providers](https://docs.openclaw.ai/gateway/config-tools/custom-providers),
[agent CLI](https://docs.openclaw.ai/cli/agent),
[MiMo's native OpenAI-compatible integration](https://docs.openclaw.ai/providers/xiaomi).
This pilot uses the custom Anthropic route to match Peko's transport.
