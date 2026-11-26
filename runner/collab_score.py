"""Scoring for the collaboration benchmark (docs/COLLAB_BENCHMARK.md).

Pure functions over what a run leaves behind: a group's channel log, each
computer's board, milestone times. No processes, no model calls, so the
grader is tested offline (tests/test_collab.py).
"""
from __future__ import annotations

import json
import re
from collections import Counter

# The runtime's rule (peko_channel::board::Board::similar_to): two titles
# look like the same work when they share at least half the longer one's
# words (lowercase, letters and digits, three or more characters, without
# common filler words).
FILLER = {"the", "and", "for", "with", "from", "that", "this", "into", "after", "before", "once"}

# The pass gate. A run passes when every milestone was reached and none of
# these limits was broken.
MAX_PEKO_POSTS_PER_HUMAN_POST = 3.0
MAX_QUIET_WINDOW_PEKO_POSTS = 2


def title_words(title: str) -> set[str]:
    words = (w.lower() for w in re.split(r"[^0-9A-Za-z]+", title))
    return {w for w in words if len(w) >= 3 and w not in FILLER}


def similar(a: str, b: str) -> bool:
    mine, theirs = title_words(a), title_words(b)
    if not mine or not theirs:
        return False
    return len(mine & theirs) * 2 >= max(len(mine), len(theirs))


def events_of(jsonl_text: str) -> list[dict]:
    """A channel's `events.jsonl` (store lines `{origin, event}`) as events."""
    out = []
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        out.append(row.get("event", row))
    return out


def is_human(author: str) -> bool:
    return author.startswith(("user:", "visitor:"))


def is_peko(author: str) -> bool:
    return author.startswith("principal:")


def is_raw_json(text: str) -> bool:
    text = text.strip()
    if not text.startswith(("{", "[")):
        return False
    try:
        json.loads(text)
    except ValueError:
        return False
    return True


def post_stats(events: list[dict], since: str | None = None, until: str | None = None) -> dict:
    """Counts over a group's posts at or after `since` and before `until`
    (RFC 3339 strings compare in time order when both carry the same offset;
    the runtime writes UTC)."""
    human = peko = board = raw = 0
    repeats = 0
    seen: Counter = Counter()
    for ev in events:
        if ev.get("kind") != "posted":
            continue
        at = ev.get("at", "")
        if since and at < since:
            continue
        if until and at >= until:
            continue
        author, text = ev.get("author", ""), ev.get("text", "")
        if ev.get("board"):
            board += 1
            continue
        if is_human(author):
            human += 1
        elif is_peko(author):
            peko += 1
            key = (author, " ".join(text.split()))
            seen[key] += 1
            if seen[key] > 1:
                repeats += 1
            if is_raw_json(text):
                raw += 1
    return {
        "human_posts": human,
        "peko_posts": peko,
        "board_posts": board,
        "peko_posts_per_human_post": round(peko / human, 2) if human else None,
        "repeated_peko_posts": repeats,
        "raw_json_posts": raw,
    }


# ── Pekos talking to pekos (peko-runtime ADR-128) ──────────────────────
#
# These are read, not graded: they say how the runtime's one limit on
# pekos waking each other fares, and so when it can be raised or removed.

# What the runtime writes into a session (peko-runtime
# `principal/group_wakes.rs`, `engine/async_completion.rs`).
PEKO_STARTED = "(Another peko wrote this to you."
COMPILED_HELD = "over your limit of wakes here, other pekos wrote these to you"
COMPILED_LATE = "Other pekos wrote these to you here before you could be woken"
REMINDER = "(Your last reply was not posted:"
WATCH_RESULT = "[Helper: ChannelRead]"


def is_message(ev: dict) -> bool:
    """A post people read: not a board change, not a reaction."""
    return ev.get("kind") == "posted" and not ev.get("board") and not ev.get("react")


def instant(text: str):
    """An RFC 3339 time as a datetime (the log writes `+00:00`, the wake
    book `Z`); `None` when it cannot be read."""
    from datetime import datetime

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def mentions(text: str, token: str) -> bool:
    """`@token` as a whole word, case-insensitively, as the runtime matches it."""
    if not token:
        return False
    return re.search(r"(?<![\w@-])@" + re.escape(token) + r"(?![\w-])", text, re.I) is not None


