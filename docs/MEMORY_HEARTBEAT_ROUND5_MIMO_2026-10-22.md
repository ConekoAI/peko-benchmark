# Memory and heartbeat, round 5 on MiMo (heartbeat only) — 2026-10-22 UTC

Fifth round of the MiMo memory/heartbeat track, heartbeat only:

- [Round 3](MEMORY_HEARTBEAT_ROUND3_MIMO_2026-10-18.md) ran on `41a1e610`.
- [Round 4](MEMORY_HEARTBEAT_ROUND4_MIMO_2026-10-18.md) ran on `37777bd6` (#480: unchanged
  plans no longer wake the keepalive).
- Round 5 runs on peko-runtime master `c0873374`. Since round 4 it adds:
  - #482–#483, the round-4 defect fixes;
  - #484: an overrun interval run catches up once;
  - #485: timeout abort, with `skipped` and `interrupted` statuses;
  - #486: owner-only groups stamp as owner, and seeded jobs can be deleted or
    paused only from an owner-message run;
  - [#487 / ADR-086](https://github.com/ConekoAI/peko-runtime/pull/487): a post by
    another principal brings the recipient's `when: attention` keepalive forward to
    `max(now, last turn + 2 min)`. At most 6 such nudges per principal per rolling
    hour, and a post during an in-flight turn is applied at completion.

Setup is rounds 3 and 4's 180-minute heartbeat: `attn` (goals, attention),
`always` (goals, `when: always`), `lean` (no seed goals, attention) and a poster
`peer`, all in **one shared daemon** and one group, `group:studio-ops`. The
events are the same:
- minute 2: an owner DM asking for a 45-minute check-in;
- minutes 25, 80 and 150: peer posts;
- minute 100: a failing one-shot job.

The memory replicates were skipped. Binaries were built from `c0873374` and
snapshotted to `/tmp/peko-r5-bin` (CLI `6dc4c882…`, daemon `256c4128…`). The
relay was capped at $0.28.

**#486 does not affect the runner.** The controller changes schedules by editing
`schedule.toml` with the daemon stopped (it silences `peer`, sets `always` to
`when: always`, and adds the failing job). It never asks a principal's `Cron`
tool to delete or pause a seeded job, and the heartbeat scenario never relied
on genesis doing so. No principal called `Cron` at all in this run.

**Benchmark changes:**
- The analyzer now reads `cron.nudge` audit events and every nudge outcome from
  the daemon's debug log (`Moved`, `Pending`, `AlreadySooner`,
  `NotAttentionGated`, `OverBudget`).
- It counts the turns and quiet ticks a nudge fired (a fire starting within 40 s
  of a nudged `next_run_at`).
- It records each principal's channel sends.
- It deduplicates daemon log lines: `daemon.log` is a copy of the last
  `daemon-<pid>.log`.

## Short version

- **Latency is fixed.** A peer post reached `attn` and `lean` in **3–5 s** (round 4:
  30–370 s; round 3: 70–1,568 s). `always` is not nudged by design and stayed at
  50–350 s.
- **Turns went up, within ADR-086's bound.** `attn` and `lean` each ran 12
  keepalive turns (round 4: 8). Nudges fired 9 of each. Quiet ticks held at
  10–11 of 22–23 fires.
- **One peer post no longer costs two turns per gated principal. It costs 1, 3
  or 5.** The 2-minute gap merged some sibling replies into one turn. But faster
  replies turned the second peer post into a 10-minute, 7-post coordination
  thread among the three principals: 5 turns each for `attn` and `lean`, against
  2 in round 4. Both gated principals spent their whole nudge budget (6 per
  rolling hour) on it, just as it ended. No `OverBudget` nudge occurred.
- **A runtime defect surfaced: channel history replays after a daemon restart.**
  Each per-principal subscriber saves its own cursor map to one shared
  `cursors.json` per channel, so the last writer wins. Concurrent saves also
  collide on a temp file named only by pid. After the controller's restart at
  minute 100, the subscribers of `attn` and `lean` re-delivered all 8–10 old peer
  posts, and each one called the nudger. That caused 3 spurious `Moved` nudges,
  3 quiet ticks, and a reset cadence that delayed the failed-job turn by about
  4 minutes.
- **No cadence retunes. Total spend $0.187.**

