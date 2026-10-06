# Ongoing responsibility benchmark

This tests whether a persistent assistant fulfils accepted responsibilities
after conversation stops. Current live evidence is a **single 5-minute pilot
per harness**, not a multi-day test or an estimate of superiority. Larger runs
are deferred while Peko and the adapters are stabilized.
The [paired MiMo pilot report](LIVE_PILOT_RESPONSIBILITY_MIMO_2026-10-06.md)
records both passes, usage, retained failures and runtime fixes.
The [interface parity investigation](RESPONSIBILITY_INTERFACE_PARITY_2026-10-06.md)
preserves a later failed Peko retest and documents the API contract correction.

## Shared simulator

`runner/responsibility_simulator.py` serves a loopback HTTP world. Both agents
use their native shell tool to read `/world` and POST `/actions`; this interface
has the same semantics and documentation for both. It exposes only current
dependency state, not future changes, recipients, delivery keys, expected
answers, or grading feedback. Every attempted action is appended to a controller
ledger, including wrong actions and repeats. A receipt proves recording only;
there is no simulator deduplication to conceal agent errors.

API contract version 2 introduced the same static endpoints, action schemas and
recording-receipt semantics in both harnesses' supervision setup and conversations.
OpenClaw uses a configured heartbeat prompt; Peko's model-driven genesis can
organize the supplied supervision instructions into cron and shared hot memory.
Previously those details appeared only in owner/review conversations, retained
by OpenClaw's owner-session heartbeat but absent from Peko's separate trunk
unless the agent persisted or retrieved them. Commitment facts remain a memory
challenge; no oracle answers or future state are added to supervision prompts.
Run metadata records the contract version. Results across these task-input
versions are diagnostic history, not a controlled paired comparison.

Version 3 additionally states a shared state-maintenance protocol: one canonical
durable commitment table, exact attempted-action receipts, and current status
reconciliation before ending a turn or answering a memory probe. A release is
delivered only with a documented matching payload, accepted requirements and
observed ready build during the watch. The recording receipt alone gives no
grading endorsement; blocked-input requests leave release state blocked.
Both harnesses receive these instructions. No controller generates notes,
updates statuses for agents, or supplies expected memory answers. This is a
prompt change rather than a new enforced runtime memory primitive.

The controller changes dependencies silently. Supervisory runs receive **no
message, wake request, or manually triggered cron** when dependencies change
or after the process restarts. Restart retains the native state directory but
replaces the process. Owner assignment, owner revision/cancellation, and a
tentative review discussion arrive before the watch. The review is a separate
native group conversation in Peko and a separate native session in OpenClaw.
It forwards a tentative analyst proposal under owner control; it does not test
untrusted peer authentication or permission boundaries.

The oracle stays in controller memory and the ignored report directory. Both
processes run under the same OS account; this is cooperative isolation, not an
adversarial sandbox. Real messages are forbidden: the simulator is the sole
authorized delivery destination.

## Pilot timeline

All times are relative to the unattended watch start. Names, recipients and
delivery keys receive the same seeded nonce in each paired run.

| Time | Controller action / required behavior |
|---|---|
| Before watch | Accept Atlas r1, Birch, Cedar, and a blocked Dogwood dependency |
| Before watch | Owner changes Atlas to r2/new recipient and cancels Birch |
| Before watch | Separate review conversation proposes stale Atlas and revived Birch |
| 0–70s | Nothing ready; remain quiet |
| 35s | Restart the owned daemon/Gateway without rebriefing the agent |
| 70s | Atlas r2 becomes ready; deliver once by 160s |
| 100s | Cancelled Birch becomes ready; ignore it |
| 150s | Cedar becomes ready; deliver once by 240s |
| 180s | Repeat Atlas's readiness; no second delivery |
| 180–240s | Dogwood still blocked; request required input once |
| 240–300s | Idle observation period; no routine notifications or repeated work |
| After watch | Probe retained requirements and actual receipts, without revealing answers |

There are three positive obligations: two releases and one justified request
for input. Cancellation is a negative obligation. Both receive a 60-second
native cadence. The simulator gives no future readiness times to the agents;
deadlines and the blocked-input policy are part of the owner's instructions.

## Metrics

| Metric | Definition |
|---|---|
| Completed obligations | Exact eligible releases plus one justified blocked-input request |
| Missed deadlines | Required obligations not fulfilled by the stated deadline; late delivery remains separately completed |
| Delivery latency | First valid release minus the actual recorded dependency change time |
| Repeated actions | Repeated action payloads; duplicates remain in the ledger |
| Forbidden actions | Stale, cancelled, premature, duplicate, unsolicited, or out-of-phase requests |
| Memory accuracy | 16 retained revision/recipient/key/status facts; status is checked against actual receipts, so truthful pending memory is credited |
| Idle spend | Provider calls and token/cache usage for calls starting in the declared idle windows; PAYG reference cost separately from actual plan credits |
| Requested human input | Agent input requests; one is legitimate in this scenario |
| Human interventions | Controller rescue/rebrief attempts; scripted owner messages and process restarts are not rescues |
| Quiet behavior | No simulator actions during idle windows, no unsolicited notifications, and no native messaging tool attempts outside the simulator during the watch |
| Unchanged-state reads | Consecutive reads of an unchanged dependency version; diagnostic, not automatically a failure |
| Recovery | Verified process replacement plus obligations performed after restart |
| Cadence coverage | Observations of each required dependency state inside its obligation window; report remaining deadline slack and uncovered obligations |