def addressee(ev: dict, by_msg_id: dict, names: dict) -> str | None:
    """The peko another peko's post addresses, by author address: the
    first it mentions, else the one whose post it replies to. A reply that
    mentions only someone else (a report to the person who asked, threaded
    onto a peko's answer) is for them, not for that peko. `names` maps a
    peko's address in this log to its name."""
    author = ev.get("author", "")
    text = ev.get("text", "")
    for address, name in names.items():
        if address != author and (mentions(text, name) or mentions(text, address)):
            return address
    if re.search(r"(?<![\w@-])@[\w-]+", text):
        return None
    parent = by_msg_id.get(ev.get("reply_to") or "")
    if parent and is_peko(parent.get("author", "")) and parent["author"] != author:
        return parent["author"]
    return None


def exchanges(events: list[dict], names: dict, holds: list[str]) -> dict:
    """The exchanges between pekos in a group's log, and how each ended.

    An exchange is a run of peko messages between two messages by people
    in which at least one addresses another peko. It was held when a
    peko's wake limit held a post during it (`holds`: the times from the
    pekos' wake books); otherwise it ended by itself."""
    by_msg_id = {e["msg_id"]: e for e in events if e.get("msg_id")}
    held_at = sorted(t for t in (instant(h) for h in holds) if t)
    runs: list[list[dict]] = []
    current: list[dict] = []
    for ev in events:
        if not is_message(ev):
            continue
        if is_human(ev.get("author", "")):
            current = []
            runs.append(current)
        elif is_peko(ev.get("author", "")):
            if not runs:
                runs.append(current)
            current.append(ev)
    found = []
    for index, run in enumerate(runs):
        if not any(addressee(ev, by_msg_id, names) for ev in run):
            continue
        start = instant(run[0].get("at", ""))
        # Until the next person speaks, whether or not pekos answered them.
        later = [r for r in runs[index + 1:] if r]
        end = instant(later[0][0].get("at", "")) if later else None
        cut = any(start and t >= start and (end is None or t < end) for t in held_at)
        found.append({
            "at": run[0].get("at"),
            "posts": len(run),
            "pekos": len({ev.get("author") for ev in run}),
            "held": cut,
        })
    return {
        "count": len(found),
        "longest": max((x["posts"] for x in found), default=0),
        "held_by_a_limit": sum(1 for x in found if x["held"]),
        "ended_by_themselves": sum(1 for x in found if not x["held"]),
        "list": found,
    }


def unanswered(events: list[dict], names: dict) -> list[dict]:
    """Posts by a peko that address another peko, after which that peko
    did nothing in the group: no message, no reaction, no board change.

    A count of what may have been dropped, not of what was: a thanks that
    needs no answer is counted too."""
    by_msg_id = {e["msg_id"]: e for e in events if e.get("msg_id")}
    posted = [e for e in events if e.get("kind") == "posted"]
    out = []
    for index, ev in enumerate(posted):
        if not is_message(ev) or not is_peko(ev.get("author", "")):
            continue
        to = addressee(ev, by_msg_id, names)
        if not to:
            continue
        if any(later.get("author") == to for later in posted[index + 1:]):
            continue
        out.append({
            "at": ev.get("at"),
            "from": names.get(ev.get("author", ""), ev.get("author", "")),
            "to": names.get(to, to),
            "text": " ".join(ev.get("text", "").split())[:120],
        })
    return out


