# Observer checklist

You run the session and write the report; the tester drives. Keep your
hands off the keyboard and record what you see.

## Before the session (15 min)

- [ ] **The release exists and passed its smoke job.**
  `gh release view v0.1.0-rc.4` lists four archives. The release run's
  `smoke` jobs are green.
- [ ] **The installer fix is in.** ConekoAI/peko-runtime#509 is merged on
  `master`; the guide's `curl` command fetches `install.sh` from `master`.
  Before #509, `--install-dir ~/.local/bin` into a directory that didn't
  exist asked for `sudo` and installed nothing. If you run the session
  before it merges, that is a known P1: record it if it happens.
- [ ] **The machine is clean.** `command -v peko` prints nothing, and
  `~/.peko` doesn't exist. `curl` is installed. Note the OS and version,
  the CPU (Apple silicon, Intel, x86_64 or arm64) and the terminal app.
- [ ] **The model card is ready** (see the kit's README). The key works:
  try it on another machine, or trust a recent `peko model test`.
- [ ] **Both guides are open** in the tester's browser on GitHub (links on
  the tester script). Nothing else is open.
- [ ] **The tester agrees** to being observed and to their conversation
  being summarised in the report. Ask before recording the screen. Ask them
  not to share anything private with the peko.
- [ ] **Start a timer** for each task. Note the start time of the session.

## While they work

**Intervention rule.** Intervene only when the tester is stuck, has tried the
guide's *Troubleshooting* section, and two minutes have passed, or when they
ask. Give the smallest hint that unblocks them, and write down the task,
the time and exactly what you said. A task that needed a hint is
**Hinted**, not **Done**.

**For every problem, record** the command they typed, the exact output or
error (a screenshot or copy), what they expected, and what they did next.

### Per task

| # | Task | Done when | Watch for (seen in our own runs) |
|---|---|---|---|
| 1 | Install | `peko --version` prints a version | Where `--version 0.1.0-rc.4` goes (`bash -s -- --version …`). The `sudo` prompt for `/usr/local/bin`. `command not found` after `--install-dir`. |
| 2 | Connect the model | `model test` says *Connection successful* | The multi-line command with `\`. Quoting the key. A slow first reply: the test waits 30 s. |
| 3 | Create the peko | *is alive* | `create` waits 1–2 min for the first turn. Do they think it hung? The `Genesis: …` lines are jargon. |
| 4 | Talk to it | Three answers, and they're in `peko log` | The reply streams. `peko log` timestamps and truncation; are its lines readable? |
| 5 | Remember | It recalls the name and the like in a new message | Whether it says it saved them. It should recall without being reminded. |
| 6 | Reminder | The reminder appears in the conversation | It appears only in the conversation; there's no system notification. Do they find it (`peko log`, or `peko log --watch`)? Note the due time and the arrival time; about a minute late is normal. Known P2s, so note how the tester reacts rather than filing them again: the reminder line starts with a raw key (`📨 [did:key:…]`), and the peko then posts its own bookkeeping ("Reminder delivered… One-shot job fired…"). |
| 7 | Skill | The answer follows the skill | Pasting the `cat > … <<'EOF'` block, and the `W=…` line before it. Does the peko use the skill unprompted? |
| 8 | Back up (optional) | A `.peko` file exists in their folder | Where the file lands. |

Between tasks, glance at `peko daemon status` from a second terminal if you
can do it without disturbing them. A daemon that stopped on its own is a P0.

## Classify every finding

| Level | Meaning | Examples |
|---|---|---|
| **P0** | Blocks the core loop (the gate's definition). | Can't install; can't converse; a message or reminder is lost (it never arrives, or a reply vanishes from the log); the daemon crashes or stops. A skill that never reaches the peko at all. |
| **P1** | The task needed a hint, or the output would make a real user give up or do the wrong thing. | A misleading error; a step the guide doesn't explain; a reminder more than 5 minutes late. |
| **P2** | Friction: slow, confusing or ugly, but the tester got through alone. | Jargon in output; a long wait with no feedback. |
| **P3** | Polish and wishes. | Wording; nice-to-haves the tester mentions. |

The model's own judgment is not a runtime bug, for example a reply that is
correct but poorly phrased. Record it as P3, unless the runtime gave the
model wrong or empty input (for example, empty tool results). That is a P0
or P1 by its effect.

## Debrief (5 min)

Ask, and write down the answers in their words:

1. What was the hardest part?
2. Was there a moment you wanted to give up? When?
3. What did you think Peko would do that it didn't?
4. Would you keep using it? What would make you?
5. How would you describe Peko to a friend, in one sentence?

## Collect evidence (with the tester's consent)

From the test machine, before cleanup:

```bash
peko --version
peko daemon status
peko list
peko log <their-peko> --limit 50 > field-test-log.txt   # their conversation; summarise, don't commit
grep -E " (ERROR|WARN) " ~/.peko/logs/daemon.log | tail -50 > field-test-daemon-warnings.txt
```

Attach the warnings to the report, after removing anything personal. Don't
attach the vault, `models.toml`, or anything that could contain the key.

## Cleanup

The test machine holds the observer's key in Peko's vault. When the evidence
is collected:

```bash
peko daemon stop
rm -rf ~/.peko
rm -rf "$HOME/Library/Application Support/peko"     # macOS data directory
rm -rf ~/.local/share/peko                          # Linux data directory
sudo rm -f /usr/local/bin/peko /usr/local/bin/peko-daemon   # or the --install-dir they used
sudo rm -f /etc/systemd/system/peko@.service        # Linux with systemd only
```

Rotate the key afterwards if the machine isn't yours.

## File the report

1. Copy `REPORT_TEMPLATE.md` to `YYYY-MM-DD-<tester-initials>.md` in this
   folder and fill it in the same day.
2. Open an issue in `ConekoAI/peko-runtime` for every P0 and P1, and link
   each one from the report.
3. Commit the report to peko-benchmark, and update gate 5 in
   `peko-runtime/docs/MVP_GATE.md` with its link and the P0 count.
