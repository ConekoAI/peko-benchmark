# Peko prompt and cache investigation — 2026-10-06

The original responsibility pilot's extra Peko spend is concentrated in a few
scheduled requests. Source inspection also found two prompt defects: duplicated
session context and an omitted message cache breakpoint on ordinary text tails.
Both are fixed in [runtime PR #422](https://github.com/ConekoAI/peko-runtime/pull/422),
alongside initialization and principal-memory path clarifications.
These findings do not establish why MiMo missed particular cache entries or
establish a Peko/OpenClaw efficiency difference.
PR #422 merged as `1e84d66a8af8219d4242837317aa620e166d1334` after the final
head's Linux unit/shutdown and module/dependency boundary CI passed.

## Original paired sample, analyzed offline

The [original report](LIVE_PILOT_RESPONSIBILITY_MIMO_2026-10-06.md) remains the
paired behavioral result: both harnesses passed once. This investigation made
no new model calls to reconstruct that sample. Local retained report IDs:

- Peko: `20261006T051351457203Z-responsibility-peko`
- OpenClaw: `20261006T045817244103Z-responsibility-openclaw`

| Active-watch metric | Peko | OpenClaw |
|---|---:|---:|
| Calls | 12 | 12 |
| Uncached input tokens | 83,675 | 22,178 |
| Cache-read tokens | 367,104 | 198,336 |
| Cache-inclusive input tokens | 450,779 | 220,514 |
| Cache-read share of input | 81.44% | 89.94% |
| Calls with zero cache reads | 2 | 0 |
| PAYG reference USD | $0.01338191 | $0.00408054 |

Peko's first requests in three active turns (provider indices 23, 27 and 31)
accounted for 78,180 uncached tokens, **93.43% of active-watch uncached input**.
The first two were entirely uncached, contributing 70,367 tokens. The input
at first requests of Peko's five scheduled turns grew from 31,157 to 44,241
cache-inclusive tokens; OpenClaw's was approximately 16,000–22,000. Neither
retained original request bodies, so their exact wire prefixes cannot be
reconstructed after the fact.

Across Peko's retained sessions, 38 runtime-context hook messages contained
99,744 characters. Eleven included both `## Session context` and
`## session_context`, repeating the same section. These are text character
counts from native storage, not model token attribution. No equivalent
OpenClaw runtime-context extractor is claimed.

All USD here uses the profile's PAYG reference rates ($0.14/M uncached input,
$0.28/M output, $0.0028/M cache reads). **Actual Token Plan credits are unknown.**

## Fixes and their scope

The renderer treated `session_context` as both a built-in section and a custom
hook section. It now excludes that name from custom rendering. The regression
requires one context body and no duplicate custom heading, while retaining
existing section updates and retractions.

