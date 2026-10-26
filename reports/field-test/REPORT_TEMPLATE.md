# YYYY-MM-DD — Non-technical field test, Peko vX.Y.Z

<!-- Copy this file to YYYY-MM-DD-<tester-initials>.md and replace every
     placeholder. Keep it factual; quote the tester where you can. Never
     paste the API key. -->

| | |
|---|---|
| **Release** | `v0.1.0-rc.4` (commit `…`) |
| **Tester** | Initials. Background in one line, e.g. "accountant, uses a laptop daily, has never opened a terminal". |
| **Observer** | Name |
| **Machine** | OS and version, CPU (Apple silicon / Intel / x86_64 / arm64), terminal app |
| **Model** | Wire format, endpoint, model id (e.g. `anthropic_messages`, MiMo v2.6 Flash) |
| **Duration** | Start–end, total minutes |
| **Docs used** | GETTING_STARTED.md and TUTORIAL_FIRST_PEKO.md at commit `…` |

## Results

Outcome: **Done** (alone), **Hinted** (needed a hint), **Failed** (not
completed), **Skipped**.

| # | Task | Outcome | Time | Notes |
|---|---|---|---|---|
| 1 | Install | | | |
| 2 | Connect the model | | | |
| 3 | Create the peko | | | |
| 4 | Talk to it | | | |
| 5 | Remember | | | |
| 6 | Reminder (due → arrived) | | | e.g. due 14:03, arrived 14:03 |
| 7 | Skill | | | |
| 8 | Back up (optional) | | | |

**Core loop completed:** yes / no. That means install → create → chat →
reminder set and received → skill installed and used.

## Interventions

| Task | Time | What the observer said | Why |
|---|---|---|---|
| | | | |

## Findings

Copy the block below once per finding, highest level first.

### P? — one-line title

- **Task:** #
- **What happened:** the command they typed, and the exact output or error.
- **Expected:** what they (or the guide) expected instead.
- **Impact:** what the tester did next; did they recover alone?
- **Evidence:** screenshot or log excerpt (nothing personal, no keys).
- **Issue:** link to the `ConekoAI/peko-runtime` issue (required for P0/P1).

## Debrief

1. Hardest part:
2. Wanted to give up when:
3. Expected Peko to … but it didn't:
4. Would keep using it if:
5. In one sentence, Peko is:

## Daemon health

- `peko daemon status` at the end:
- Unexpected stops or restarts during the session:
- ERROR / WARN lines from `daemon.log` (summarised):

## Gate 5 verdict

- **One non-technical-user session:** done / not done (core loop completed?
  every task attempted?)
- **P0 findings:** N. List each with its issue link. Gate 5 closes when
  every one is fixed and verified on a new release candidate.
- **Follow-ups:** P1s to fix before the MVP tag, and P2/P3s for later.