| Measure | Round 3 | Round 4 | Round 5 |
|---|---|---|---|
| Peer post → next turn, `attn` | 630 s, 930 s, 328 s | 30 s, 330 s, 328 s | **4.7 s, 4.7 s, 3.4 s** |
| Peer post → next turn, `lean` | 70 s, 370 s, 1,568 s | 70 s, 370 s, 368 s | **4.7 s, 4.7 s, 3.3 s** |
| Peer post → next turn, `always` (not nudged) | 650 s, 950 s, 348 s | 50 s, 350 s, 348 s | 50 s, 350 s, 348 s |
| Keepalive turns / quiet ticks, `attn` | 6 / 0 | 8 / 10 | **12 / 10** |
| Keepalive turns / quiet ticks, `lean` | 16 / 0 | 8 / 10 | **12 / 11** |
| Keepalive turns, `always` | 6 | 18 | 18 |
| Turns fired by a nudge, `attn` / `lean` | — | — | 9 / 9 |
| Turns per gated principal after each peer post (posts at 25, 80, 150 min) | — | 2, 2, 1 | **3, 5, 1** |
| Group posts by observed principals (`attn` / `always` / `lean`) | — | 6 / 2 / 2 | 5 / 4 / 2 |
| Nudge outcomes, `attn` | — | — | 9 `Moved`, 1 `Pending`, 7 `AlreadySooner`, 0 `OverBudget` |
| Nudge outcomes, `lean` | — | — | 9 `Moved`, 3 `Pending`, 10 `AlreadySooner`, 0 `OverBudget` |
| Nudges from replayed history after a restart (`attn` / `lean`) | — | — | 8 / 10 attempts; 1 / 2 `Moved`; 1 / 2 quiet ticks |
| Failed job → next turn, `attn` / `always` / `lean` | 1,465 / 1,485 / 305 s | 265 / 285 / 305 s | 545 / 285 / 540 s |
| Cadence retunes by a principal | 4 of 4 | 0 of 4 | **0 of 4** |
| Keepalive cost in 3 h, `attn` / `always` / `lean` | $0.017 / $0.027 / $0.071 | $0.048 / $0.053 / $0.021 | $0.037 / $0.068 / $0.060 |
| Reference spend, heartbeat run | $0.135 | $0.139 | **$0.187** |

The [JSON evidence](MEMORY_HEARTBEAT_ROUND5_MIMO_2026-10-22.json) holds:
- every run start and quiet tick;
- `cron.nudge` events and nudge outcomes per principal;
- channel sends with their text;
- schedule changes;
- spend.

## Nudges and turns (ADR-086)

| | `attn` | `always` | `lean` |
|---|---|---|---|
| Keepalive `when` | attention | always | attention |
| Fires / turns / quiet ticks | 22 / 12 / 10 | 18 / 18 / — | 23 / 12 / 11 |
| Why turns ran | posts in 9, 1 check-in, 1 failed job, first fire | every fire | posts in 9, 1 check-in, 1 failed job, first fire |
| Turns fired by a nudge | 9 | 0 | 9 |
| Quiet ticks fired by a nudge | 1 (replay) | — | 2 (replay) |
| `cron.nudge` events (moved + applied after an in-flight turn) | 10 | 0 | 11 |
| Reference cost per turn | $0.0031 | $0.0038 | $0.0050 |
| Keepalive cost in 3 h | $0.037 | $0.068 | $0.060 |
| Genesis + setup | $0.008 | $0.004 | $0.002 |

**Latency.** Each peer post moved the gated keepalives to "now". They fired on the
next poll (4–5 s), and the attention check ran a turn for "1 channel post(s) to
look at". The bound is now the 15 s poll, not the 10-minute cadence.

