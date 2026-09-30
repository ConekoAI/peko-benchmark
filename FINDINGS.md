# Findings log

Curated, human-written gap list from benchmark runs. Raw evidence lives in
`reports/<run>/` (gitignored) — this file is the distilled signal for the
pre-MVP gap list.

## 2026-09-30 — first live run (peko + MiniMax-M3, 4 tasks × 1 rep)

**Results:** 4/4 pass (after one spec fix on the benchmark side — see F2).
`reports/20260930T025222Z-first-contact/` + `reports/20260930T025627Z-mdspec-v2/`.

### F1 — `max_iterations = 10` is hard-coded and binds on every real task (pre-MVP gap, peko-runtime)

- `peko-rs/engine/src/agentic_loop.rs:303` sets `max_iterations: 10` in
  `AgenticLoop::new`; `with_max_iterations` is only ever called by tests.
  No config/principal.toml knob exists.
- Smoke run: agent diagnosed the bug correctly but hit the cap mid-fix;
  channel reply was literally "Max iterations reached (10)".
- Full run: 4 of 5 runs consumed the entire budget (`[peko] iterations=10`
  in send.err), including 3 of the 4 passes. Tasks passed *despite* the
  cap, not comfortably within it. Anything slightly larger will fail.
- Recommendation: expose an iteration budget knob (principal.toml) and/or
  raise the default substantially for interactive workloads.

### F2 — Benchmark lesson: spec ambiguity measures luck, not capability

- `py-md-stats` v1 said "--top-words composes: summary first when
  combined with count flags" without stating the standalone behavior.
  The agent (defensibly) preserved the CLI's `no flags → print summary`
  default and failed all hidden tests while believing it had succeeded.
- Fixed by stating standalone behavior explicitly; re-run passed (54s).
- Rule for future tasks: every observable behavior the grader checks must
  be derivable from the prompt. When a run fails, check the spec before
  blaming the harness.

### F3 — Workdir discovery friction (benchmark-side, fixed)

- A peko agent's default cwd is its own (empty) workspace; a prompt that
  names the project directory only in a trailing note cost ~4 iterations
  of confused exploration. The runner now leads with the working
  directory. Runtime-side, consider whether the principal's workspace
  should be the natural place users drop projects (document the pattern).

### Notes

- Token usage per run: ~210k input tokens on the python tasks (no
  compaction triggered at this size), ~1.7–2.1k output. Wall 36–62s on
  MiniMax-M3 with a debug binary.
- No harness failures; isolation, model setup, and grading all clean.