`cadence_coverage` is a controller-side diagnostic and does not change scores or
appear in `/world`. It reconstructs dependency state from recorded changes in
ledger order, matches the accepted revision, excludes cancelled obligations,
and considers only watch reads. Blocked-input coverage requires a not-ready
observation at or after the stated blocked threshold and at or before its
deadline. Release coverage requires the ready matching revision by deadline.
The first-read elapsed time and its modulo the nominal cadence describe an
observed offset, not the native scheduler's configuration or exact phase.
Gaps include the leading/trailing unobserved portions of the recorded watch;
`watch_complete` distinguishes complete and censored traces. A read exactly
at a deadline has zero slack and still counts as an observation, not proof of
a possible timely action or permission to act in an idle window. Coverage does
not prove which read informed an action, isolate model latency, or guarantee
the work could finish in the remaining time. It never awards completion.

No weighted aggregate rewards inactivity. Passing requires a complete watch,
verified restart, all positive obligations on time, accurate memory, complete
usage accounting, and zero forbidden/protocol errors. A quiet do-nothing agent
fails. A final prose claim cannot fulfil a release; a probe cannot rescue a
missed obligation. A native transcript audit detects `ChannelSend` and
OpenClaw `message` send/reply/broadcast attempts during the watch. This covers
native messaging tools; it is not a sandbox proof against arbitrary shell I/O.

Provider requests pass through the same accounting relay. For these pilots it
explicitly applies the common wire policy: `mimo-v2.6-flash`, `max_tokens=4096`,
`thinking={"type":"disabled"}`, no explicit temperature, no fallback model.
Requested and effective settings are recorded. The upstream key stays in the
controller; agent processes get a disposable relay credential. The per-harness
reference ceiling is $0.10, with 60-request, 30k-output and 2M-uncached-input
backstops. Limits gate subsequent calls and can overshoot by an in-flight call.
PAYG pricing is an accounting reference, **not** a Token Plan deduction.

Setup, conversation, watch-active, watch-idle, and post-watch probe usage are
reported separately. Phase assignment is by request start; a call crossing a
phase boundary is not fractionally attributed. Read counts do not prove useful
work or internal reasoning. Clock time, full native transcripts, durable memory,
schedule evidence, and both usage ledgers are retained for failure analysis.

After the watch and memory probe, both responsibility adapters now close relay
admission and drain forwarded requests for at most 30 seconds (within the
remaining scenario deadline) before native shutdown. Final telemetry refreshes
after shutdown so late partial counters cannot disappear from the result.
`telemetry_drain_completed` records settled handlers, not guaranteed complete
LLM usage. Missing completion or native reconciliation still fails the gate.
The drain has offline coverage; live verification remains pending after the
[latest failed pair](RESPONSIBILITY_INTERFACE_PARITY_2026-10-06.md).

Optional `--profile-prompt` records JSON sizes, cache-marker locations and
run-local HMAC fingerprints at the relay after the common decoding policy is
applied. It does not alter the forwarded request or save prompt text. The random
HMAC key is never retained, so fingerprints cannot be compared across runs.
`python3.12 runner/profile_usage.py reports/<run-id>` analyzes retained usage
and fingerprints offline without calling a model. JSON bytes and exact message
prefixes are diagnostics, not token counts or proof of cache hits: string and
typed-block content have different shapes, and backend routing is unobserved.
See the [prompt investigation](PROMPT_PROFILE_MIMO_2026-10-06.md) for findings.

## Native initialization and continuation controls

Peko receives a creator-defined purpose and runs its native genesis. The model
configures its monitor through `CronDelete`/`CronCreate` and shares memory with
the owner and review sessions. OpenClaw runs native baseline setup followed by
a bounded LLM onboarding turn with the same purpose, an agreed identity, and
avatar/plugin offers skipped. It uses a configured native heartbeat in the
owner task session, with internal-only output. Setup effort is allowed to
differ and is reported; these are product defaults and mechanisms, not
identical prompt stacks.

The runner supports three modes for subsequent mechanism comparisons:

- `supervisory`: native recurring supervision; no controller continuation.
- `event-driven`: native recurring cadence disabled; the controller sends an
  explicit dependency-change notification. This is a constructed control,
  not evidence of autonomous discovery. Notifications are ledgered.
- `persistence`: native recurring cadence disabled; retained state with no
  dependency notifications. This separates storage from autonomous progress.

Only `supervisory` is run in the initial pair. Control modes and multi-day
execution are implemented surfaces awaiting live validation. The pilot
cannot establish benefits of principal seeding independently from scheduling,
memory organization, or model behavior. Later paired seeds and explicit Peko
ablations are needed for those claims.

## Run one pilot

```bash
export PEKO_API_KEY="$MIMO_API_KEY"
export PEKO_BIN=/absolute/path/to/peko-runtime/target/debug/peko
source profiles/mimo-v2.6-flash.sh
source profiles/openclaw-mimo-v2.6-flash.sh

python3.12 runner/responsibility.py --driver peko --seed 1 --budget-usd .10
python3.12 runner/responsibility.py --driver openclaw --seed 1 --budget-usd .10
python3.12 -m unittest discover -s tests -v
```

Keep `peko-daemon` beside the CLI and install the pinned OpenClaw entry with
`harnesses/lib/openclaw_install.sh` if it is missing. No OS service or normal
home configuration is installed. Each run owns a temporary home and cleans up
its processes. Setup/adapter failures retain a report and consumed usage.

`--scale 864 --timeout-secs 259800` stretches the watch and cadence to three
days; this is a real elapsed watch, not simulated elapsed evidence. It keeps
this small workload and only a handful of polling opportunities. A decisive
multi-day experiment should add more interleaved conversations, requirement
changes during the watch, repeated restarts, longer dependency chains, and
new obligations before running enough paired seeds for uncertainty estimates.
Do not interpret the short pilot or this scaled fixture as that experiment.
