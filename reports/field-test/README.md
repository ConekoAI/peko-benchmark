# Field-test kit: one non-technical user, one release

This kit runs the human field test that peko-runtime's MVP launch gate needs
(`docs/MVP_GATE.md`, gate 5). One person who is not a developer installs and
uses a Peko release by following its public docs. A second person watches
and writes the report.

| File | For | Use |
|---|---|---|
| [TESTER_SCRIPT.md](TESTER_SCRIPT.md) | the tester | One page of tasks. Print it or open it beside the terminal. |
| [OBSERVER_CHECKLIST.md](OBSERVER_CHECKLIST.md) | the observer | Setup, what to watch at each task, how to classify findings, cleanup. |
| [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) | the observer | Copy it to `YYYY-MM-DD-<tester-initials>.md` in this folder and fill it in. |

## What the gate asks

From `MVP_GATE.md` gate 5:

- **One non-technical-user session** against the release artifact:
  install → create a peko → chat → set a reminder → receive it → install a
  skill → use it.
- **Zero P0 findings open** from that report. **P0** blocks the core loop:
  the tester can't install, can't converse, loses messages, or the daemon
  crashes.

A filed report with every task attempted closes the first item. The second
closes when no P0 from it is open: each P0 is fixed and verified on a new
release candidate, or none was found.

## The session at a glance

- **Release:** `v0.1.0-rc.4`, or the newest candidate if a later one exists.
  Use the same release for the whole session.
- **People:** a tester who has never used Peko and doesn't write code for a
  living, and an observer who knows Peko.
- **Time:** about 60 minutes, plus 15 for setup and 15 to write the report.
- **Machine:** a Mac (Apple silicon or Intel), or a Linux desktop with
  Ubuntu 22.04 or newer, where Peko has never been installed. The tester
  needs a terminal and a browser.
- **Docs the tester uses:** only the public ones, `docs/getting-started/
  GETTING_STARTED.md` and `docs/getting-started/TUTORIAL_FIRST_PEKO.md` on
  GitHub. Nothing else: no source code, no help from the observer unless
  the tester is stuck (see the checklist's intervention rule).

## Dry run

The observer's own run of the eight tasks on `v0.1.0-rc.4` (2026-10-26,
macOS arm64, MiMo v2.6 Flash, a throwaway home) passed every task.
- **Timings:** install 41 s, `create` 92 s, and the 3-minute reminder
  arrived about a minute late.
- **What it found:** the installer bug fixed in ConekoAI/peko-runtime#509
  (a missing `--install-dir` installed nothing), and the two reminder P2s
  listed in the checklist. Those are fixed in ConekoAI/peko-runtime#510,
  which reaches testers with the next release candidate.

## The model card

The tester needs a model to connect. The observer writes these four values on
a card, or in a note the tester can copy from, before the session:

```
API format:  anthropic_messages
Base URL:    https://token-plan-cn.xiaomimimo.com/anthropic
Model:       mimo-v2.6-flash
API key:     (the observer's key)
```

Any endpoint in a supported wire format works. Record which one was used in
the report.

The key is the observer's. Don't paste it into the report or any committed
file. Delete the test machine's Peko data at the end (checklist, Cleanup) or
rotate the key afterwards.
