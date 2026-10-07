# Direct actions and lean worker checks — 2026-10-07

The [contract-6 handoff pilot](RESPONSIBILITY_HANDOFF_MIMO_2026-10-07.md)
reached the unattended watch with verified supervisor/task-worker separation
in both harnesses. Both completed all three obligations on time. OpenClaw
passed; Peko repeated Atlas and Dogwood after successful HTTP POSTs were
followed by failing shell timing arithmetic, then exhausted its 60-request
allowance before the memory probe. Those results remain retained.

## Contract 7 intervention

Both separated harnesses now receive the same additional action guidance:
issue one direct curl POST that prints its response immediately; avoid shell
variables, timing arithmetic, pipelines, retries or other output processing
around a mutating request. An error after a POST is an uncertain outcome,
not evidence that the mutation did not occur. Persist an uncertain attempted
payload and do not resubmit without durable evidence that it did not happen.
This is model guidance, not enforced idempotency or an action transaction API.

Worker ticks batch independent canonical reads where supported, persist concise
receipts and changed task state after meaningful work, and skip no-action
receipt rows, last-check timestamps and unchanged-state rewrites. Elapsed-time
notes label the already observed world time as observation time rather than
claiming it is the action completion time. No separate timestamp process is
needed. The action schema, canonical state rules and required receipt/state
maintenance remain intact. The flattened contract-3 prompts are unchanged.

No controller installs task jobs/files, supplies commitment answers, deduplicates
actions, changes the grader or intervenes during the watch. Formation remains
directed through native genesis/onboarding, with a dedicated task worker every
60 seconds and organizational supervisor every 120 seconds.

Run one fresh sample per harness, simulator seed 1, same MiMo v2.6 Flash,
4096 max output, thinking disabled, no fallback, $0.10 PAYG reference cap,
60 forwarded-request/30k-output admission caps, 300-second watch, restart at
35 seconds, original deadlines and 900-second overall allowance. Native
conversation/setup/worker time limits are unchanged. Launch the pair concurrently
in isolated native homes, as in contract 6. Account for every phase and retain
failures or incomplete usage rather than retrying until passing.

## Validation and results

Offline checks verify that both separated conversation and worker prompts
contain the same static direct-action guidance without obligation answers.
Live results will be recorded after the bounded pair finishes. Raw native
transcripts remain local and ignored.
