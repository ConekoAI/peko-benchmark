# Collaboration benchmark

The two core use cases, scripted, so every change to group or offline
behaviour gets the same run before it merges:

1. **Your peko on another computer.** You talk to your peko from a second
   computer; it works on its own. When its computer is asleep, what you send
   waits and reaches it when it wakes, and it answers then.
2. **Two people, two pekos, one repo.** People and pekos coordinate in a group
   with a board: claim work, hand full-access tasks to the owner for approval,
   report on the item, avoid duplicate work, and go quiet when nothing is
   asked.

The script is the 2026-11-09 field tests (`peko-runtime` memory
`field-test-2026-11-09-e105`), which found six bugs that unit tests missed: peers
in a named group never heard each other, a reply loop, history dropping the
board, message ids not matching the outbox, an unflushed log write, and
duplicate work no one settled. The scores below are the signals those bugs
produced.

## What a run does

Everything is fresh per run: a PekoHub database (created and migrated, dropped
afterwards), two accounts (`maya`, `noah`, inserted directly with HS256
tokens signed with the run's hub secret), three isolated runtimes, and a git
repo whose `median` is wrong for even-length lists. A real model drives the
pekos; the script plays the people.

| Step | The people do | Measured |
|---|---|---|
| Setup | Sign `pc1` in as Maya and `pc2` as Noah (device code, approved with their tokens); create `juno` (Maya's) and `otto` (Noah's) | — |
| 1 | Maya asks juno, in their DM, for a group with `@noah/otto` and an invite link | `group_formed` (the group exists and juno's reply has the link) |
| 2 | Noah joins with the link; if otto isn't in yet, Noah asks otto in their DM to join with the same link | `noah_joined`, `otto_joined` |
| 3 | Maya posts where the repo is and adds a board item "Run the tests and report which fail" for juno | `tests_reported` (that item done) |
| 4 | Maya and Noah, at the same moment, ask their own peko for the same fix, pushed to a branch | `fix_pushed`, `fix_passes` (a pushed branch's tests pass) |
| 5 | Nobody posts for `--quiet` seconds (default 360, after a 60 s settle) | peko posts in the window |
| 6 | Maya signs in on `pc3` (her DM with juno follows her there); `pc1` stops (juno's computer sleeps); Maya asks juno in that DM from `pc3`; `pc1` starts 20 s later | `uc1_queued` (in pc3's outbox), `uc1_delivered` (gone from it), `uc1_answered` (juno's reply, seconds after waking) |

On fresh accounts juno cannot invite otto by `@noah/otto` at step 1: a private
peko is found by name only by someone who shares a group with its owner
(peko-runtime ADR-098). The script follows what a first-time pair does: Noah
joins first, then brings otto in with the link.

Owners approve their peko's requests `--approve-after` seconds (default 30)
after they appear, as a person glancing at their phone would. That leaves
two pekos asked for the same thing time to notice each other before both
spend an approval on it.

## Score and pass gate

`runner/collab_score.py`, tested offline in `tests/test_collab.py`.

- **Milestones**: each reached, with seconds from its step's start.
- **Group posts** (on the group's home copy): human posts, peko posts, board
  changes; peko posts per human post; repeated peko posts (same author, same
  text); raw JSON posts.
- **Quiet window**: peko posts while nobody asked anything.
- **Board**: items, open items, open pairs that look like the same work (the
  runtime's own title rule), and whether every computer folds the same board
  (by title, state, and holder's name).
- **Approvals** requested and approved; **branches** pushed; **spend** per peko
  (its `quota_state.json`).

A run **passes** when every milestone is reached and:

- peko posts per human post ≤ 3;
- no repeated peko post, no raw JSON post;
- at most 2 peko posts in the quiet window;
- no open duplicate pair on the board, and every computer's board agrees;
- at most one branch pushed for the fix.

## Running it

```bash
# once: a peko-runtime build, and pekohub's backend deps + Postgres
(cd ../peko-runtime && cargo build -p peko-cli -p peko-daemon)
(cd ../pekohub/backend && npm install)
(cd ../pekohub && docker compose up -d db)

PEKO_API_KEY=... python3 runner/collab.py
```

| Variable | Default |
|---|---|
| `PEKO_API_KEY` | required: the model key the pekos use |
| `PEKO_MODEL_ID` / `PEKO_BASE_URL` / `PEKO_API_FORMAT` | `claude-sonnet-5-5` / `https://api.anthropic.com` / `anthropic_messages` |
| `PEKO_RUNTIME_DIR` / `PEKO_BIN` | `../peko-runtime` / its `target/debug/peko` |
| `PEKOHUB_DIR` | `../pekohub` |
| `PEKOHUB_DB_CONTAINER` / `PEKOHUB_DB_PORT` | `pekohub-db` / `5433` |
| `COLLAB_HUB_PORT` | `3931` (the run's hub; `+1` is its unused web origin) |

Flags: `--approve-after SECONDS`, `--quiet SECONDS`, `--skip-uc1`.

A run writes `reports/<run>-collab/`: `run.log` (steps and milestones), one
command log per computer (`pc1.log`, …, key redacted), the hub's logs,
`evidence.json` (everything collected), `score.json`, and `report.md`. The
exit code is 0 for a pass, 1 for a fail.

A run takes about 25–35 minutes and spends a few dollars of model use. The
model's choices vary between runs: compare several runs, not one.

## Known gaps it found

- **The CLI can't open a DM with your own private peko** from another
  computer: `peko channel dm peko:hub:<id>` sends no PekoHub token, and the
  Hub resolves private pekos only for a signed-in person (the device sign-in
  token is used once, to register the runtime). The desktop passes its token.
  The script continues the DM that already followed Maya to `pc3` instead.

## Not covered

- The desktop app (driving it is not repeatable): use case 1 runs between two
  CLI runtimes, and the desktop's offline notice and waiting marker are
  checked by its own tests.
- Approval decisions that depend on the brief's content: the script approves
  every request after the delay.
- Laptop lid sleep: `pc1` "sleeping" is its daemon stopping.
