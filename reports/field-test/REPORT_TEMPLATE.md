# YYYY-MM-DD — Field test, Peko vX.Y.Z

<!-- Copy this file to YYYY-MM-DD-<tester-initials>.md and replace every
     placeholder. Keep it factual; quote the tester where you can. Never
     paste the API key. -->

| | |
|---|---|
| **Release** | Peko Desktop `v0.1.0-rc.6`, file `…`; peko-runtime `v0.1.0-rc.6` (commit `…`) |
| **Tester** | Initials. Background in one line, e.g. "accountant, uses a laptop daily, has never opened a terminal". |
| **Observer** | Name |
| **Machine** | OS and version, CPU (Apple silicon / Intel / x64) |
| **Model** | Wire format, endpoint, model id (e.g. `anthropic_messages`, MiMo v2.6 Flash) |
| **Duration** | Start–end, total minutes |
| **Agent run** | Agent and model, machine or container image, date |

## Desktop session (a person)

Outcome: **Done** (alone), **Hinted** (needed a hint), **Failed** (not
completed), **Skipped**.

| # | Task | Outcome | Time | Notes |
|---|---|---|---|---|
| 1 | Install the app | | | which file; what the system warned about |
| 2 | Connect the model | | | |
| 3 | Create the peko | | | wait until "awake" |
| 4 | Talk to it | | | |
| 5 | Reminder (due → arrived) | | | e.g. due 14:03, arrived 14:03; how they noticed |
| 6 | Close and come back | | | |
| 7 | Look around (optional) | | | |

**Core loop completed:** yes / no. That means install → model → create →
chat → reminder set and seen → conversation still there after quitting.

### Interventions

| Task | Time | What the observer said | Why |
|---|---|---|---|
| | | | |

### Debrief

1. Hardest part:
2. Wanted to give up when:
3. Expected Peko to … but it didn't:
4. Would keep using it if:
5. In one sentence, Peko is:

### App and daemon health

- A `peko-daemon` was running while the app was open: yes / no
- A `peko-daemon` was left after quitting: yes / no
- Crashes, freezes or restarts during the session:
- ERROR / WARN lines from `daemon.log` (summarised):

## Command-line run (an agent)

Outcome: **Done** (the result holds; at most one failed attempt),
**Hinted** (it holds, but after several failures, a guess, a workaround or
a look at source code), **Failed**, **Skipped**. Fill this in from your own
checks and the transcript, not from the agent's summary.

| # | Asked for | Outcome | Time | Failed commands | Notes |
|---|---|---|---|---|---|
| 0 | Install rc.6 | | | | |
| 1 | A peko | | | | |
| 2 | Three exchanges | | | | |
| 3 | Remembers Sam and hiking | | | | |
| 4 | Reminder (due → arrived) | | | | |
| 5 | Haiku skill | | | | |
| 6 | A job on the machine | | | | |
| 7 | Backup | | | | |
| 8 | Restart | | | | |

**Command-line loop completed:** yes / no. That means install → create →
chat → reminder set and received → skill installed and used.

- **Where it looked:** help screens and doc pages, in order.
- **Guesses and workarounds:** each one, with what would have saved it (a
  help line, an error message, a doc page).
- **Rule breaks:** source code read, repository cloned, key printed.
- **Claims that didn't hold:** anything the agent reported done that your
  check contradicted.
- **Daemon at the end:** `peko daemon status`, and ERROR / WARN lines
  (summarised).

## Findings

Copy the block below once per finding, highest level first. Say which run
it came from.

### P? — one-line title

- **Run and task:** desktop / command line, #
- **What happened:** what they clicked or typed, and the exact message or
  output.
- **Expected:** what the tester, the agent or the guide expected instead.
- **Impact:** what they did next; did they recover alone?
- **Evidence:** screenshot or log excerpt (nothing personal, no keys).
- **Issue:** link to the `ConekoAI/peko-desktop` or `ConekoAI/peko-runtime`
  issue (required for P0/P1).

## Gate 5 verdict

- **One non-technical-user session:** done / not done (desktop core loop
  completed? every task attempted?)
- **Command-line run by an agent:** done / not done (loop completed? every
  task attempted?)
- **P0 findings:** N. List each with its issue link. Gate 5 closes when
  every one is fixed and verified on a new release candidate.
- **Follow-ups:** P1s to fix before the MVP tag, and P2/P3s for later.
