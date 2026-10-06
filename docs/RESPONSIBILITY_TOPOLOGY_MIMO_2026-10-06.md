# Directed supervisor/task separation pilot — 2026-10-06

The previous pilot replaced Peko's default keepalive with a release-monitor Send
job in the trunk, discouraged delegation at genesis, and prohibited delegated
monitors in every task prompt. It therefore measured a flattened configuration,
not the intended supervisor/task-worker division. Its failures remain valid
for that configuration; they do not establish failure of the intended design.

## Protocol

Contract 4 adds `--topology separated` while preserving flattened contract 3.
Keep the same MiMo v2.6 Flash model, seed 1, 300-second watch, 35-second restart,
60-second task cadence, action API, obligations, deadline windows, grader and
$0.10 PAYG reference budget per harness. Wire admission remains 60 requests and
30k output tokens, max output 4096, thinking disabled and no fallback.

Peko genesis receives a directed organization task: retain and retune the
keepalive to organizational supervision every 120 seconds; create a focused
release-watch role and persistent child; register a separate native 60-second
Cron job that invokes Agent directly in that child. The worker checks dependency
state, acts and maintains task receipts/current state. The trunk tends general
memory/skills/session organization and repairs worker organization when needed.
No trunk LLM call dispatches each worker tick. Owner/review chats share canonical
requirements and cancellation/revision decisions with the worker.

OpenClaw receives the same division and permission to create workers/schedules:
its configured organizational heartbeat is 120 seconds, and its model registers
a native 60-second agent-turn automation in a persistent custom release-watch
session with no delivery. Native built-in memory/skill schedules are retained
and recorded. Any calls they make also count against the shared run budget.

The controller does not write roles, commitment answers or native task jobs.
Formation is directed by explicit setup instructions, not autonomous discovery
of the best topology. Read-only snapshots verify registration before the watch,
after restart and after the watch. Retained transcripts identify actual worker
and supervisor activity, including operational tool intents outside the worker.
The extended full gate requires verified registration and both execution lanes;
original obligation/quietness/memory grades are unchanged. Command-intent
attribution is diagnostic evidence, not proof of every HTTP caller identity.

This intervention changes topology and role prompts together. A comparison to
the retained flattened pair is exploratory, sequential and unpaired in model
latency, not a causal architecture experiment. Do not discard failures or rerun
until passing. Run one sample per harness, retain full costs, then decide the
next stabilization step. Deadline enforcement and latency risks still apply to
the task worker after isolation.

## Validation

All 60 offline tests pass, including rejection of a renamed trunk job, incorrect
worker routing, extra custom schedules, loss of the independent supervisor,
and operational tool intents in the supervisor. Live validation follows below.
Raw transcripts/native schedule snapshots remain local and gitignored.