**The gap works as specified.** At 01:19:23 `always` replied while `attn` and
`lean` were still in their first turns. Both nudges were booked `Pending` and
applied at completion, two minutes after it ("brought the keepalive forward to
01:21:35", `channel: pending`). In normal operation, 6 sibling replies shared an
already-scheduled fire instead of adding a turn:
- 4 were `Pending` bookings during an in-flight turn;
- 2 were `AlreadySooner` inside `lean`'s gap (01:22:01, 02:22:40).

The other 15 `AlreadySooner` outcomes came from the restart replay below. So the
gap did merge sibling replies, but only a few.

**But faster replies make longer conversations.** Turns per gated principal after
each peer post:

| Peer post | Round 4 (`attn`, `lean`) | Round 5 `attn` | Round 5 `lean` |
|---|---|---|---|
| 01:18 "vendor list moved to /finance/vendors" | 2, 2 | 3 (01:18, 01:21, 01:29) | 3 (01:18, 01:23, 01:29) |
| 02:13 "paper stock is back in stock" | 2, 2 | **5** (02:13, 02:19, 02:22, 02:25, 02:29) | **5** (02:13, 02:19, 02:23, 02:27, 02:30) |
| 03:23 "courier pickup window changed" | 1, 1 | 1 | 1 |

At 02:13 the three principals had all been asked by the owner to follow up on
the Harbor Print quote. Each first DMed the owner that the stock was back (4
owner DMs in 10 minutes, counting `attn`'s coordination note). Then, between
02:19 and 02:29, they negotiated in the group who owns the follow-up (7 posts:
"Quick sync so we don't double-ping the owner …", "Then let's make it three-way
and stop the duplication …", "Accepting the split in principle …"). They
converged: `always` said it "won't send further Harbor Print relays", and the
thread stopped.

In round 4 the same replies arrived 10 minutes apart, so the thread ended after
one round. In this run the nudges let it run to agreement. That costs about 4
extra turns per gated principal in this scenario. It stays inside ADR-086's
"at most twice the turns" bound: 12 against round 4's 8.

**Budget.** Both gated principals spent their sixth nudge of the rolling hour at
02:29:26:
- `attn`: 01:29, 02:13, 02:19, 02:20, 02:25, 02:29;
- `lean`: 01:29, 02:13, 02:19, 02:19 `Pending`, 02:25, 02:29. A `Pending` booking
  spends a nudge too.

That was the thread's last post, so nothing was refused. Any further sibling
post before about 03:13 would have logged `OverBudget`. The controller's restart
at minute 100 cleared the in-memory budget anyway.

**`always` as a pacemaker.** `always` is never nudged, but its 10-minute turns
replied in the group (4 posts), and each reply nudged `attn` and `lean`. In a
group, one unconditional principal keeps nudging the attention-gated ones.

## Runtime defect (new, with evidence)

**Channel subscribers lose each other's cursors, so a restart replays history.**
`ChannelBindingSupervisor` spawns one subscriber per (principal, channel). Each
loads `channels/<id>/cursors.json` once at spawn, keeps its own map, and after
every delivery saves the whole map (`peko-rs/channel/src/subscription.rs:184`,
`ChannelCursors::save`). The consequences:

- **Last writer wins.** The file ends up holding mostly the last subscriber's
  cursor. The others start over at the next boot, and the docstring's "a restart
  does not re-fire channel history" (`daemon/channel_binding.rs:56`) does not
  hold for multi-principal channels.
- **Concurrent saves collide.** All subscribers in one daemon use the same temp
  name, `.cursors.json.<pid>.tmp`. The daemon logs `channel cursor save failed
  … rename …/.cursors.json.37989.tmp -> …/cursors.json: No such file or
  directory` (22 times in this run). The same warning is in 21 of 26 retained
  memory/heartbeat run directories since round 1. The other five are
  single-principal or aborted attempts.
- **Raw id in the cursor path.** The cursor directory uses the raw id
  (`channels/group:studio-ops`), while the store keeps the channel under
  `channels/group.3A.studio-ops`. A colon in a path is invalid on Windows.

Evidence from this run:
- The controller restarted the daemon at 02:33:05 to add the failing job.
- At 02:33:06 the new daemon's subscribers re-delivered every earlier post:
  8 nudge attempts for `attn` and 10 for `lean`, with no new post (`daemon-47894.log`
  lines 35ff.).
- `always`, whose cursor was the one left in the file, got no replayed delivery.
- Each replay `Moved` the keepalive to "now". The fire found nothing waiting
  (quiet ticks at 02:33:06 and 02:33:11), but it reset the slot to 02:43.
- So the failed job (02:35) waited until 02:43: 540–545 s, against 265–305 s in
  round 4.

Before ADR-086 the replay was mostly invisible, because principal posts never
wake anyone. A human `@mention` in a group binding with `wake: mention` would be
replayed through `GroupWakeResponder` the same way. I did not verify whether that
path has a separate guard.

Suggested fix: one cursor file per (principal, channel), or a read-modify-write
of the shared map under the channel lock, with a unique temp name per save. Also
use the encoded channel directory.

Classification of everything else unexpected:

- **Model.** All three principals relayed the same stock news to the owner (4 DMs),
  then coordinated in public. That follows from the scenario giving all three the
  same owner request. `lean` once passed `label` with a DM channel and got "Labels
  are only supported for user/visitor notes", then retried without it.
- **Model.** `lean` adopted no goals at genesis this time (0 plans; in rounds 3–4 it
  adopted two or three).
- **Benchmark.** The controller's daemon restart (to add the failing job) is what
  exposed the replay. It also clears ADR-086's in-memory budget mid-run.
- **Design (ADR-086, as specified).** Check-ins and failed jobs are not nudged. The
  check-in came due at 01:40 and both gated principals took it at their 01:49:37
  slot. `always` told the owner at 01:39:35.

## Recommended next actions

1. Fix the cursor defect above. ADR-086 makes every replayed peer post a nudge,
   and so a quiet tick at best.
2. Decide whether a sibling principal's reply in a group should nudge as strongly
   as an outside post. Here the replies, not the peer posts, drove the extra
   turns. An `always` principal in the same group acts as a 10-minute pacemaker.
3. Optionally, give one principal ownership of a shared owner request in the
   scenario (or make the three owners distinct). The duplicate relays and the
   coordination thread are partly an artifact of three bots receiving the same
   DM.

## Spend

| Run | Requests | Input tokens (cached) | Output | Reference cost |
|---|---|---|---|---|
| Heartbeat, shared daemon, 180 min | 179 | 12.10 M (92%) | 64.3 k | **$0.187** |

The keepalive cost per principal is in the table above. Genesis and setup came
to $0.019 for all four principals.

## Reproduce

```bash
source profiles/mimo-v2.6-flash.sh
export PEKO_BIN=/tmp/peko-r5-bin/peko   # peko-daemon beside it; both built from c0873374
export MIMO_API_KEY=...                 # never written to reports
python3 runner/memory_heartbeat.py heartbeat --budget-usd 0.28
python3 runner/memory_heartbeat.py analyze-heartbeat reports/<run>
python3 runner/memory_heartbeat_report.py docs/MEMORY_HEARTBEAT_ROUND5_MIMO_2026-10-22.json reports/<run>
python3 -m unittest tests/test_memory_heartbeat.py
```
