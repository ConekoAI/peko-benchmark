# Collaboration benchmark: first runs (2026-11-09)

Runtime `39341c84` (peko-runtime master after #604–#608), hub `753444f`
(pekohub master after #84), model `claude-sonnet-5-5`, defaults
(`--approve-after 30 --quiet 360`). See [COLLAB_BENCHMARK.md](COLLAB_BENCHMARK.md).

| Run | Result | Notes |
|---|---|---|
| `20261109T092907Z` | stopped at step 1 | Harness: `peko channel ls --json` is a list, not an object. Behaviour: on fresh accounts juno could not invite `@noah/otto` (a private peko is found by name only by someone sharing a group with its owner, ADR-098); it made the group and the link and said otto could join with it. The script now follows that first-time path. |
| `20261109T093225Z` | use case 2 **pass**; use case 1 not run | `peko channel dm peko:hub:<id>` from the CLI is refused for your own private peko (no PekoHub token). The script now posts in the DM that followed Maya to `pc3`. |
| `20261109T094402Z` | **PASS** | All milestones; details below. |
| `20261109T100538Z` | **PASS** (`--quiet 30`) | With finding 1 fixed (runtime + hub branches `feat/runtime-directory-proof`): Maya opened the DM from `pc3` with `peko channel dm peko:hub:<juno>`; delivered when `pc1` woke, answered in 12.7 s. |

## The passing run

| Milestone | Seconds |
|---|---|
| group_formed | 14.2 |
| noah_joined | 0.0 |
| otto_joined (after Noah asked otto) | 8.6 |
| tests_reported (board item for juno, one approval) | 55.4 |
| fix_pushed (both asked at once) | 50.3 |
| fix_passes | yes |
| uc1_queued (pc1 asleep) | yes |
| uc1_delivered (after pc1 woke) | at once |
| uc1_answered (after pc1 woke) | 12.8 |

- Group: 3 human posts, 6 peko posts (2.0 per human post), 10 board changes;
  no repeated post, no raw JSON post, 0 peko posts in the 6-minute quiet window.
- Board: 2 items, both done; no open duplicate; both computers agree.
- Two approvals requested and approved, both juno's. Asked for the same fix,
  otto added its own item, saw juno's (the `similar` hint, #607) and removed its
  item 3 seconds later, with one post: it dropped its duplicate, juno has it as
  #5faf47. One branch (`juno/fix-median-even`) was pushed.
- Usage: juno 32 requests (905k input tokens, 723k of them cache reads, 8k
  output); otto 16 requests (438k input, 378k cache reads, 3k output).

Runs 2 and 3 took nearly the same time for every use case 2 step (13.1/14.2,
8.2/8.6, 55.4/55.4, 50.2/50.3 s; the waits poll every 3–10 s, so close times
can read the same). The model's choices were the same in both. Compare several
runs before trusting a change.

## Findings for the runtime

1. **The CLI can't open a DM with your own private peko** from another computer
   (`peko channel dm` sends no PekoHub token; the device sign-in token is used once
   to register the runtime). Use case 1 works from the desktop and, from the CLI,
   only in a DM that already exists. **Fixed**: the runtime signs the lookup
   with its own key and the Hub answers it as the runtime's person
   (ConekoAI/peko-runtime and ConekoAI/pekohub `feat/runtime-directory-proof`);
   run `20261109T100538Z` uses it.
2. **First-time pairs can't add each other's private pekos by name** until they
   share a group (by design, ADR-098). The pekos handled it well: juno explained
   it and offered the link, and otto joined by it when Noah asked.
3. **Status posts after a hand-up remain.** After each owner approval request
   juno still posted a line ("I've sent Maya a request…") although its board
   item already said so; #608's wording did not stop it. Within the gate (2.0
   peko posts per human post), but it is the bulk of juno's posts.
4. **A "nothing to say" post.** After juno's result otto posted that juno's
   posts needed no answer from it, where an empty reply was right. Rare, but a
   candidate for a runtime guard (drop a conversation reply that only says no
   reply is needed).