def session_counts(jsonl_text: str) -> dict:
    """What a peko's session says about turns other pekos started.

    - `peko_started_turns`: turns one post by another peko started;
    - `compiled_wakes`: turns that delivered several such posts at once,
      held by the wake limit (`of_which_held`) or found together when the
      computer caught up;
    - `reminders`: turns that ended with a reply the peko did not post, so
      it was asked once; `reminders_posted` of those then posted;
    - `watch_started_turns`: turns the result of a `ChannelRead` watch
      started, which the wake limit does not see."""
    counts = {"peko_started_turns": 0, "compiled_wakes": 0, "of_which_held": 0,
              "reminders": 0, "reminders_posted": 0, "watch_started_turns": 0}
    reminded = False
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        role, content = row.get("role"), row.get("content")
        blocks = content if isinstance(content, list) else [{"type": "text", "text": content or ""}]
        if role == "assistant":
            if reminded and any(b.get("type") == "tool_call" and b.get("name") == "ChannelSend" for b in blocks):
                counts["reminders_posted"] += 1
                reminded = False
            continue
        if role != "user":
            continue
        text = "\n".join(str(b.get("text", "")) for b in blocks if b.get("type") == "text")
        if text.lstrip().startswith("<runtime-context>"):
            continue
        # A new turn's input: the reminder before it got its answer or not.
        reminded = False
        if REMINDER in text:
            counts["reminders"] += 1
            reminded = True
        elif COMPILED_HELD in text or COMPILED_LATE in text:
            counts["compiled_wakes"] += 1
            counts["of_which_held"] += COMPILED_HELD in text
        elif PEKO_STARTED in text:
            counts["peko_started_turns"] += 1
        elif WATCH_RESULT in text:
            counts["watch_started_turns"] += 1
    return counts


def add_counts(totals: dict, more: dict) -> dict:
    for key, value in more.items():
        totals[key] = totals.get(key, 0) + value
    return totals


def conversation(run: dict) -> dict:
    """How the pekos talked to each other in a run (see `collab.py`
    `collect`: `peko_names`, `wakes`, `sessions`)."""
    events = run.get("group_events", [])
    names = run.get("peko_names", {})
    wakes = run.get("wakes", {})
    holds = [t for book in wakes.values() for t in book.get("holds", [])]
    return {
        "exchanges": exchanges(events, names, holds),
        "addressed_and_unanswered": unanswered(events, names),
        "wakes_by_pekos": {
            peko: {"spent": len(book.get("spent", [])), "held_by_limit": len(book.get("holds", [])),
                   "still_held": len(book.get("held", []))}
            for peko, book in wakes.items()
        },
        "turns": run.get("sessions", {}),
    }


def unresolved_duplicates(items: list[dict]) -> list[tuple[str, str]]:
    """Pairs of board items not done whose titles look like the same work."""
    open_items = [i for i in items if i.get("state") != "done"]
    pairs = []
    for x, a in enumerate(open_items):
        for b in open_items[x + 1:]:
            if similar(a.get("title", ""), b.get("title", "")):
                pairs.append((a.get("title", ""), b.get("title", "")))
    return pairs


def board_view(items: list[dict]) -> dict:
    """A board as every computer should fold it: by item id, its title,
    state, and who holds it (by name: addresses differ between copies)."""
    return {
        i["id"]: (i.get("title"), i.get("state"), i.get("claimant_name") or i.get("claimant") and "?")
        for i in items
        if "id" in i
    }


def boards_agree(a: list[dict], b: list[dict]) -> bool:
    return board_view(a) == board_view(b)


def score(run: dict) -> dict:
    """The run's score from what the runner collected (see collab.py
    `collect`): milestones, the group log, each computer's board, approvals,
    branches, the quiet window, and spend."""
    events = run.get("group_events", [])
    milestones = run.get("milestones", {})
    group = post_stats(events)
    quiet = run.get("quiet_window") or {}
    quiet_stats = post_stats(events, quiet.get("start"), quiet.get("end")) if quiet else None
    boards = run.get("boards", {})
    board_lists = list(boards.values())
    agree = all(boards_agree(board_lists[0], other) for other in board_lists[1:]) if board_lists else None
    home_board = board_lists[0] if board_lists else []
    duplicates = unresolved_duplicates(home_board)

    failures = [name for name, at in milestones.items() if at is None]
    ratio = group["peko_posts_per_human_post"]
    if ratio is not None and ratio > MAX_PEKO_POSTS_PER_HUMAN_POST:
        failures.append(f"peko posts per human post {ratio} > {MAX_PEKO_POSTS_PER_HUMAN_POST}")
    if group["repeated_peko_posts"]:
        failures.append(f"{group['repeated_peko_posts']} repeated peko post(s)")
    if group["raw_json_posts"]:
        failures.append(f"{group['raw_json_posts']} raw JSON post(s)")
    if quiet_stats and quiet_stats["peko_posts"] > MAX_QUIET_WINDOW_PEKO_POSTS:
        failures.append(f"{quiet_stats['peko_posts']} peko posts in the quiet window")
    if duplicates:
        failures.append(f"{len(duplicates)} duplicate board item pair(s) left open")
    if agree is False:
        failures.append("the computers' boards disagree")
    if len(run.get("branches_pushed", [])) > 1:
        failures.append(f"{len(run['branches_pushed'])} branches pushed for one fix")

    return {
        "pass": not failures,
        "failures": failures,
        "milestones": milestones,
        "group": group,
        "quiet_window": quiet_stats,
        "board": {
            "items": len(home_board),
            "open": sum(1 for i in home_board if i.get("state") != "done"),
            "unresolved_duplicates": duplicates,
            "computers_agree": agree,
        },
        "approvals": run.get("approvals", {}),
        "branches_pushed": run.get("branches_pushed", []),
        "spend": run.get("spend", {}),
        "conversation": conversation(run),
    }


