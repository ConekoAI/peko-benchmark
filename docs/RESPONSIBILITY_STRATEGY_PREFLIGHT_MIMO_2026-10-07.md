# Offline preflight and native recovery pilot — 2026-10-07 UTC

Native workflow scheduling and recovery are functional on both harnesses. Both
fresh MiMo strategy attempts failed during setup, before the watch began. This
pair measures automation formation under a bounded setup allowance; it cannot
establish obligation completion, deadline reliability or a persistence advantage.

| Observation | Peko | OpenClaw |
|---|---|---|
| Scripted native recovery checks | 18/18 passed | 18/18 passed |
| Real LLM calls in recovery probes | 0 | 0 |
| Fresh strategy result | First owner turn timed out | Review turn timed out |
| Operational job registered | No | No |
| Authored code | No saved Python script | Python worker and offline tests |
| Watch began | No | No |
| Completion, deadlines, memory, restart | Unmeasured | Unmeasured |
| Provider requests in live attempt | 24, last incomplete | 33 |
| Wire/native tool intent matches | 49/49 | 39/42; three unresolved |

The [JSON evidence](RESPONSIBILITY_STRATEGY_PREFLIGHT_MIMO_2026-10-07.json)
pins source, binary, result and probe hashes, failures and accounting limits.
Original reports and the earlier strategy pair remain unchanged. Synthetic
fallback `missed_deadlines=3` is not three observed missed deadlines here.

## Contract and verified native paths

[Strategy contract 2](RESPONSIBILITY_STRATEGY_CHOICE.md) requires bounded offline
tests before registering or repairing generated code. Both harnesses receive
the same active/inactive, revision, cancellation, threshold, replay, rejection
and uncertain-receipt cases. Tests use fictional facts and mock HTTP. Supervisor
reviews may organize or repair jobs but cannot read the live world, perform
operational effects, force a job or wait for its next fire.

Each controller-authored recovery probe exercised native file tools, code-job
creation, three actual failures, persisted history inspection, code repair,
offline active/inactive/receipt checks, eligibility reset, restart and at least
two healthy **scheduled** fires. Healthy fires were never manually forced;
the scheduled code made no provider requests. These probes certify native
paths, not the model's ability to construct a strategy.

Peko disables a job after three failures. Re-enabling resets its failure budget
without changing next_run; replacing the job can change cadence. OpenClaw timer
failures led to a five-minute backoff. Enabling an already enabled job reset
its counter but left the delayed nextRunAtMs. Explicit disable followed by
enable/every reset the schedule and produced scheduled success after restart.
The saved capability reference now describes these exact reachable routes.

