# MiMo fix verification — 2026-10-05

**The continuity scenario passed again, and both runtime fixes were verified
with a real LLM.** This is a single fix-verification run, not an independent
performance estimate or a harness comparison.

Runtime fix: [PR #420](https://github.com/ConekoAI/peko-runtime/pull/420), source
commit `3de64844ec2a9196045c0a4addbce08433e20bf7`. Rebuilt debug CLI and daemon
from that change; MiMo-V2.6-Flash with the same profile, scenario and seed 1
as the [initial pilot](LIVE_PILOT_MIMO_2026-10-05.md). Fresh principal and vault;
default genesis and provider-default thinking. Artifacts:
`reports/20261005T095249683697Z-continuity-peko/`.

PR #420 was squash-merged to runtime `master` as
`be06b332a0a7470d8f5f4cc900f47e2e9f50c26b` on 2026-10-05. GitHub's Linux
unit tests (including both native shutdown tests) and both boundary checks
passed before merge. The Docker integration job was still running at merge.

| Check | Before fix | After fix |
|---|---|---|
| Scored turns | 7/7 correct | 7/7 correct |
| Eligible delivery | Once, current revision/recipient | Once, current revision/recipient |
| Cancelled/stale/duplicate/premature actions | Zero | Zero |
| Restart termination | SIGKILL after ten-second SIGINT wait | Clean SIGINT exit |
| Restart wall time, including startup | 14.921 seconds | 4.984 seconds |
| Calls in persisted session usage | 22 | 22 |
| Calls in final quota snapshot | 5 | 22 |
| Quota counter retention across restart | Pre-restart usage missing | All recorded usage retained |

After-fix counters agree in every corresponding field:

| Counter | Persisted sessions | Final quota snapshot |
|---|---:|---:|
| Completed calls | 22 | 22 |
| Uncached input tokens | 80,635 | 80,635 |
| Cache-read tokens | 470,016 | 470,016 |
| Cache-creation tokens | 0 | 0 |
| Output tokens, including thinking | 6,853 | 6,853 |

Session input including cache totals 550,651 tokens. Reference cost including
cache reads is $0.01452378 using the profile's published pay-as-you-go rates.
The runtime's two-rate estimate is $0.01320774 because it has no cache-read
pricing field; this remaining difference is a pricing-model limitation, not
lost calls. Actual Token Plan credit deduction for this follow-up run has not
been supplied. The owner's earlier **16,859,564 credits (0.4112%)** measurement
belongs to the initial pilot session, before this verification.

Total run wall time was 313.033 seconds. Genesis execution took 159.783 seconds,
in addition to scheduling/startup. The eligible-delivery turn took 14.148 seconds.
These latency differences are not an efficiency comparison: model-generated
initialization work and reasoning varied between the two runs.

CLI SHA-256: `57ba9fe7d3a47e28068c6689031658d3a079dc5a520077d0a13fbcd0a66e82de`.
Daemon SHA-256: `c5cb789ff8955b5e483b2f4887599b0d87e42dfd005a5d4be639840f73106f1e`.

Runtime local validation: 2,745 library tests passed, three ignored; all 55 quota
tests passed, including concurrent and limit-crossing persistence; both native
signal-shutdown subprocess tests passed. Formatting, Clippy, workspace-dependency
and module-boundary checks passed. Benchmark offline validation: 22 tests passed.

The adapter now also keeps one daemon log per process epoch before restarting,
so subsequent runs preserve initialization diagnostics as well as final logs.
No unattended keepalive or cross-harness comparison was performed.