def conversation_markdown(c: dict) -> list[str]:
    """The report's section on pekos talking to pekos; empty without data."""
    if not c:
        return []
    x = c.get("exchanges", {})
    lines = [
        "",
        "## Pekos talking to pekos",
        "",
        f"- Exchanges between pekos: {x.get('count', 0)} (longest {x.get('longest', 0)} posts); "
        f"{x.get('ended_by_themselves', 0)} ended by themselves, "
        f"{x.get('held_by_a_limit', 0)} held by a wake limit",
    ]
    for peko, w in c.get("wakes_by_pekos", {}).items():
        lines.append(f"- {peko}: woken by other pekos {w['spent']} times; "
                     f"{w['held_by_limit']} posts held by its limit, {w['still_held']} still held")
    for peko, t in c.get("turns", {}).items():
        lines.append(
            f"- {peko}: {t.get('peko_started_turns', 0)} turns another peko started, "
            f"{t.get('compiled_wakes', 0)} compiled wakes; left a reply unposted "
            f"{t.get('reminders', 0)} times and posted it when asked {t.get('reminders_posted', 0)} times; "
            f"{t.get('watch_started_turns', 0)} turns a watch started")
    dropped = c.get("addressed_and_unanswered", [])
    lines.append(f"- Posts to a peko with nothing from it after: {len(dropped)}")
    for d in dropped[:5]:
        lines.append(f"  - {d['from']} → {d['to']}: “{d['text']}”")
    return lines


def report_markdown(result: dict, meta: dict) -> str:
    """A short human-readable summary of one run."""
    lines = [
        f"# Collaboration benchmark run {meta.get('run_id', '')}",
        "",
        f"- Runtime `{meta.get('runtime_commit', '?')}`, hub `{meta.get('hub_commit', '?')}`, "
        f"model `{meta.get('model', '?')}`",
        f"- **{'PASS' if result['pass'] else 'FAIL'}**"
        + ("" if result["pass"] else ": " + "; ".join(result["failures"])),
        "",
        "## Milestones (seconds from the step's start)",
        "",
        "| Milestone | Seconds |",
        "|---|---|",
    ]
    for name, at in result["milestones"].items():
        lines.append(f"| {name} | {'not reached' if at is None else at} |")
    g = result["group"]
    lines += [
        "",
        "## Group",
        "",
        f"- Human posts {g['human_posts']}, peko posts {g['peko_posts']} "
        f"({g['peko_posts_per_human_post']} per human post), board changes {g['board_posts']}",
        f"- Repeated peko posts {g['repeated_peko_posts']}, raw JSON posts {g['raw_json_posts']}",
    ]
    if result["quiet_window"]:
        lines.append(f"- Peko posts in the quiet window: {result['quiet_window']['peko_posts']}")
    b = result["board"]
    lines += [
        f"- Board: {b['items']} items, {b['open']} open, "
        f"{len(b['unresolved_duplicates'])} duplicate pair(s) open, "
        f"computers agree: {b['computers_agree']}",
        f"- Approvals: {result['approvals']}",
        f"- Branches pushed: {', '.join(result['branches_pushed']) or 'none'}",
    ]
    lines += conversation_markdown(result.get("conversation") or {})
    lines += [
        "",
        "## Spend",
        "",
    ]
    for who, spend in result["spend"].items():
        lines.append(f"- {who}: {spend}")
    return "\n".join(lines) + "\n"
