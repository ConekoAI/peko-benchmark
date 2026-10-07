# Native tool and path audit — 2026-10-07

The scripted provider native smoke checks passed **14/14 for Peko and 14/14 for
OpenClaw**, with **zero real LLM calls**. This is interface evidence, not a model
benchmark result or evidence of autonomous reliability.

| Surface | Peko | OpenClaw |
|---|---|---|
| Absolute canonical file read | Passed | Passed |
| Relative canonical file read | Expected failure under runtime workspaces | Passed under configured agent workspace |
| Native write/edit/read-after-edit | Passed | Passed with advertised `edits` array |
| Shell cwd and simulator GET/POST | Passed | Passed |
| Distinct persistent worker session: file + HTTP dispatch | Passed; native Agent child | Passed; custom native session |
| Common service commit, replay, conflict, rejected precondition | Passed | Passed |
| Durable receipt lookup; one effect despite replay | Passed | Passed |

Peko's default `Read`/`Write`/`Edit`/`Bash` directory is `<data>/workspaces`;
principal KB files live under the principal workspace. Prior benchmark guidance
calling `kb/...` relative to the principal workspace was misleading. Contract 10
requires absolute paths anchored to runtime-advertised principal workspace/KB.
The earlier live pilot used successful absolute reads, so this finding alone
does not explain its missed Cedar deadline.

Peko's CronCreate description and `tool` parameter promise no LLM cost for fixed
scheduled tool calls while naming Agent as an example. Agent can invoke models.
[Runtime PR #426](https://github.com/ConekoAI/peko-runtime/pull/426), now merged,
corrects that advertised cost promise to distinguish fixed dispatch from model
calls performed by the invoked tool.

The historical Cedar trace saved `Edit` with shell-command arguments and a
missing-fields error. The original provider tool response was not captured.
It remains **historically unresolved between model intent and any upstream/native
mapping issue**. New reports record value-free provider catalog/call/result
structure and compare it with saved native intent. A correctly advertised call
with missing required keys is classified as a model choice only when that
intent and the native outcome match. Valid-looking calls with errors and
unmatched/truncated calls require investigation. Conditional constraints and
all other advertised tools remain outside this smoke coverage.

Preparation errors found during this audit were retained, not counted as model
failures: the first scripted Peko Agent call omitted its required role; the first
OpenClaw fixture used ids that its provider adapter normalized; a later edit
probe used a supported legacy shape absent from the current advertised schema;
and a transcript scanner mistook a string audit event for a message object.
The corrected probes verify the advertised schema and distinct native worker
session. No live-model tokens were spent on these fixture repairs.

The common service checks only present public state and caller-declared
preconditions. Hidden owner policy is never injected into it. Durable SQLite
receipts/idempotency prevent repeated effects while retaining all attempts for
grading. A wrongly supplied blocked threshold, recipient or cancellation can
still produce an invalid effect. Guarded and raw runs answer different questions
and must be reported separately.

Offline validation: **81 tests passed**, including concurrent retries, service
reopen, conflicting keys, schema/precondition rejection, attempt/effect grading,
provider/native attribution and upstream accounting after downstream disconnect.
Scripted reports and binary hashes are summarized in
[the JSON evidence](RESPONSIBILITY_SURFACE_AUDIT_2026-10-07.json). Probe source and
semantics are in [the execution protocol](RESPONSIBILITY_EXECUTION_PROTOCOL.md).
Native scheduling cadence and restart behavior remain separate live-test gates.

Subsequent live concurrent-stream evidence found a real runtime parser bug,
which these sequential surface probes did not cover. The fix and one focused
confirmation are recorded in the
[guarded pilot report](RESPONSIBILITY_GUARDED_MIMO_2026-10-07.md).
