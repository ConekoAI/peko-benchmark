# 2026-11-11 — Trial of the agent brief, Peko v0.1.0-rc.6

A first run of `AGENT_BRIEF.md`, to try the brief and the observer's checks
before the gate session. It is **not** the gate 5 run: see "How this differs
from the gate run" below. There was no desktop session.

| | |
|---|---|
| **Release** | peko-runtime `v0.1.0-rc.6` (commit `0616d2db`), `peko-macos-aarch64.tar.gz`, SHA-256 checked against the release notes |
| **Agent** | Claude Code 2.1.322 on `claude-haiku-5-5`, headless, started in an empty folder with a clean environment; no Peko checkout, notes or memory |
| **Observer** | Claude Code (the session that prepared the kit); results checked on the machine afterwards |
| **Machine** | macOS, Apple silicon; a throwaway home (`HOME` pointed at an empty folder), no `peko` on `PATH` |
| **Model for the peko** | `anthropic_messages`, `https://api.anthropic.com`, `claude-haiku-5-5` |
| **Duration** | 16:21–16:38 JST, 17 minutes, of which about 10 were the download; 32 agent turns |

## Results

Every result was checked on the machine by the observer: `peko list`,
`peko log pip`, the files in the peko's folder, and `peko audit ledger pip`.

| # | Asked for | Outcome | Failed commands | Notes |
|---|---|---|---|---|
| 0 | Install rc.6 | Done | 1 | Looked for tag `0.1.0-rc.6`; it is `v0.1.0-rc.6`. Did not use `install.sh` (finding 3). Both binaries are in `~/.local/bin`. |
| 1 | A peko | Done | 0 | `peko create pip --model claude-haiku`, found from `create --help`. Ready in under a minute. |
| 2 | Three exchanges | Done | 0 | Three questions and three answers in `peko log pip`. |
| 3 | Remembers Sam and hiking | Done | 0 | Recalled in the next message; `kb/MEMORY.md` has both. |
| 4 | Reminder | Done | 0 | Asked 16:33:22, job created 16:33:24, arrived 16:36:32: 8 s after it was due. One clean line, "Time to stretch, Sam." |
| 5 | Haiku skill | **Hinted** | 0 | Asked the peko to "remember this rule as a skill"; it saved a memory note and said "Noted" (finding 1). The agent then found the tutorial and wrote `skills/haiku/SKILL.md` itself. |
| 6 | A job on the machine | Done | 0 | The ledger shows the peko's own `Write` at 16:36:57; `notes/today.md` has three ideas. The agent found the folder with `peko show pip`. |
| 7 | Backup | Done | 0 | `peko export pip -o …`, 28 KB. Made before the skill file existed, so it doesn't hold the skill. |
| 8 | Restart | Done | 0 | `daemon stop`, `status`, `daemon start`; the peko named Sam and hiking afterwards. |

**Command-line loop completed:** yes, with one hinted step.

- **Where it looked:** the GitHub releases API and the release notes; then
  `--help` for `model`, `model add`, `daemon`, `create` and `export`. It
  read the README and the tutorial only after all eight goals, to check its
  work, and that is when it found the skill format.
- **Guesses and workarounds:** one, the skill (finding 1).
- **Rule breaks:** none. No source code read, no clone, and the key appears
  in no file the agent made (checked by count).
- **Claims that didn't hold:** none. The agent's report matched every check,
  and it volunteered the two weak spots itself (the skill, and the backup
  predating it).
- **Daemon at the end:** running, version `0.1.0`; two `WARN` lines, both
  the expected "principal pip added" drift notice after the restart.

## Findings

### P2 — Asking a peko to learn a skill saves a memory note, and it doesn't say so

- **Run and task:** command line, 5
- **What happened:** `peko send pip "From now on, whenever I ask you for a
  haiku, end your reply with a final line that says: -- peko   Please
  remember this rule as a skill for haiku requests."` The peko answered
  "Noted. From now on, when you ask for a haiku, I'll end the reply with
  `-- peko`." It edited `kb/MEMORY.md`. No `skills/` folder was made.
- **Expected:** a skill, or a reply saying that a skill is a file and where
  it goes. The peko has `Write` and could have made
  `skills/haiku/SKILL.md` itself.
