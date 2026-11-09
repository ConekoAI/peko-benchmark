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
    }


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
        "",
        "## Spend",
        "",
    ]
    for who, spend in result["spend"].items():
        lines.append(f"- {who}: {spend}")
    return "\n".join(lines) + "\n"
