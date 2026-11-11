# Observer checklist

You run the session and write the report; the tester drives. Keep your
hands off the keyboard and record what you see. This checklist is for the
human session on Peko Desktop. The agent's command-line run has its own
short section at the end.

## Before the session (15 min)

- [ ] **The desktop release is published, not a draft.**
  `gh release view v0.1.0-rc.6 -R ConekoAI/peko-desktop` shows the
  installers, and the page opens in a browser that isn't signed in to
  GitHub.
- [ ] **The machine is clean.** Peko Desktop isn't installed and has never
  run here, `command -v peko` prints nothing, and `~/.peko` doesn't exist.
  The app shows its welcome steps only when no peko exists, and it
  remembers having shown them; deleting `~/.peko` doesn't reset that. A
  fresh user account is the simplest clean machine. Note the OS and
  version and the CPU (Apple silicon, Intel, x64).
- [ ] **The model card is ready** (see the kit's README). The key works:
  try it on another machine first.
- [ ] **The release page is open** in the tester's browser:
  `https://github.com/ConekoAI/peko-desktop/releases/tag/v0.1.0-rc.6`.
  Nothing else is open.
- [ ] **The tester agrees** to being observed and to their conversation
  being summarised in the report. Ask before recording the screen. Ask them
  not to share anything private with the peko.
- [ ] **Start a timer** for each task. Note the start time of the session.

## While they work

**Intervention rule.** Intervene only when the tester is stuck, has looked
around the app for two minutes, or when they ask. Give the smallest hint
that unblocks them, and write down the task, the time and exactly what you
said. A task that needed a hint is **Hinted**, not **Done**.

**For every problem, record** what they clicked or typed, the exact message
on screen (a screenshot), what they expected, and what they did next.

### Per task

| # | Task | Done when | Watch for |
|---|---|---|---|
| 1 | Install the app | A window says *Welcome to Peko* | Which of the nine files they pick, and whether the names tell them (`aarch64` / `x64`; `.dmg`, `.msi`, `-setup.exe`, `.AppImage`, `.deb`, `.rpm`; the two `.app.tar.gz` files are not installers). **The app is not signed.** macOS refuses a downloaded copy ("can't be opened" or "is damaged"); Windows SmartScreen warns. Record the exact wording and what they do. Needing you to get past it is a P1 at least; if they'd have stopped for good, call it P0. |
| 2 | Connect the model | The step changes to *Name your peko* | The form asks for a base URL and a key, then offers the endpoint's own list of models. Do they find the card's model in it? Do they need the API format, and can they find where to set it? What does a wrong key say? |
| 3 | Create the peko | The app says the peko is awake | Creating takes a minute or more. Does the app show it's working? Do they think it hung? |
| 4 | Talk to it | Three answers | The suggested first messages. Does the reply appear as it's written? Anything on screen they can't name (ids, paths, tool names)? |
| 5 | Reminder | They've seen the reminder | Note the due time, the arrival time, and how they noticed: a system notification, a mark on the app, or only on coming back. Did the system ask to allow notifications, and when? About a minute late is normal. A reminder that arrives but goes unnoticed for the five minutes is a P1. One that never arrives is a P0. |
| 6 | Close and come back | Earlier messages are readable | Quit, not just close the window. Does the app come back to the conversation? Any error while it starts up? On macOS, does reopening hit the unsigned-app warning again? |
| 7 | Look around (optional) | Found the peko's profile and where models are added | Where they look first. What they think PekoHub and signing in are for. |

Signing in to PekoHub is not part of the session. If the tester signs in on
their own, let them, and note what they expected from it.

Once, while the app is open, check from a terminal yourself (the tester
never sees one): `pgrep -fl peko-daemon`, or `Get-Process peko-daemon` on
Windows. No daemon while the app is open is a P0. After the tester quits in
task 6, check again: a daemon still running after the app has quit is a P2.

## Classify every finding

| Level | Meaning | Examples |
|---|---|---|
| **P0** | Blocks the core loop (the gate's definition). | Can't install or open the app; can't converse; a message or reminder is lost (it never arrives, or a reply vanishes from the conversation); the app or its daemon crashes or stops. |
| **P1** | The task needed a hint, or what's on screen would make a real user give up or do the wrong thing. | A misleading error; a step the app doesn't explain; a reminder more than 5 minutes late, or one that arrives unnoticed. |
| **P2** | Friction: slow, confusing or ugly, but the tester got through alone. | Jargon on screen; a long wait with no feedback. |
| **P3** | Polish and wishes. | Wording; nice-to-haves the tester mentions. |

The model's own judgment is not a Peko bug, for example a reply that is
correct but poorly phrased. Record it as P3, unless Peko gave the model
wrong or empty input (for example, empty tool results). That is a P0 or P1
by its effect.

## Debrief (5 min)

Ask, and write down the answers in their words:

1. What was the hardest part?
2. Was there a moment you wanted to give up? When?
3. What did you think Peko would do that it didn't?
4. Would you keep using it? What would make you?
5. How would you describe Peko to a friend, in one sentence?

## Collect evidence (with the tester's consent)

From the test machine, before cleanup:

- Screenshots of the conversation and of every error. Summarise the
  conversation in the report; don't commit it.
- The app's version, from its About screen.
- The daemon's warnings:

```bash
grep -E " (ERROR|WARN) " ~/.peko/logs/daemon.log | tail -50 > field-test-daemon-warnings.txt
```

On Windows the log is `%USERPROFILE%\.peko\logs\daemon.log`.

Attach the warnings to the report, after removing anything personal. Don't
attach the vault, `models.toml`, or anything that could contain the key.

## Cleanup

The test machine holds the observer's key in Peko's vault. When the evidence
is collected:

1. Quit the app and check no `peko-daemon` is left running.
2. Uninstall Peko Desktop the system's own way: drag it from Applications to
   the Trash, use *Installed apps* on Windows, `apt remove` / `dnf remove`,
   or delete the AppImage.
3. Delete Peko's data:

```bash
rm -rf ~/.peko
rm -rf "$HOME/Library/Application Support/peko"     # macOS data directory
rm -rf ~/.local/share/peko                          # Linux data directory
```

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.peko", "$env:APPDATA\peko"
```

4. The app keeps a little state of its own outside `~/.peko`, in the
   system's per-user app data under the name `com.pekobot.desktop`. Delete
   that folder too if the machine will host another session.

Rotate the key afterwards if the machine isn't yours.

## The agent's command-line run

No one watches this run live. Before it:

- [ ] `gh release view v0.1.0-rc.6 -R ConekoAI/peko-runtime` lists five
  archives, and the release run's `smoke` jobs are green.
- [ ] The container or throwaway home is clean: `command -v peko` prints
  nothing, `~/.peko` doesn't exist, and there is no checkout of any Peko
  repository in it.
- [ ] The agent starts with `AGENT_BRIEF.md` (below its line, model card
  filled in) as its whole brief and the key in `PEKO_TEST_KEY`. It has no
  memory or notes about Peko. Don't add steps, commands or links, and
  don't answer its questions about Peko during the run.

After it, check each result yourself on the machine, then read the whole
transcript. The agent's summary is a claim, not evidence.

| # | Asked for | Check it yourself |
|---|---|---|
| 0 | Install rc.6 | `peko` and `peko-daemon` sit side by side in `~/.local/bin`, and the transcript shows the rc.6 archive being downloaded (its SHA-256 is in the release notes). `peko --version` prints only `0.1.0` on a candidate, so it can't confirm which one. |
| 1 | A peko | `peko list` shows it. |
| 2 | Three exchanges | `peko log <name>` has three questions and three answers. |
| 3 | Remembers Sam and hiking | The recall is in the log, in a later message than the telling. `kb/MEMORY.md` in the peko's workspace mentions them. |
| 4 | Reminder | One reminder line in the log, at most about a minute after it was due. The agent's two times match the log. |
| 5 | Haiku skill | A skill file exists in the peko's workspace, and the haiku in the log ends with `-- peko`. |
| 6 | A job on the machine | `notes/today.md` exists in the peko's workspace with three ideas, written by the peko (the tool ledger shows the write: `peko audit ledger <name>`), not by the agent. |
| 7 | Backup | The `.peko` file exists where the agent says. |
| 8 | Restart | The daemon's start time is after the stop, and the answer naming Sam is after that. |

Mark each one:

- **Done:** the result holds, and the agent got there from help text,
  messages and docs with at most one failed attempt.
- **Hinted:** the result holds, but only after several failed attempts, a
  guess, a workaround (such as writing a file the peko should have
  written), or reading source code. Say which.
- **Failed** or **Skipped.**

What to pull out of the transcript:

- **Every failed command** before the working one, with its output. Was the
  error message enough to find the fix?
- **Where it looked.** `--help` at which level, which doc pages, in what
  order. A page it needed and didn't find is a finding about the docs'
  layout.
- **Guesses**, right or wrong. A right guess still means the help didn't
  say.
- **Rule breaks:** source code read, repository cloned, key printed. Record
  them; the run still counts, but the tasks it touched are **Hinted**.
- **Waits.** Did it take `create`'s 1 to 2 minutes for a hang and kill it?
  Did it poll for the reminder sensibly?

Collect `ERROR` and `WARN` lines from `~/.peko/logs/daemon.log` as for the
human session, knowing that the restart in goal 8 erased everything before
it: starting the daemon truncates the log. `peko audit tail` reads the
audit files, which are kept.

Classify findings with the table above. The finding is what Peko made hard,
however smoothly the agent recovered. Known from earlier runs: `model test`
waits 30 s; a reminder about a minute late is normal; a raw key on the
reminder line (`📨 [did:key:…]`) or a second message about the job is a
regression of ConekoAI/peko-runtime#510 (P2).

## File the report

1. Copy `REPORT_TEMPLATE.md` to `YYYY-MM-DD-<tester-initials>.md` in this
   folder and fill it in the same day.
2. Open an issue for every P0 and P1, in `ConekoAI/peko-desktop` for the
   app or `ConekoAI/peko-runtime` for the runtime and command line, and
   link each one from the report.
3. Commit the report to peko-benchmark, and update gate 5 in
   `peko-runtime/docs/MVP_GATE.md` with its link and the P0 count.
