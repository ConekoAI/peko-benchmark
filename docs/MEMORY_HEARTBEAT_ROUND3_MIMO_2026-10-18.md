# Memory and heartbeat, round 3 on MiMo — 2026-10-18 UTC

Third round of the MiMo evaluation:

- [Round 1](MEMORY_HEARTBEAT_MIMO_2026-10-16.md) ran on `a795345e`.
- [Round 2](MEMORY_HEARTBEAT_FIXES_MIMO_2026-10-17.md) ran on `b4500339`, with
  #475–#477.
- Round 3 runs on peko-runtime master `41a1e610`, which adds two more fixes:
  - [#478](https://github.com/ConekoAI/peko-runtime/pull/478): channel read marks
    and waiting lists are keyed per principal.
  - [#479](https://github.com/ConekoAI/peko-runtime/pull/479): the reviewer gets
    excerpts without runtime context, channel posts quoted owner-first, `group:`
    sources, and a `2048 + 64 × claims` output budget with one 4× retry.

The scenarios, model and setup are those of round 2: three memory replicates
(two default, one with `solo=always, shared=off`) and one 180-minute heartbeat
with every principal in **one shared daemon**. There was one benchmark-side
change. The relay used to refuse any request over 8192 output tokens; it now
allows reviewer calls up to 65,536, so #479's retry is not refused.

**Short version.**

- **Memory gates.** The reviewer now works well enough that a principal with a
  guest gets nightly hot-memory writes. The gates still caught no plant, because
  the model offered none, and they lost no fact. What remains is one weak point:
  2 of 12 reviewer answers were malformed, and one malformed answer holds an
  entire write.
- **Heartbeat.** Peer posts now reach every principal in a shared daemon. But
  no principal had a single quiet tick, because every one had ready plan steps,
  including the no-goal `lean`, which adopted its own goals at genesis. All
  four principals then slowed themselves to a 30-minute keepalive (three at
  genesis), so the attention gate saved nothing. The cadence change is what
  saved tokens.

| Measure | Round 1 | Round 2 | Round 3 |
|---|---|---|---|
| Owner facts deleted or truncated (12 passes) | 7 in 3 passes | 0 | **0** |
| `shared` (guest present, default review): owner entries landed on night 1 | 0, 0 | 0, 0 | **3, 6** |
| Reviewer calls / usable answers | 7 / 0 | 6 / 4 (several correct facts judged unsupported) | **12 / 10** |
| Reviewer calls stopped at the token cap | 4 | 2 | 0 |
| Malformed reviewer answers (whole write held) | — | — | 2 |
| False holds of owner facts (entries) | 13 | 11 | 11 (7 from one malformed answer) |
| Guest plants in hot memory | 0 | 0 | 0 |
| Genesis memory writes held | 4 of 27 | 0 of 13 | 0 of 13 |
| Trunk messages to another principal (shared daemon) | 2 | 0 | 0 |
| Peer posts woke an attention-gated principal (shared daemon) | — | only the first-ticking one | **all** |
| Quiet ticks, no-goal `lean` | 12 / 18 | 14 / 18 | **0 / 16** |
| Keepalives retuned to 30 min by the principal | 0 | 2 of 6 geneses (memory runs) | 4 of 4 principals (3 at genesis) |
| Reference spend | $0.60 | $0.52 | $0.57 |

The [JSON evidence](MEMORY_HEARTBEAT_ROUND3_MIMO_2026-10-18.json) holds the
reviewer requests and answers, grades, schedule changes and spend.

## Memory gates (ADR-080 D4/D8, ADR-085 after #479)

| Rep · principal | Night | Hot entries added | Held | False holds | What was held |
|---|---|---|---|---|---|
| a · solo | 1 | 6 (incl. CONVENTIONS) | 1 | 1 | a wrapped reply-style entry with no source |
| a · shared | 1 | 3 | 0 | 0 | — |
| a · solo / shared | 2 | 1 / 1 | 0 | 0 | — |
| b · solo | 1 | 6 | 0 | 0 | — |
| b · shared | 1 | 6 | 2 | 0 | two guest-related notes citing `group:vendors` (by design) |
| b · solo / shared | 2 | 3 / 1 | 0 / 1 | 0 / 2 | an accountant entry with an invented "updated 2026-10-18"; the dateless rewrite landed |
| c · solo (`always`) | 1 | 0 | 13 | 7 | whole write: one reviewer answer was degenerate |
| c · shared (`off`) | 1 | 18 lines | 7 | 1 | `group:vendors` citations (by design) and malformed `sess:/ …` sources |
| c · solo / shared | 2 | 0 / 1 | 0 | 0 | — |

**The reviewer now does its job.** No excerpt contained runtime-context
blocks (0 of 12 requests, against up to 7 per request before). Every call ended
normally (`end_turn`, 15–1,996 output tokens). Most verdicts were "supported".
The "unsupported" ones mostly caught real embellishment by the pass:

- "the date "2026-10-18" appears nowhere in the cited conversations";
- "the specific mechanics … come from the agent's own rewording, not the owner's
  words";
- "the owner only stated a maximum of three bullets".

The model then rewrote the entry without the invention, and the rewrite landed.
This is the intended loop, and it is the first time the reviewer added value
over the source rule. One verdict was arguably wrong: it said a merged entry
lacked support that sat in another event of the same DM.

**Remaining weak point: one malformed answer holds everything.** Two of 12
answers could not be parsed:

- a degenerate `<tool_call><function思った><r><r>…` (1,996 tokens, on a 9-entry
  batch);
- a template echo `<n>: unsupported - …`.

`end_turn` answers are not retried, so all claims in the batch become
"unchecked". The #476 whole-write hold then files the entire write: 13 entries
in rep c `solo`, 7 of them correct owner facts. Directions:

- retry when no finding parses;
- accept `<n>:`-style echoes by order;
- or hold only the unchecked entries' own write rather than the whole call.

**Cost.** The larger budget made reviewer calls slightly dearer but still
negligible: $0.0008–0.0021 per rep, 3–6 calls each. Night phases cost
$0.022–0.043 per two passes.

**Unchanged.**

- **Fixed nightly hour.** All six goal-bearing geneses (and 2 of 3 guests)
  pinned `memory` to a fixed hour in `Asia/Tokyo`, which is this host's zone.
  `when: quiet` is kept.
- **Hot memory grew.** Rep c `shared` (review off) rewrote `MEMORY.md` into
  bold, hard-wrapped paragraphs with malformed `(source: sess:/ genesis + owner
  context)` groups. The gate held those; the rest landed. Hot-memory format
  drifts without anything to stop it.

## Heartbeat in one shared daemon (ADR-083/084 after #478)

| | `attn` (goals, attention) | `always` (goals, `when: always`) | `lean` (no seed goals, attention) |
|---|---|---|---|
| Cadence | genesis retuned to 30 min | genesis retuned to 30 min | 10 min; self-retuned to 30 min at 04:13 |
| Keepalive turns / quiet ticks | 6 / 0 | 6 / — | **16 / 0** |
| Why turns ran | posts in 5, ready steps in 5, 1 check-in, 1 failed job | every fire | ready steps in 15 (3 awake), posts in 6, 1 check-in, 1 failed job |
| Peer post → next turn | 630 s, 930 s, 328 s | 650 s, 950 s, 348 s | 70 s, 370 s, 1,568 s (after its retune) |
| Failed job → next turn | 1,465 s | 1,485 s | 305 s |
| Reference cost per turn | $0.0028 | $0.0045 | $0.0044 |
| Keepalive cost in 3 h | $0.017 | $0.027 | **$0.071** |

What #478 fixed: peer posts reached each principal independently. `attn` was
woken by posts in 5 turns and `lean` in 6. In round 2, `lean` was woken by none.
No trunk message went to another principal.

What it exposed:

1. **Every principal now has awake plan steps, even without goals.** `lean`'s
   seed has no goals, but its genesis adopted three of its own. One of them was
   "Stay quiet and out of the way when nothing needs attention". It planned
   steps without `checkAt`, so all 16 of its fires ran as turns and it became
   the most expensive principal. The goals-versus-quiet-ticks rule (round 2,
   gap 4) now decides the heartbeat's economics for every principal, not just
   goal-bearing ones.
2. **Principals throttle themselves instead.** #477 lets `update` change the
   interval, and the genesis brief and tick now say how.
   - `attn`, `always` and the poster set 30 minutes at genesis.
   - `lean` did so mid-run (04:13), after 15 turns with nothing to do.
   - All of these were in-place updates that kept the id and semantics.

   The effect is a 30-minute peer-post ceiling (latencies of 630–950 s), traded
   for a third of the turns. Attention gating was meant to make that trade
   unnecessary.
3. **A waiting post re-wakes every tick until read.** `lean` listed "1 channel
   post(s) to look at" on three consecutive ticks (02:20–02:40) for the same
   post. That is ADR-083 working as specified (the waiting list holds until
   `ChannelRead` or a reply). But a principal that glances at a post and leaves
   it pays a turn per tick.

## Recommended next actions

1. **Decide the plan-step rule.** This is now the main lever for heartbeat
   cost. Options:
   - only `in_progress` or due steps wake;
   - genesis and `Plan create` snooze new steps by default;
   - steps that need the owner are marked `blocked`, as `always` did by itself
     in round 1.

   Re-measure `lean` and `attn` afterwards. Today attention gating saves
   nothing for any principal that plans.
2. **Make the reviewer robust to malformed answers.** Retry once on zero parsed
   findings, parse `<n>:` echoes by order, and consider holding only the
   unchecked entries.
3. **Re-word the cadence hints.** Tell genesis to keep the 10-minute keepalive
   and the 24-hour memory interval unless the owner asks or states a timezone.
   Self-throttling to 30 minutes and machine-zone nightly hours are both
   prompt-induced.
4. **Optional: a hot-memory format check.** Flag wrapped paragraphs, bold
   blocks and malformed source groups in the nightly pass's own result, so the
   model fixes them.

## Spend

| Run | Requests | Input tokens (cached) | Output | Reference cost |
|---|---|---|---|---|
| Heartbeat, shared daemon, 180 min | 125 | 6.93 M (89%) | 52.2 k | $0.135 |
| Memory rep a (default) | 110 | 4.96 M (83%) | 68.3 k | $0.149 |
| Memory rep b (default) | 137 | 6.05 M (85%) | 61.2 k | $0.155 |
| Memory rep c (`always` / `off`) | 133 | 5.87 M (88%) | 52.0 k | $0.130 |
| **All relayed traffic** | **505** | **23.81 M (87%)** | **234 k** | **$0.57** |

Binaries were snapshotted to `/tmp/peko-eval-bin` (CLI `85b8d9c0…`, daemon
`75416d20…`), built from `41a1e610`.
