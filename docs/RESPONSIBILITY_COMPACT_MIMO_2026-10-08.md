# Compact formation pilot — 2026-10-08 UTC

Both fresh MiMo v2.6 Flash attempts timed out in the first owner turn. Neither
registered an operational job or reached review. Native file, shell, fixture and
scheduler paths passed separate scripted probes. This pair does not establish
an unattended completion result or a Peko persistence advantage.

| Observation | Peko | OpenClaw |
|---|---|---|
| Native compact-profile probe | Passed, including truncation recovery | Passed |
| Real LLM calls in native probe | 0 | 0 |
| First owner turn | 180.010s, timeout | 182.042s, timeout |
| Provider requests | 18; last incomplete | 14; all upstream usage complete |
| Output-limited responses observed | 0 | 0 |
| Operational jobs registered | 0 | 0 |
| Canonical obligations retained | 0 | 4 initial owner facts |
| Worker retained | Partial, no entry point | Partial, no entry point |
| Post-run fictional fixture | 5/10; only no-action cases | 5/10; only no-action cases |
| Strict accounting gate | Failed | Failed |
| Watch, deadlines, restart, memory | Unmeasured | Unmeasured |

The [JSON evidence](RESPONSIBILITY_COMPACT_MIMO_2026-10-08.json) records frozen
source, binaries, raw report hashes, native probes, phase usage and limitations.
Earlier reports and this pair's raw results remain unchanged.

One serial attempt per harness used benchmark `fd1f7f1`, Peko build `cd161f60`
(merged as `9042a924`), disabled thinking, 4,096 max output tokens, seed 1,
180-second owner/review turns, a 900-second scenario ceiling and the unchanged
$0.05 reference operating allowance. Peko made seven native genesis requests;
OpenClaw's prepared setup made no LLM request. These costs are separated in
phase accounting, so total request counts are not equal-scope owner counts.

## What changed and what is verified

The [compact diagnostic](RESPONSIBILITY_COMPACT_FORMATION.md) supplies a small
fictional HTTP fixture rather than asking each model to write its own tests.
Neither live workspace receives a worker or accepted owner facts from the
controller. Review is restricted to owner decisions. Each model must author one
stdlib Python worker, pass the supplied fixture and register one recurring
native code job with the live URL and workspace. Supervision remains unarmed;
there is no watch, oracle feedback, controller continuation or retry.

Both scripted native probes used actual file tools and shell execution, passed
all ten fixture cases, registered the expected worker arguments and observed
an actual successful scheduled call to the inactive world without an LLM
request during the fire. These verify the sampled routes, not every advertised
tool or the model's ability to construct a working strategy. The first Peko
probe had a collector false negative: the checker searched nested JSON output
as plain text. Decoding that output fixed the checker; a regression test covers
the case. The initial report stays frozen and is not a failed native tool.

Merged [PR #433](https://github.com/ConekoAI/peko-runtime/pull/433) preserves
partial output and native results at an output limit, then allows at most two
normal continuations with smaller-response guidance. It raises no output,
quota or iteration limits, guesses no arguments and replays no successful call.
Empty billing-only assistant entries remain in JSONL and are omitted from
provider requests. A third capped response returns a typed error. The native
HTTP-streaming probe verified an empty Write's validation failure followed by a
corrected Write. The live pair recorded no `max_tokens` response, so it does
not measure this recovery's benefit. All 2,762 library tests and 105 benchmark
tests pass; formatting, clippy, boundaries and Linux CI pass. Three library
tests were ignored; Windows and integration CI tiers were skipped.

## What failed and why it can be attributed narrowly

Peko completed genesis, then used small shell writes to start a worker. Its
commitment table remained empty and it registered no code job. All 29 observed
wire tool intents matched persisted native execution and returned native
success results. This verifies dispatch; it does not certify shell-program
semantics. The 17 completed provider responses emitted only 4,268 output tokens
in total. Its ten completed owner responses occupied 55.679 seconds at the
relay. Request 18 reached the relay but had no recorded upstream HTTP headers,
termination reason or usage when the final report froze, about 152 seconds
after its recorded start. The owner turn hit its 180-second limit. This is an
unfinished upstream response, not evidence of truncation, a scheduler delay or
a missing tool path. Queueing, connection, prefill and generation time cannot
be separated with the current telemetry.

OpenClaw retained the four initial owner requirements and wrote worker pieces,
but did not finish the program or register a job. Its 14 upstream responses
occupied 180.825 seconds cumulatively, with per-response times from about 4.6
to 28.9 seconds despite outputs of only 84–482 tokens. The command timed out at
182.042 seconds; the final response was drained after client interruption.
Seventeen tool intents match natively. One completed mismatch is transcript
redaction: the persisted command docstring changes `read commitments` to
`*** commitments`. Restoring that single fragment from the retained worker
reproduces the wire argument hash exactly. The native result and authored file
corroborate execution. The other unresolved call is the final interrupted
command, which has no persisted native intent/result. These records do not
demonstrate argument substitution or a broken advertised command.

Both saved workers lack an entry point and end mid-construction. Separate
post-run audits against the pristine fictional fixture pass the five no-action
cases and fail all five cases requiring delivery, rejection handling,
reconciliation or blocked escalation. This is an incomplete-program finding,
not proof that a finished version would have those bugs. No feedback from these
audits was sent to either model, and the failed frozen scores remain failed.

## Accounting and next step

Known completed-call reference cost is at least
**$0.0142481080** for the pair. Peko's
unfinished request leaves its total unknown. OpenClaw's observed reference cost
is $0.0054643232; native request counts include an
aborted assistant entry while its token totals omit exactly the final drained
call's usage. Thus its token difference equals that call, but the generic
request-count reconciliation diagnostic does not match. Neither strict
accounting gate passes. Actual Token Plan credit deductions are separate.

The smaller contract prevented neither a stalled response nor cumulative
response time from exhausting a 180-second formation turn. The next controlled
step should record header/first-event timing and native interruption outcomes,
then checkpoint owner facts before worker construction and give formation an
explicit allowance suited to observed response times. Keep that allowance equal
across harnesses and report formation cost separately. Resume unattended
comparisons only after each harness has a validated, registered worker. There
is no basis here to blame Peko's persistent architecture or claim that prompt
engineering alone explains the result.