The Anthropic adapter flattened ordinary text messages to a JSON string, then
only attached the conversation breakpoint when the last message was already
a block array. With caching enabled it now converts the last plain-text message
to a single text block with `cache_control`. Earlier messages retain their
existing representation; `CacheRetention::None` still uses the plain string.
Default and one-hour retention, user and assistant tails, are covered. Tool-only
tails retain their existing behavior. The
[Anthropic protocol](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
documents explicit cache breakpoints on content blocks; MiMo's acceptance is
verified separately through native calls below. A breakpoint does not promise
a cache hit, and MiMo already returned cache reads before this repair.

A diagnostic genesis attempt exposed a separate reliability issue: the model
edited runtime-owned `boot_state` to the invalid value `ready`. The native
genesis brief now explicitly tells the model to leave this field unchanged;
the runtime marks successful genesis `organized`. This is prompt guidance,
not a new enforced filesystem or lifecycle boundary.

The bounded watch then exposed a memory-location blind spot. Filesystem tools
intentionally default to `<data>/workspaces`, while shared principal memory is
read from `<principal>/kb`. Placeholder-free role bodies received a generated
runtime section without the principal path. Native tool results show the owner
successfully wrote relative `kb/responsibilities.md` and `kb/MEMORY.md` under
`data/workspaces`; supervision searched the principal kb, found no commitments,
and spent multiple iterations rediscovering them. The generated stable runtime
section now states the principal workspace and knowledge-base paths and directs
shared-memory writes to absolute paths there. Tool path resolution is unchanged.
The existing bare-role regression now requires these paths and guidance.

## Diagnostic attempts

The attempts below are stabilization work. The watch uses the original seed
and five-minute scenario; the final path check is a smaller targeted diagnostic.
They are not extra independent paired samples.

`20261006T054413953463Z-responsibility-peko` used only the renderer repair
(`d338b940e186f652a8483d35bd5c1cfc9348a489`). All eight setup calls completed and
native/provider usage reconciled: 10,243 uncached input, 176,896 cache-read and
1,315 output tokens, $0.00229753 reference cost. Genesis then failed parsing
the model's invalid lifecycle edit; no watch started. Its wire profiles showed
only tool and system markers, confirming the missing text-tail breakpoint.
The tool catalog was 62,209 JSON bytes and system content 7,151 JSON bytes,
each stable across those eight requests. Native context duplication was zero.
This failed attempt is retained and is not counted as a successful pilot.

The marker/renderer verification is retained as
`20261006T055041023046Z-responsibility-peko`. Its native binaries include all
three earlier changes from `59abd31c2d284efd9651308588be1c57c716a61b`;
`210879de190d3eaadbe1cd53fb11e75a736ca04d` added documentation only. It used
`--profile-prompt`, seed 1, the same
`mimo-v2.6-flash` decoding policy, 60-second cadence, $0.10 reference ceiling,
and existing admission backstops. No extra continuation or rescue prompts
were introduced. **This diagnostic watch failed.**

| Watch result | Observation |
|---|---:|
| Completed obligations | 2/3 |
| On-time obligations | 1/3 |
| Missed deadlines | 2 |
| Atlas / Cedar delivery time | 226.994 / 227.013 seconds |
| Dogwood input request | Missing |
| Repeated / forbidden actions | 0 / 0 |
| Idle-window actions / native outbound attempts | 0 / 0 |
| Process restart | Verified |
| Human rescues / controller continuations | 0 / 0 |
| Memory probe | Missing after timeout; 0/16 scored |

The 300-second watch completed. Setup and conversations took approximately
518 seconds; the final probe exceeded the 900-second overall deadline.
Missing probe evidence is not proof that all memory facts were forgotten.
Provider responses were slower than the original paired sample, and the native
trace also shows the misplaced-memory search. This run does not isolate their
contributions to missed deadlines.

| Phase | Calls | Uncached input | Cache reads | Output | Reference USD |
|---|---:|---:|---:|---:|---:|
| Setup | 8 | 10,943 | 176,768 | 1,779 | $0.00252509 |
| Conversations | 19 | 77,720 | 416,192 | 3,842 | $0.01312190 |
| Active watch | 9 | 28,192 | 378,176 | 3,374 | $0.00595049 |
| Idle watch | 1 | 1,810 | 55,744 | 230 | $0.00047388 |
| Probe | 6, one incomplete | 38,797 observed | 202,752 observed | 1,417 observed | Unknown |

Forty-two completed requests account for 157,462 uncached input, 1,229,632
cache-read and 10,642 output tokens, and reconcile exactly with native assistant
and persisted quota token counters. A 43rd forwarded request was interrupted;
total consumption and total cost are unknown. The completed-accounting subset
prices to $0.02846741 reference USD; this is not the full attempt cost.
The scorer correctly rejects incomplete accounting. Both owned daemon epochs
were stopped. All 43 admitted profiles carried tool, system and message markers;
the tool/system profiles were stable at 62,209 / 7,151 JSON bytes. Native context
messages had zero duplicated session-context headings (43 messages, 93,063
characters). These repair checks passed despite the failed behavioral result.

The missing path is addressed in `7c705d24decff8de5edc8b1c00300f6d2ae4e527`.
`runner/memory_path_probe.py` separately runs native genesis with keepalive
disabled, one durable-note write, and one readback turn. It checks the actual
principal file, absence of a misplaced default-directory copy, exact readback,
and an absolute native `Read` call to that file. This uses a $0.03 reference cap
and 600-second timeout and is not a watch or comparative performance sample.
**The targeted check passed**, retained as
`20261006T061132437538Z-responsibility-memory-path-peko`: all four checks true,
no errors, nine calls, 17,427 uncached input, 178,816 cache-read and 1,402 output
tokens, $0.00333302 reference USD. Provider and native token/request counters
reconciled exactly. Offline inspection also confirmed the canonical `Read`
returned successfully. The owned daemon was stopped. Binaries were built with
the final runtime code at `7c705d24decff8de5edc8b1c00300f6d2ae4e527`:
CLI SHA-256 `a049e90450a36c475d5e4e2869326c062c22708f77c5b160d6c32bcf8a45eab0`;
daemon SHA-256 `bb502f1a4236f2a404185d4411bdc3204079777fad08d6924ca3c845b9838750`.
The full unattended scenario has not been rerun after this path correction.

The failed watch's finalizer preserved principal memory and transcripts, but
not `data/workspaces` Markdown. Its tool results still identify the misplaced
files and successful writes. The adapter now retains owned default-directory
Markdown as well, redacted and locally ignored, for future failure analysis.

## Profiling instrumentation and interpretation

`runner/prompt_profile.py` is opt-in. It observes the effective relay payload
without modifying it and saves tool/system/message JSON sizes, marker
locations, and run-local HMAC-SHA256 fingerprints. Its random key is never
saved. Raw prompts, tool names, text and headers are not included in these
profiles; existing native transcripts remain local and ignored by Git.

The profiler matches the best prior request with identical tool, system and
decoding fingerprints, allowing independent sessions to interleave. Prefix
counts describe **exact JSON message shapes**, after excluding cache markers.
String content and a typed text-block array remain different shapes. Moving
the marked tail into historical string content can therefore make the strict
prefix test false even when MiMo reports substantial cache reads. Same-role
history normalization can also change shapes between runs. These counts are
not tokenizer equivalence or proof of cache hits/misses; request metadata,
stream mode, HTTP headers and provider routing are outside this match.
JSON bytes cannot attribute tokens or costs to individual prompt components.

Reproduce the optional diagnostic under the
[normal native driver setup](RESPONSIBILITY_BENCHMARK.md#run-one-pilot), with
the built `PEKO_BIN` and configured provider key:

```bash
source profiles/mimo-v2.6-flash.sh
python3.12 runner/responsibility.py --driver peko --seed 1 --budget-usd .10 --profile-prompt
```

Analyze retained evidence without contacting a model:

```bash
python3.12 runner/profile_usage.py reports/<run-id>
python3.12 -m unittest discover -s tests
```

Run the targeted native memory-path diagnostic under the same provider profile:

```bash
python3.12 runner/memory_path_probe.py
```

Validation: 49 offline benchmark tests; runtime formatting and clippy with
warnings denied; 2,747 library tests passed (3 ignored); workspace dependency
and module boundary checks passed. Provider tests check the actual request
shape. The profiler tests cover privacy, unchanged payloads, interleaved
sessions, marker movement, parameter changes and incomplete usage accounting.

## Remaining context growth

`RuntimeContextState` is initialized anew for every engine run. Consequently,
each scheduled turn appends a full snapshot even when its sections are
unchanged; within-run delta rendering cannot prevent growth across runs.
The original watch appended roughly 7.8 KB of context at each new turn.
This is an identified design cost, not changed by the duplicate-section fix.

First repeat one unattended Peko watch after the memory-path correction.
The next optimization should restore trusted context state across runs only
when it corresponds to retained conversation history, and invalidate it after
compaction, truncation or relevant section changes. Inferring that state from
user-authored Markdown would not provide a trustworthy basis for suppression.
Measure context growth and cache reuse again after a separately tested change,
then resume paired seeds and longer runs. This diagnostic does not yet justify
a multi-day efficiency or architectural-value claim.