- **Impact:** the behaviour worked, so nothing looked wrong. The agent
  noticed only because it later checked the folder. `peko --help` doesn't
  mention skills; the tutorial is the only place that does.
- **Evidence:** `peko log pip` at 16:36; ledger `Edit` at 16:36:48.

### P2 — `peko --version` prints `0.1.0` on a release candidate

- **Run and task:** command line, 0
- **What happened:** `peko --version`, `peko version` and
  `peko daemon status` all print `0.1.0` for the rc.6 binaries.
- **Expected:** `0.1.0-rc.6`. Nothing on the machine says which candidate is
  installed, so a bug report can't name it and two candidates can't be told
  apart. The kit's own check for this step was wrong for the same reason
  (fixed in this change).

### P2 — A candidate's release notes give an install command that doesn't install it

- **Run and task:** command line, 0
- **What happened:** the rc.6 release notes' "One-line installer" is
  `curl … install.sh | bash`, with no `--version`. The installer's default
  asks GitHub for the latest release, which never returns a prerelease. The
  agent downloaded the archive by hand instead, which worked.
- **Expected:** on a candidate's page, the command that installs that
  candidate (`bash -s -- --version 0.1.0-rc.6`).
- **Not tested:** what the bare one-liner does today, with no stable
  release to find. The agent never ran it.

### P2 — Starting the daemon erases the previous daemon log

- **Run and task:** command line, 8
- **What happened:** after `peko daemon stop` and `peko daemon start`,
  `~/.peko/logs/daemon.log` begins at the second start. Everything from the
  first 5 minutes is gone. This is by design
  (`daemon_process_service.rs`, "truncated on each start").
- **Impact:** after a crash, the natural next step is to start the daemon
  again, and that erases the evidence. The kit's "collect ERROR / WARN
  lines" step can't cover anything before a restart; this report has
  daemon warnings only for the last 90 seconds.

### P3 — Small things

- `peko log` shows minutes only, so a reminder's delay can't be read from
  it. The exact time is in the channel's `events.jsonl`.
- The reminder's acknowledgement ("I'll remind you to stretch in 3
  minutes") doesn't give the time it will arrive.
- Asked "What do you know about me?", the peko added that it has "an open
  item" and will ask about the owner's goals on 2026-11-12. Nobody asked
  for that; it comes from the plan a new peko makes for itself.
- Every `send` prints a line such as `[peko] iterations=1 input=23378
  output=15 total=23393 tools_failed=0`. A one-line question costs about
  23K input tokens; the session's turns added up to roughly 560K by those
  counts.
- The brief said `0.1.0-rc.6` and the tag is `v0.1.0-rc.6` (one failed
  lookup). `~/.local/bin` wasn't on `PATH`, so the agent used the full
  path throughout; `install.sh` would have said so, but it wasn't used.

No P0 and no P1.

## What the trial says about the kit

- **The brief works as written.** A small model got through all eight goals
  in 32 turns from help text alone, and its report was accurate. The goals
  need no more detail.
- **The skill goal is the one that separates outcomes.** It is the only
  step the help doesn't cover, and the only one where the result looked
  right while the thing asked for wasn't made.
- **Fixed in the kit with this report:** the install check no longer
  expects `peko --version` to name the candidate; the checklist says to
  collect daemon warnings knowing a restart erased the earlier ones; the
  README says how to keep macOS from raising a keychain prompt.
- **One run, one model.** A second run or a different agent would show
  which of these are steady.

## How this differs from the gate run

- **The vault was set to passphrase mode beforehand**
  (`PEKO_UNLOCK_METHOD=passphrase` and a passphrase in the agent's
  environment), so that Peko would not raise a macOS keychain prompt a
  headless agent can't answer. How a first-time command-line user gets
  through that step was therefore not tested.
- **A throwaway home on a developer's Mac**, not a clean container. Tools a
  clean machine lacks (`gh`, `python3`) were present.
- **The observer wrote the kit** and is not a second person.
- **No desktop session**, so gate 5's first item is untouched.

## Gate 5 verdict

- **One non-technical-user session:** not done.
- **Command-line run by an agent:** trial only; not counted.
- **P0 findings:** 0.
- **Follow-ups:** the four P2s above. None is filed as an issue yet.
