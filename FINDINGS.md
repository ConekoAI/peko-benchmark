# Findings log

Curated, human-written gap list from benchmark runs. Raw evidence lives in
`reports/<run>/` (gitignored) — this file is the distilled signal for the
pre-MVP gap list.

## 2026-09-30 — first live run (peko + MiniMax-M3, 4 tasks × 1 rep)

**Results:** 4/4 pass (after one spec fix on the benchmark side — see F2).
`reports/20260930T025222Z-first-contact/` + `reports/20260930T025627Z-mdspec-v2/`.

### F1 — `max_iterations = 10` is hard-coded and binds on every real task — **RESOLVED 2026-09-30** (cap removed entirely, peko-runtime `da16eb7e`)

- `peko-rs/engine/src/agentic_loop.rs:303` set `max_iterations: 10` in
  `AgenticLoop::new`; `with_max_iterations` was only ever called by tests.
  No config/principal.toml knob existed.
- Smoke run: agent diagnosed the bug correctly but hit the cap mid-fix;
  channel reply was literally "Max iterations reached (10)".
- Full run: 4 of 5 runs consumed the entire budget (`[peko] iterations=10`
  in send.err), including 3 of the 4 passes. Tasks passed *despite* the
  cap, not comfortably within it. Anything slightly larger would fail.
- **Resolution:** the cap was removed entirely (not made configurable).
  The loop now ends on natural completion, abort, quota, or error.
  Verified live (`reports/20260930T040446Z-uncapped2/`): py-md-stats ran
  to **31 iterations / 759k input tokens** and passed; py-cache-invalidation
  finished in 8. Note the consequence: quota (`budget_per_cycle`, cost
  ceiling) is now the ONLY runaway governor — no iteration backstop exists.
- Verification caveat: the harness's `peko create` spawns the
  `peko-daemon` binary *next to* `PEKO_BIN` — both binaries must be
  rebuilt (`cargo build -p peko-cli -p peko-daemon`), a CLI-only rebuild
  silently benchmarks the old engine. (First uncapped attempt hit exactly
  this; the footer gave it away: `iterations=10`.)

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