The probe exposed a real Peko tool defect: CronTrigger returned a UUID different
from the row later stored in CronHistory. [PR #431](https://github.com/ConekoAI/peko-runtime/pull/431)
reserves and persists the real run before returning; timer/manual admission
coalesces onto the same open row. It is merged, with red-before/green-after
identity coverage, 2,758 passing library tests, formatting, clippy, boundary
checks and CI. The corrected native probe verifies returned/history identity.
Earlier failed probes are retained and separated into collector errors,
timer-versus-manual fixture behavior and the real backoff-reset finding.

## Fresh model attempts

One serial attempt per harness used frozen benchmark `5049603`, runtime build
`e2a9086` (merged as `fb72cf8`), MiMo v2.6 Flash, thinking disabled, 4,096 max
output tokens, seed 1 and identical owner/review instructions. Each owner/review
turn had 180 seconds, with a 900-second scenario ceiling and the unchanged
$0.05 PAYG-reference operating allowance. No retries or additional seeds ran.

Peko wrote canonical requirements and proposed a ten-second workflow, then
spent much of setup examining SDK, role, environment, cron and session history.
It saved no operational script or job before the first owner turn timed out.
All 49 native tool intents preserved their wire arguments. A stale exact-text
Edit correctly returned an error and was retried. The final completed response
emitted an empty Write at exactly 4,096 output tokens; native validation rejected
the missing required arguments. The following provider request was interrupted.
Its 17 completed conversation responses occupied 173.341 seconds at the relay;
the empty Write alone took 51.749 seconds. Generation/response time contributed
heavily to the 180-second timeout, alongside the model's choice of work.

OpenClaw authored `ops/release_job.py` and an offline test file, accepted the
owner revision and timed out during review without registering an operational
job. Its last completed offline test invocation exited 1: replay-envelope,
rejection/no-effect and uncertain-receipt assertions failed. Earlier mocks also
treated a receipt dictionary as callable. Some tests were overprescriptive or
shared mutable state, so this is failed offline validation, not proof that every
failed assertion denotes a worker defect. Correct native errors identified
`sessionKey`, the automations action enum and `timeoutSeconds`; the model used
unsupported arguments rather than encountering substituted tool inputs.
OpenClaw's script/test writes took 57.640 and 53.244 seconds, and its two empty
writes took 43.073 and 50.971 seconds. These are response durations including
streaming, not isolated network latency. Neither sample reached scheduled
operational execution, so scheduler lateness cannot explain these setup failures.

Both traces contain direct owner/review GETs of the live world or receipts,
outside their organizational role. These violations remain failures. No
controller-created operational solution or continuation repaired either sample.

The collector initially retained code only in workflows/kb/scripts/root and
missed OpenClaw's ops directory. Initial native Write intents prove authorship,
but cleanup removed the final files after subsequent edits. Their final state
cannot be certified. Code retention now covers other workspace directories
with SDK, dependency, identity and credential exclusions; this fix does not
retroactively recover the lost files.

## Output limits and a provider-parser fault

Peko's empty Write and OpenClaw's two empty writes each coincided with exactly
4,096 output tokens. Historical relay logs did not retain the upstream stop
reason, so their exact termination remains unmeasured.

Two separately labelled direct API probes, each capped at 64 output tokens,
requested one oversized fictional Write and executed no native tool. MiMo's
Anthropic endpoint returned a tool_use block with input `{}`, no argument
deltas, and nested `max_tokens`; its OpenAI endpoint returned incomplete JSON
argument fragments and finish_reason `length`. This reproduces an output-limit
mechanism capable of producing empty tool inputs. It supports an explanation
for the observed pattern without proving the historical calls' exact cause.

Peko's Anthropic parser also ignored nested delta.stop_reason, returned usage
before considering termination, and emitted unconditional Stop at message_stop.
The [official streaming protocol](https://platform.claude.com/docs/en/build-with-claude/streaming)
places the reason in message_delta.delta, often beside usage. Merged
[PR #432](https://github.com/ConekoAI/peko-runtime/pull/432)
retains it independently until the terminal event, preserving Length/ToolUse
and isolating parser clones and new streams. It changes termination reporting;
the engine's tool-validation and retry policy remains unchanged. Upstream stop
reasons are now also captured in benchmark telemetry, with no inference from
token counts. The frozen pilot scores remain failed.
The regression failed before the fix; 239 provider tests and all 2,760 workspace
library tests pass (three ignored), with formatting, clippy, boundaries and Linux
CI passing. Windows and integration tiers were skipped. CLI/daemon rebuild
hashes and the merge commit are recorded separately from the frozen pilot build.
Future attribution also uses wire-based labels for missing required arguments.
The legacy `model_missing_required_argument` category in this frozen sample
describes the received fields and native rejection, not a proven model cause.

## Accounting and next experiment

Known completed-call reference cost for the pair is **at least $0.0370185592**.
Peko's last request did not finish or fully drain, so total billing is unknown.
OpenClaw controller usage is complete, but its native transcript omits the
aborted final call's usage; that exact call explains the accounting difference.
The strict usage-equality gates remain failed. Actual Token Plan credits and
the separate two protocol requests are not included in this cost floor.

The next experiment should isolate formation: one operational worker, one
small shared mock fixture and a narrowly scoped review, with formation time,
request count, output truncation and successful job registration reported
separately. Keep generated writes small enough to fit the common output cap.
First define explicit handling of truncated calls and test it offline; simply
raising timeouts would conflate construction cost with unattended reliability.
Only after both harnesses reliably register a validated native job should a
fresh watch compare the unchanged obligations and supervisory rhythm. Defer
additional seeds and multi-day conclusions until that gate is stable.
