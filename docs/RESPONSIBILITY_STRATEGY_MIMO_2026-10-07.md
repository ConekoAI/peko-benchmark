# Native automation strategy pilot — 2026-10-07

One MiMo Flash attempt per harness failed the full gate. Peko did not finish
constructing automation before the first owner turn timed out. OpenClaw authored
code and completed the watch, but its scheduled jobs crashed; supervisory repair
produced only one delivery. This does not demonstrate that workflows are an
ineffective strategy, or that either harness has a persistent-agent advantage.

The native surfaces were tested separately before inference. Runtime
[PR #429](https://github.com/ConekoAI/peko-runtime/pull/429) fixed missing
principal-name context in conversational/spawned/resumed Workflow execution.
Its regression failed before the fix, then passed; all 2,757 library tests,
formatting, clippy, boundaries and CI passed. Native Peko and OpenClaw probes
then verified code execution, recurring and one-shot dispatch, process restart,
history collection and measurement isolation with zero real LLM calls. Code
fires made zero model requests. Observed one-shot delays were 2.056s for Peko
and 0.058s for OpenClaw; these single observations are not precision guarantees.

Two OpenClaw probe failures remain retained: the history CLI required a job id,
and HTTP readiness preceded native heartbeat declaration reconciliation. The
runner now collects paginated `cron.runs` with `scope=all` and waits for the
configured heartbeat before starting the watch. The corrected probe passes.
These were runner/fixture faults, not model failures. All 97 benchmark tests pass.

## Experiment and results

This separate [strategy-choice contract](RESPONSIBILITY_STRATEGY_CHOICE.md)
permits model-authored code, chosen cadence and native one-shots. It supplies
empty shared notes and organizational supervision, without an operational
solution or hidden obligation facts. Original fixed-worker contract 11 results
are unchanged. Both live runs used benchmark `af35ef7`, the same owner/review
messages, seed 1, guarded action service, MiMo v2.6 Flash, thinking disabled,
4096 max output and no fallback model. They ran serially.

Each harness had a $0.05 PAYG-reference / 60-request / 30k-output operating
allowance, plus $0.01 / 8-request / 6k-output for the memory probe. The total
scenario timeout was 900s, individual owner turns were bounded at 180s, and the
intended watch was 300s with a restart scheduled at 35s. Code generation and
genesis cost remain included. Actual Token Plan deductions are unknown.

| Measure | Peko | OpenClaw |
|---|---:|---:|
| Full gate | Fail: setup incomplete | Fail |
| Watch completed | No | Yes |
| Obligations completed/on time | Unmeasured | 1/3 |
| Missed deadlines in an observed watch | Unmeasured | 2 |
| Memory facts | Unmeasured | 23/24 |
| Committed operational effects | 0 | 1 |
| Repeated/forbidden effects | Unmeasured | 0/0 |
| Quiet-window effects | Unmeasured | 0 |
| Receipt log retained committed receipt ids | Unmeasured | 0/1 |
| Native process restart | Unmeasured | Verified |
| Wire/native intent preserved | 27/28 | 48/50 |
| Controller/native transcript usage equality | Fail | Fail |
| Provider calls | 18 | 37 |
| PAYG reference cost | $0.0112868728 | $0.0199562832 |

The machine scorer emits synthetic zeros/missed deadlines when Peko never
starts the watch. Those must not be presented as three observed execution
failures or zero memory competence. Neither sample received a human intervention
or controller continuation. The [JSON evidence](RESPONSIBILITY_STRATEGY_MIMO_2026-10-07.json)
pins result/source/binary hashes, phase usage, native probes and score gates.

## Peko: setup failure with a real surface defect

Peko used five genesis calls and thirteen owner-conversation calls. It repeatedly
read roles, the SDK and memory, then searched session history instead of promptly
building an operational job. The owner turn hit the 180s command limit. It wrote
initial commitments, but no native operational job or retained script existed
when cleanup finished. Revisions, conflicting review and the watch never ran.

The trace contains a concrete runtime defect: `session list` advertised the
trunk as `sess:/<trunk UUID>`, and `session history` rejected that exact address
because the resolver interpreted the UUID as a child slug. The tool description
explicitly told callers to reuse listed paths. This is not a fabricated model
argument or an unreachable external service. Later history calls returned the
owner facts; those facts also existed in the original persisted user message.
Thus the bad address contributed friction, but this sample cannot establish
that it alone caused the extended exploration or timeout.

Retrieving history with tool results expanded the serialized message payload
from 14,727 bytes on the first owner request to 179,877 bytes on call 17; that
response took 39.406s. This is concrete context-growth and response-duration
evidence, not proof of model-only latency or a keepalive architectural failure.

Twenty-six native tool calls succeeded, one returned that addressing error,
and a final provider-issued Write remained unresolved after interruption. The
provider/native token difference equals call 18 (809 uncached input, 62,976
cache reads, 2,365 output); the persisted quota counter includes all 18 calls,
while assistant transcripts contain 17. The strict transcript-equality gate
remains failed. No argument substitution was observed among joined calls.

The observed trunk-address defect is fixed in
[PR #430](https://github.com/ConekoAI/peko-runtime/pull/430) with a real SessionTool
list → history/status/scoped-list regression from a child caller, reproduced
failing before the change and passing afterward. All 2,758 library tests,
formatting, clippy, boundary checks and CI pass; the PR is merged. The display form is
the resolver's existing `sess:/`; mutation validation remains unchanged.
The rebuilt runtime also passes 22/22 scripted native automation checks,
including reuse of the listed trunk address from a conversational child,
Workflow SDK callbacks, recurring/one-shot jobs, restart and probe isolation;
this confirmation spends zero real LLM calls.
This fix is subsequent to the frozen live sample and does not improve
its score retroactively. Legacy non-trunk slugless display fallbacks still need
a separate addressability audit.

## OpenClaw: generated-code failure and incomplete repair

The model created 5s and 10s recurring command jobs invoking the same Python
script with a filesystem lock. It preserved Atlas r2 and Birch's cancellation
against the reviewer. Its inactive-watch test returned before parsing canonical
requirements, so that test missed this active-path defect:

```python
start, end = txt.find("```json"), txt.find("```", start+7) if "```json" in txt else -1
```

Python evaluates the right-hand side before assigning `start`. Native scheduled
execution correctly reported `UnboundLocalError`; six watch invocations failed
with the traceback. This is an authored program bug, not a broken Python tool.
After three failures each native job had a five-minute retry delay, longer than
the remaining watch. Registration/execution evidence is present, but there was
**no successful chosen native operational invocation during the watch**.

The organizational heartbeat inspected failures, fixed the parser and removed
the duplicate 10s job. It directly invoked Python at 117.740s, which committed
Atlas at 117.742s, before the 160s deadline. That effect came from the supervisor's
direct script execution, outside the intended organizational role; it cannot
count as proof of healthy recurring task execution. It invoked Python again at
134.534s, before Cedar became ready at 150s and Dogwood's 180s threshold.

The remaining job retained its failure backoff: its next run was about 395.428s,
past both 240s deadlines and the 300s watch. The supervisor did not restore that
schedule, spent additional calls inspecting it and hit its 90s native timeout.
The next heartbeat was skipped with `requests-in-flight`. Cedar and Dogwood
received no effects. Code repair alone did not restore the operational lifecycle.

Receipt logging stored the exact attempted envelope and HTTP outcome but omitted
receipt id 1 from the required append-only receipt log; the receipt existed in
commitment state instead. The script's reconciliation reads `delivery_key`/`key`
where the service returns `action_key`, and its compact JSON log conflicts with
its space-sensitive fallback parser. Those are additional recovery defects,
not exercised uncertain-write guarantees. The memory probe incorrectly mapped
Dogwood's deadline to null, giving 23/24 facts. The script also unconditionally
rewrites `updated_at` on successful active polls; quiet messaging scores do not
certify an absence of idle disk work.

There were 23 conversation calls, 11 watch repair calls and three probe calls.
Call 34's downstream connection was interrupted after the heartbeat timeout;
its token totals match the controller/native token difference (500 uncached,
29,440 cache reads, 310 output). Request counts still match at 37, so the
existing whole-call diagnostic does not fully reconcile this aborted native
request: the native transcript counted a zero-usage aborted assistant entry at
11:01:55 UTC. Two late exec intents remain unresolved. Neither accounting nor tool
intent gates were waived.

Manual role audit also found direct `/world` reads in both harnesses' owner
conversations, and OpenClaw used a 12s sleep while checking inactive state.
Its supervisor directly read `/world` during repair as well as executing the
operational script. These violate the supplied role/bounded-turn instructions.
The automatic effect/quietness metrics do not certify role separation: phase-only
HTTP reads cannot distinguish permitted background code from a conversation's
read. A future role-attribution gate needs evidence beyond the latest-read
diagnostic; this sample must not be presented as conforming role separation.

## What to do next

The trunk-address fix is merged. Before another Peko sample, add a common preflight
expectation for model-authored procedures: exercise local parsing and receipt
handling with mocked HTTP and synthetic states, including the active branch;
compilation or an inactive-watch test alone is insufficient. This need not
provide controller-authored task code or grading answers.

Then validate recovery as a distinct deterministic capability: patch failed
code, reconcile receipts and restore the native job's retry eligibility without
the supervisor taking over operational effects. Use the installed native APIs,
verify their results and preserve native failure/backoff semantics. A declared
recovery contract should cover duplicate-job cleanup, immutable owner policy,
bounded repair turns and quiet operation.

After those surfaces stabilize, make one further Peko attempt and one matched
recovery comparison if needed. Defer multi-seed and multi-day runs. The proposal
to move deterministic work into code is technically viable; this pilot shows
that construction, validation and repair of that code are themselves essential
parts of the persistent-agent problem. It supplies no causal supervisor-value
estimate, harness superiority claim or novelty claim.
