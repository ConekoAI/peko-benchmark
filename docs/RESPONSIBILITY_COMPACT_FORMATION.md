# Compact formation diagnostic v1

This diagnostic isolates setup from unattended execution. It asks the same MiMo
model to accept owner requirements, revise them, inspect a conflicting review,
author one stdlib Python worker, validate it and register one native recurring
code job. It never starts a watch, advances the dependency timeline, restarts a
harness or issues a memory probe. Completion, deadlines, restart behavior and
unattended quietness are unmeasured.

The controller supplies an empty organization and two immutable fixture files
under `.benchmark-fixture/`. It supplies neither a worker nor accepted owner
facts. The fictional fixture uses actual localhost HTTP and the public guarded
action service. Ten cases cover eligibility, rejection, repeat quietness,
committed receipt reconciliation, a committed POST whose connection drops, and
blocked thresholds. A valid reference implementation exists only in fixture
certification tests and the separately labelled scripted native probe.

The worker interface is `workflows/watch.py --base-url URL --workspace DIR`.
Canonical commitments use plain JSON. The controller verifies owner facts,
fixture hashes, actual native job arguments and period, and independently runs
the pristine fixture against the retained worker. A job must bind exactly that
worker to the live URL and workspace. Live action attempts during formation
fail the gate. Controller-prepared supervision stays unarmed: Peko's supervisor
is parked an hour ahead and OpenClaw's heartbeat is disabled.

Both harnesses use the existing common 4096 output-token cap, disabled thinking,
request/output limits and reference cost budget. Each owner/review command has
180 seconds within a 900-second scenario budget. There is one attempt per
harness; no oracle feedback, controller continuation or automatic rerun.
Formation wall time and spend remain outcomes. Accounting completeness and
native usage reconciliation are separate validity gates. The result retains
tool intent, native results and upstream termination reasons for attribution.

Peko's bounded output-limit recovery is runtime behavior, not controller
feedback: partial output and native results are preserved; at most two
continuations suggest smaller responses without increasing limits. An invalid
empty Write still fails validation. OpenClaw uses its pinned native behavior.

```sh
export PEKO_BIN=/absolute/path/to/peko-runtime/target/debug/peko
source profiles/mimo-v2.6-flash.sh
source profiles/openclaw-mimo-v2.6-flash.sh
# These scripted probes use no real provider credentials or real LLM calls.
python3.12 runner/responsibility_compact_smoke.py --driver peko
python3.12 runner/responsibility_compact_smoke.py --driver openclaw
# Live attempts read MIMO_API_KEY from the environment; run serially.
python3.12 runner/responsibility_formation.py --driver peko
python3.12 runner/responsibility_formation.py --driver openclaw
```

Reports contain source hashes, native fingerprints, formation gates, phase
durations, accounting and final authored code. Supplied fixture code is excluded
from authored artifacts. These reports have separate evidence kinds and never
replace historical strategy-choice scores. Passing fictional tests establishes
the sampled worker behaviors; it is not evidence of live native scheduler
execution or success over several days. The scripted probe establishes native
file/shell/registration reachability and an actual scheduled invocation against
the inactive live world separately, without an LLM request during the fire.
