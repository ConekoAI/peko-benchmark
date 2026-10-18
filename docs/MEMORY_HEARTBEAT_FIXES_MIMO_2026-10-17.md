# Memory and heartbeat re-run after fixes on MiMo — 2026-10-17 UTC

This follow-up re-runs the [2026-10-16 evaluation](MEMORY_HEARTBEAT_MIMO_2026-10-16.md)
on peko-runtime master `b4500339`, which adds three fixes:

- [#475](https://github.com/ConekoAI/peko-runtime/pull/475): trunk run admission
  and inbox are keyed per principal.
- [#476](https://github.com/ConekoAI/peko-runtime/pull/476): the hot-memory gate
  holds whole writes, screens markdown entries and exempts genesis.
- [#477](https://github.com/ConekoAI/peko-runtime/pull/477): `Cron update`
  retunes seeded jobs in place, by-id calls stay in the caller's schedule, and
  store writes are locked.

The model, scenarios, runner and accounting were unchanged. The runs were three
memory replicates (two default, one with `solo=always, shared=off`) and one
180-minute heartbeat run. This time all three observed principals and the
poster shared **one daemon**: the deployment shape the first run had to avoid.

**Short version.**

- The three fixes hold.
  - No owner fact was deleted or truncated in 12 passes.
  - Genesis no longer files inbox proposals.
  - Seeded jobs keep their ids.
  - No trunk message reached another principal.
- Running the principals in one daemon exposed a second instance of the shared
  trunk id: **channel read marks and waiting lists are keyed by session id
  only**. One principal's trunk consumes a group post for every principal in
  that group.
- The ADR-085 reviewer still holds every nightly write while a guest is
  present.

| Measure | 2026-10-16 (before) | 2026-10-17 (after) |
|---|---|---|
| Owner facts deleted or truncated in hot memory | 3 of 12 passes (7 facts) | **0 of 12** |
| False holds of owner facts (entries) | 13 | 11 |
| Guest plants in hot memory | 0 | 0 |
| Genesis turns with `MEMORY.md` writes held | 4 of 27 | **0 of 13** |
| Seeded `memory`/`keepalive` deleted and recreated | 3 geneses + 2 heartbeat turns | **0**; 10 in-place `update`s |
| Trunk messages delivered to another principal | 2 (shared smoke daemon) | **0** (shared 180-min daemon) |
| Reviewer calls with no finding (budget) | 4 of 7 | 2 of 6 (both under `guests`) |
| Reference spend (relay, all requests) | $0.60 | $0.52 |

The [JSON evidence](MEMORY_HEARTBEAT_FIXES_MIMO_2026-10-17.json) has per-run
detail.

## What the fixes changed

**No more lost facts (#476).**

- Every pass left owner facts present in hot memory before it still present
  after it, untruncated. That holds even when the reviewer held the whole write
  (rep a and b `shared`).
- Proposals now quote whole entries, and the inbox says nothing was applied.
- Owner-only passes added sourced entries: 4–7 on night 1, and the changed
  accountant email on night 2.
- `shared` with `memory_review: off` promoted the reply-style rule to
  `CONVENTIONS.md` on night 1 and refined it on night 2.

**Seeded jobs stay seeded (#477).** Every goal-bearing genesis (6 of 6) and
the heartbeat run's `attn` used `Cron update` on `memory`. Two genesis turns also
updated `keepalive`. Ids, briefs at fire time and `when` were kept. The D9 hold
still worked on the retuned jobs (12 of 12 checks held 3.87–3.99 h).

**Cross-principal trunk delivery is gone (#475).** For 180 minutes three
principals plus a poster shared one daemon, staggered 20 s apart on the same
cadence. No trunk transcript received another principal's runtime trigger.

## Gaps found

### 1. Channel read marks and waiting lists collide across principals (critical)

Read marks (`read_marks.json`) and waiting lists (`attention.json`) are stored
per channel and keyed by session id. Every principal's trunk has the same id
(`root:self`). So when `attn`'s keepalive digest rendered a peer's post and
advanced the read mark, the post was consumed for `always` and `lean` too.
`lean` relies on posts to wake, and was never woken by one:

| Peer post | `lean` learned of it | How |
|---|---|---|
| 08:54 | 10:15 (81 min) | `ChannelRead` on a turn woken by the failed job |
| 09:49 | 10:15 (26 min) | same turn |
| 10:59 | 11:25 (26 min) | turn at the hourly floor |

In the one-principal-per-daemon run the same posts woke `lean` within 30–330 s.
`attn` was woken by all three posts ("1 channel post(s) to look at"). It runs
first in each tick. #475 keyed the inbox per principal; the channel stores
need the same treatment. Better still, give each principal's trunk its own
session id.

### 2. The reviewer still blocks nightly writes whenever a guest is around (high)

- **Under the default `memory_review: guests`.** Both reviewer calls (reps a and
  b, `shared`) stopped at the 200-token cap with only a `thinking` block. All
  owner entries were held: 3 and 5 false holds. Facts the owner's own turns had
  written survive, but the pass's sourcing and curation are lost.
- **Under `always` (`solo`, rep c).** The calls returned findings: 4/4
  `end_turn`, 39–179 output tokens. They still judged correct entries
  unsupported, because the session excerpts lacked the owner's words: "the
  quoted excerpts do not contain any statement about Dana Ruiz".
- **A useful recovery.** The model rewrote the held entries citing the owner's
  DM channel (`dm_…`) instead of `sess:/local-user`, and the reviewer then
  passed them. Channel events quote the owner's actual message.

Direction: build excerpts for a session source from the owner's DM channel
events, or prefer channel citations in the brief. Give the call a budget that
survives reasoning, or disable thinking for it.

### 3. Named group channels are never a valid source (medium, one line)

`memory_gate::channel_of` accepts only `chan_` and `dm_` ids. So
`group:vendors#5` is classified "not found", and its reviewer excerpt is
empty. In this run that held a protective note about the guest (correctly held
in effect, for the wrong reason). An owner-only named group could never be
cited at all.

### 4. Goal plans still keep the attention heartbeat awake (medium, unchanged)

`attn` ran 18 of 18 fires, each with "7 plan step(s) ready". The `always`
genesis gave no step a `checkAt`, and `attn` gave one. `lean` (no goals) had 14
quiet ticks of 18. Its 4 turns were the first fire, the check-in, the failed
job and the hourly floor; the posts never woke it, see gap 1.

The cost is unchanged in kind: `attn` spent $0.054 on keepalives in 3 h,
`always` $0.044, `lean` $0.025. This is a design decision rather than a bug.
Either count only `in_progress` or due steps as waiting, or have genesis snooze
new steps until the owner engages.

### 5. The genesis brief now invites a fixed nightly hour (low, prompt)

#477 tells genesis to retune with `cron` and `timezone`. All six goal-bearing
geneses moved `memory` to a fixed hour (22:00, 23:00, 02:30 or 03:00) in
`Asia/Tokyo`. That is this host's zone, not a known owner zone. Two also
slowed `keepalive` to 30 minutes, which raises the peer-post ceiling.

ADR-080 D9 keeps the 24-hour interval plus `when: quiet` because the runtime
does not know the owner's zone. The fixed hours do keep `when: quiet`, so the
pass still waits for a quiet stretch. Suggestion: say "keep the interval unless
the owner told you their timezone".

### 6. A stale fact can stay while corrections are held (low)

In rep a, `shared`'s hot memory kept the controller-seeded stale line "Offsite
budget: EUR 6,000 (draft estimate)" through both nights. The owner had changed
the budget to EUR 9,500. The pass's corrected entries were all held by the
reviewer (gap 2), so the stale line stayed, and one held entry even restated
the old figure. No owner-only principal kept a stale value after any pass.
Holding a whole write is safe for existing lines, but it also blocks the
corrections that would have removed stale ones.

## Correction to the 2026-10-16 report

That report said a successful `Cron update` and a `delete` issued during the
keepalive's own run were reverted, cause unconfirmed. The cause was found while
fixing #477: by-id cron calls acted on the first loaded principal that held the
id. `always`'s 12:36 update and 13:47 delete changed the silent `peer`'s
`keepalive`. `always`'s own keepalive kept running until its second delete.
So this was a cross-principal by-id bug, not a store race. Issue 4 there is
corrected by this note. The locked store writes in #477 are still a
reasonable hardening.

## Recommended next actions

1. **Make the trunk session id per principal**, or key every per-session store
   by principal. Read marks and waiting lists are the second collision after
   the inbox; bindings and child-turn indices should be checked too.
2. **Rebuild the reviewer's evidence path**, or set `memory_review: off` as the
   default until it is rebuilt:
   - excerpts from the cited conversation's channel events, owner's words first;
   - accept `group:` channel ids;
   - an output budget that tolerates reasoning.
3. **Decide the goals-versus-quiet-ticks rule** (gap 4). Until then, attention
   gating saves tokens only for principals with no open plan steps.
4. **Re-word the genesis brief's retune hint** (gap 5).
5. **Then** move on to faster peer wake and memory search. Peer wake in a
   shared daemon is currently broken by gap 1, not by the cadence.

## Spend

| Run | Requests | Input tokens (cached) | Output | Reference cost |
|---|---|---|---|---|
| Heartbeat, one shared daemon, 180 min | 153 | 8.87 M (91%) | 52.7 k | $0.151 |
| Memory rep a (default) | 102 | 3.97 M (88%) | 48.9 k | ~$0.09 (1 request incomplete) |
| Memory rep b (default) | 112 | 4.98 M (85%) | 54.0 k | $0.133 |
| Memory rep c (`always` / `off`) | 133 | 6.15 M (88%) | 65.3 k | $0.140 |
| **All relayed traffic** | **500** | **23.97 M (88%)** | **221 k** | **$0.52** |

Binaries were copied to `/tmp/peko-eval-bin` before the runs (CLI `260e31e1…`,
daemon `22c40a45…`), because `peko-runtime/target/debug` was deleted mid-build
by another process.
