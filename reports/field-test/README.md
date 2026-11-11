# Field-test kit: one release, two first-time users

This kit runs the field test that peko-runtime's MVP launch gate needs
(`docs/MVP_GATE.md`, gate 5). Peko has two front doors, and each gets the
first-time user it was built for:

- **Peko Desktop, tested by a person.** Someone who is not a developer
  installs the app and uses it, with no guide. A second person watches and
  writes the report.
- **The `peko` command line, tested by an agent.** A coding agent that has
  never seen Peko is asked, the way a person would ask, to install it and
  do a list of things with it. It gets goals, not steps. The command line
  is the surface agents and scripts use, so the test is whether an agent
  can work it out from the tool's help, its messages and its docs.

| File | For | Use |
|---|---|---|
| [TESTER_SCRIPT.md](TESTER_SCRIPT.md) | the human tester | One page of desktop tasks. Print it or open it beside the app. |
| [OBSERVER_CHECKLIST.md](OBSERVER_CHECKLIST.md) | the observer | Setup, what to watch at each task, how to classify findings, cleanup. |
| [AGENT_BRIEF.md](AGENT_BRIEF.md) | the agent | Eight things to get done with `peko`, given to the agent as its whole brief. No commands and no pointers into the docs. |
| [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) | the observer | Copy it to `YYYY-MM-DD-<tester-initials>.md` in this folder and fill it in. It has a section for each run. |

## What the gate asks

Gate 5 asks for one non-technical-user session against the release artifact,
and zero open P0 findings from it. **P0** blocks the core loop: the tester
can't install, can't converse, loses messages, or the daemon crashes.

- **The human session is the desktop one.** Its loop is install → connect a
  model → create a peko → chat → set a reminder → receive it → come back
  after quitting.
- **The agent run covers the command line**: install → create → chat →
  memory → reminder → skill → a job on the machine → backup → restart. The
  skill is there because the app has no screen for skills.

A filed report with every task of both runs attempted closes the first
item. The second closes when no P0 from either run is open: each P0 is fixed
and verified on a new release candidate, or none was found.

## The human session at a glance

- **Release:** Peko Desktop `v0.1.0-rc.6`, or the newest candidate if a
  later one exists. It must be published; a draft release is invisible to
  the tester.
- **People:** a tester who has never used Peko and doesn't write code for a
  living, and an observer who knows Peko.
- **Time:** about 30 minutes, plus 15 for setup and 15 to write the report.
- **Machine:** a Mac (Apple silicon or Intel), a Windows 10 or 11 PC (x64),
  or a Linux desktop with Ubuntu 22.04 or newer, where neither Peko Desktop
  nor `peko` has ever been installed. The tester needs a browser. No
  terminal.
- **Docs the tester uses:** none. The app has no end-user guide yet and
  should explain itself. Every place the tester needs a guide is a finding.

## The agent run at a glance

- **Release:** peko-runtime `v0.1.0-rc.6`, the same candidate.
- **Agent:** any coding agent with a shell, started with no Peko source
  checkout and no memory of Peko. Record which agent and model.
- **Machine:** a clean container or throwaway home (Ubuntu 22.04 or newer,
  or macOS) where `peko` isn't installed and `~/.peko` doesn't exist.
- **Brief:** `AGENT_BRIEF.md` below its line, verbatim, with the model
  card's values filled in. Nothing else: no steps, commands or doc links.
- **What the agent may use:** the tool's own help and messages, and the
  documentation in the peko-runtime repository, which it finds itself. Not
  the source code, and no clone of the repository.
- **Observer's part:** read the transcript afterwards and check each result
  yourself on the machine; don't take the agent's word. Then fill in the
  report's agent section. Using `--help` is the expected path. What gets
  recorded is every command that failed before one worked, every guess,
  and any look at source code.
- **On macOS,** Peko keeps its vault key in the keychain, and a headless
  agent can't answer the system's prompt. A Linux container avoids it. On a
  Mac, either let the prompt count as a finding, or set
  `PEKO_UNLOCK_METHOD=passphrase` and `PEKO_MASTER_PASSPHRASE` in the
  agent's environment and say so in the report.
- **Runs:** one is enough for the gate. Agents vary from run to run, so a
  second run, or a second agent, shows which stumbles are Peko's.

## Dry runs

The command-line loop was dry-run by a developer following the guides on `v0.1.0-rc.4`
(2026-10-26, macOS arm64, MiMo v2.6 Flash, a throwaway home) and all passed.
- **Timings:** install 41 s, `create` 92 s, and the 3-minute reminder
  arrived about a minute late.
- **What it found:** the installer bug fixed in ConekoAI/peko-runtime#509
  (a missing `--install-dir` installed nothing), and two reminder P2s fixed
  in #510. `v0.1.0-rc.5` is the first candidate to carry both.

The agent brief was tried once on `v0.1.0-rc.6` (2026-11-11, a Haiku agent
in a throwaway home on macOS): all eight goals reached, one of them hinted,
four P2 findings, no P0. See
[2026-11-11-agent-trial.md](2026-11-11-agent-trial.md). The desktop tasks
have never been dry-run. Do the desktop one yourself, on a machine or user account
where the app has never run, before the session.

## The model card

Both runs need a model to connect. The observer writes these four values on
a card, or in a note the tester can copy from, before the session:

```
Base URL:    https://token-plan-cn.xiaomimimo.com/anthropic
API format:  anthropic_messages
Model:       mimo-v2.6-flash
API key:     (the observer's key)
```

Any endpoint in a supported wire format works. Record which one was used in
the report.

The key is the observer's. Don't paste it into the report or any committed
file. Give it to the agent through its environment, not in the brief's
text. Delete the test machine's Peko data at the end (checklist, Cleanup) or
rotate the key afterwards.
