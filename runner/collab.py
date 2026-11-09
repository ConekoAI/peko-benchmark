#!/usr/bin/env python3
"""Collaboration benchmark: the two core use cases, scripted (docs/COLLAB_BENCHMARK.md).

Two people (Maya, Noah) and their pekos (juno, otto) fix a bug in a shared
repo through a group with a board; then Maya, from her other computer,
asks juno for something while juno's computer is asleep. Each run starts
from nothing: a fresh PekoHub database, fresh accounts, fresh runtimes, a
fresh repo. A real model drives the pekos; the script plays the people.

Usage (from this repo):

    PEKO_API_KEY=... python3 runner/collab.py [--approve-after 30] [--quiet 360]

Needs: a peko-runtime build (`cargo build -p peko-cli -p peko-daemon`), a
pekohub checkout with `npm install` done in `backend/`, and its Postgres
container (`docker compose up -d db` in pekohub; default name `pekohub-db`,
port 5433). Writes `reports/<run>-collab/` with command logs, the collected
evidence (`evidence.json`), the score (`score.json`) and `report.md`.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import collab_score

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = Path(os.environ.get("PEKO_RUNTIME_DIR", ROOT.parent / "peko-runtime"))
HUB_DIR = Path(os.environ.get("PEKOHUB_DIR", ROOT.parent / "pekohub"))
PEKO_BIN = Path(os.environ.get("PEKO_BIN", RUNTIME_DIR / "target/debug/peko"))
DB_CONTAINER = os.environ.get("PEKOHUB_DB_CONTAINER", "pekohub-db")
DB_PORT = int(os.environ.get("PEKOHUB_DB_PORT", "5433"))
HUB_PORT = int(os.environ.get("COLLAB_HUB_PORT", "3931"))
MODEL = os.environ.get("PEKO_MODEL_ID", "claude-sonnet-5-5")
BASE_URL = os.environ.get("PEKO_BASE_URL", "https://api.anthropic.com")
API_FORMAT = os.environ.get("PEKO_API_FORMAT", "anthropic_messages")

# The people's lines. Fixed so runs compare.
ASK_GROUP = (
    "Noah and I are going to fix a small stats repo together, with you and his peko "
    "otto (@noah/otto). Please make a group called stats-team with otto in it, and give "
    "me an invite link for Noah."
)
REPO_NOTE = "The repo is at {origin} (clone it to work on it). Tests run with python3 -m unittest."
TESTS_ITEM = "Run the tests and report which fail"
ASK_FIX_MAYA = "@juno please fix median so the even-length test passes, and push it to a new branch."
ASK_FIX_NOAH = "@otto can you fix the even-length median bug and push the fix to a branch?"
ASK_OTTO_JOIN = "Please join our stats-team group with this link: {link}"
ASK_WHILE_ASLEEP = "When you're back: what is still open on the stats-team board?"

STATS_PY = '''"""Small statistics helpers."""


def mean(xs):
    return sum(xs) / len(xs)


def median(xs):
    s = sorted(xs)
    return s[len(s) // 2]


def spread(xs):
    return max(xs) - min(xs)
'''
TEST_STATS_PY = '''import unittest

from stats import mean, median, spread


class StatsTest(unittest.TestCase):
    def test_mean(self):
        self.assertEqual(mean([1, 2, 3, 4]), 2.5)

    def test_median_odd(self):
        self.assertEqual(median([3, 1, 2]), 2)

    def test_median_even(self):
        self.assertEqual(median([4, 1, 3, 2]), 2.5)

    def test_spread(self):
        self.assertEqual(spread([5, 1, 9]), 8)


if __name__ == "__main__":
    unittest.main()
'''


def channel_ids(listing: str) -> list[str]:
    """`peko channel ls <peko> --json`: a list of ids (older builds: an object)."""
    data = json.loads(listing or "[]")
    return [str(c) for c in (data.get("channels", []) if isinstance(data, dict) else data)]


def group_of(listing: str) -> str | None:
    return next((c for c in channel_ids(listing) if not c.startswith("dm_")), None)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def wait_for(check, timeout: float, every: float = 3.0):
    """Seconds until `check()` is truthy, or None at `timeout`."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            if check():
                return round(time.monotonic() - start, 1)
        except Exception:  # noqa: BLE001 - a probe that fails is "not yet"
            pass
        time.sleep(every)
    return None


def sign_jwt(claims: dict, secret: str) -> str:
    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps({**claims, "iat": int(time.time())}).encode())
    sig = hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{b64(sig)}"


class Log:
    def __init__(self, path: Path, secrets_to_hide: list[str]):
        self.path = path
        self.hide = [s for s in secrets_to_hide if s]
        self.lock = threading.Lock()

    def write(self, text: str):
        for s in self.hide:
            text = text.replace(s, "[REDACTED]")
        with self.lock, self.path.open("a") as f:
            f.write(text.rstrip("\n") + "\n")


class Hub:
    """A PekoHub on a fresh database, for this run only."""

    def __init__(self, run_dir: Path, log: Log):
        self.run_dir = run_dir
        self.log = log
        self.db = "collab_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        self.secret = secrets.token_hex(24)
        self.url = f"http://127.0.0.1:{HUB_PORT}"
        self.proc = None
        self.backend = HUB_DIR / "backend"

    @property
    def database_url(self) -> str:
        return f"postgres://pekohub:pekohub@127.0.0.1:{DB_PORT}/{self.db}"

    def psql(self, query: str, db: str | None = None) -> list[list[str]]:
        out = subprocess.run(
            ["docker", "exec", DB_CONTAINER, "psql", "-U", "pekohub", "-d", db or self.db,
             "-AtF", "\t", "-c", query],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
        return [line.split("\t") for line in out.splitlines() if line]

    def start(self):
        self.psql(f"CREATE DATABASE {self.db}", db="postgres")
        env = {**os.environ, "DATABASE_URL": self.database_url}
        migrate = subprocess.run(["npx", "drizzle-kit", "migrate"], cwd=self.backend, env=env,
                                 capture_output=True, text=True, timeout=300)
        self.log.write(f"hub migrate rc={migrate.returncode}\n{migrate.stdout[-2000:]}\n{migrate.stderr[-2000:]}")
        if migrate.returncode:
            raise RuntimeError("hub migration failed; see hub.log")
        env.update({
            "PORT": str(HUB_PORT), "HOST": "127.0.0.1", "NODE_ENV": "development",
            "JWT_SECRET": self.secret, "PUBLIC_ORIGIN": self.url,
            "FRONTEND_URL": f"http://127.0.0.1:{HUB_PORT + 1}",
            "DOTENV_CONFIG_PATH": str(self.backend / ".env"),
        })
        out = (self.run_dir / "hub-server.log").open("w")
        self.proc = subprocess.Popen(["npx", "tsx", "src/index.ts"], cwd=self.backend, env=env,
                                     stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        if wait_for(lambda: urllib.request.urlopen(f"{self.url}/health", timeout=2).status == 200,
                    120, 1) is None:
            raise RuntimeError("the hub did not come up; see hub-server.log")

    def add_user(self, namespace: str, name: str) -> tuple[str, str]:
        uid = str(uuid.uuid4())
        self.psql(
            "INSERT INTO users (id, external_id, provider, namespace, display_name, email, "
            f"handle_chosen_at) VALUES ('{uid}', 'bench:{namespace}', 'bench', '{namespace}', "
            f"'{name}', '{namespace}@bench.invalid', now())"
        )
        return uid, sign_jwt({"sub": uid, "namespace": namespace}, self.secret)

    def approve_device(self, code: str, token: str):
        req = urllib.request.Request(
            f"{self.url}/v1/oauth/device/decision",
            data=json.dumps({"user_code": code, "approve": True}).encode(),
            headers={"authorization": f"Bearer {token}", "content-type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=20).read()

    def peko(self, name: str) -> dict:
        rows = self.psql(f"SELECT hub_id, status FROM instances WHERE name = '{name}'")
        return {"hub_id": rows[0][0], "status": rows[0][1]} if rows else {}

    def stop(self):
        if self.proc and self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL)
        try:
            self.psql(f"DROP DATABASE IF EXISTS {self.db} WITH (FORCE)", db="postgres")
        except Exception as e:  # noqa: BLE001
            self.log.write(f"hub: drop database failed: {e}")


class Runtime:
    """One computer: an isolated peko runtime under the run directory."""

    def __init__(self, name: str, run_dir: Path, hub: Hub, key: str):
        self.name = name
        self.home = run_dir / name
        self.home.mkdir(parents=True, exist_ok=True)
        self.peko_home = self.home / ".peko"
        self.key = key
        self.hub = hub
        self.log = Log(run_dir / f"{name}.log", [key])
        self.env = {
            **{k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "TMPDIR", "USER")},
            "HOME": str(self.home),
            "PEKO_HOME": str(self.peko_home),
            "PEKO_UNLOCK_METHOD": "passphrase",
            "PEKO_MASTER_PASSPHRASE": f"collab-{name}-{secrets.token_hex(4)}",
            "RUST_LOG": "info",
        }
        self.env["PEKO_IDENTITY_PASSPHRASE"] = self.env["PEKO_MASTER_PASSPHRASE"]

    def run(self, *args: str, timeout: float = 180, check: bool = True) -> str:
        proc = subprocess.run([str(PEKO_BIN), *args], env=self.env, cwd=self.home,
                              capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        shown = [a if not self.key or a != self.key else "[REDACTED]" for a in args]
        self.log.write(f"$ peko {' '.join(shown)}  (rc={proc.returncode})\n{proc.stdout}\n{proc.stderr}")
        if check and proc.returncode:
            raise RuntimeError(f"{self.name}: peko {args[0]} failed (rc={proc.returncode})")
        return proc.stdout

    def setup(self, token: str):
        self.peko_home.mkdir(parents=True, exist_ok=True)
        self.run("model", "add", "--id", "bench", "--api-format", API_FORMAT, "--base-url", BASE_URL,
                 "--model", MODEL, "--context-window", "200000", "--key", self.key)
        self.run("daemon", "start")
        self.sign_in(token)

    def sign_in(self, token: str):
        proc = subprocess.Popen([str(PEKO_BIN), "auth", "login", "--hub", self.hub.url], env=self.env,
                                cwd=self.home, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, text=True)
        seen, code = [], None
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and code is None:
            line = proc.stdout.readline()
            if not line:
                break
            seen.append(line)
            match = re.search(r"\b([A-Z0-9]{4}-[A-Z0-9]{4})\b", line)
            if match:
                code = match.group(1)
        if code is None:
            proc.kill()
            self.log.write("".join(seen))
            raise RuntimeError(f"{self.name}: no device code from auth login")
        self.hub.approve_device(code, token)
        rest, _ = proc.communicate(timeout=90)
        self.log.write("$ peko auth login\n" + "".join(seen) + rest)
        if proc.returncode:
            raise RuntimeError(f"{self.name}: sign-in failed")

    def start(self):
        self.run("daemon", "start")

    def stop(self):
        self.run("daemon", "stop", timeout=60, check=False)

    def channels_dir(self) -> Path:
        return self.peko_home / "runtime" / "channels"

    def channel_events(self, kind: str) -> list[tuple[Path, list[dict]]]:
        """Each channel copy of `kind` ("group"/"dm") with its events."""
        out = []
        for meta in self.channels_dir().glob("*/meta.json"):
            try:
                if json.loads(meta.read_text()).get("kind") != kind:
                    continue
            except ValueError:
                continue
            text = "".join(p.read_text() for p in sorted(meta.parent.glob("events*.jsonl")))
            out.append((meta.parent, collab_score.events_of(text)))
        return out

    def outbox_texts(self) -> list[str]:
        out = []
        for f in (self.peko_home / "runtime" / "channel_delivery" / "outbox").glob("*.json"):
            try:
                out.append(json.dumps(json.loads(f.read_text())))
            except ValueError:
                continue
        return out

    def quota(self, peko: str) -> dict:
        """The peko's usage this run: requests and tokens (its cost is 0
        unless the model catalog has prices for the model)."""
        keep = ("request_count", "input_tokens", "output_tokens", "cache_read_tokens",
                "cache_creation_tokens", "cost_usd")
        for f in self.peko_home.glob(f"data/pekos/{peko}/local/**/quota_state.json"):
            try:
                state = json.loads(f.read_text())
            except ValueError:
                return {}
            return {k: state[k] for k in keep if k in state}
        return {}


class Approver(threading.Thread):
    """Each owner approves their peko's requests a while after they appear,
    as a person glancing at their phone would: long enough for two pekos
    asked for the same thing to notice each other first."""

    def __init__(self, owners: list[tuple[Runtime, str]], delay: float, log: Log):
        super().__init__(daemon=True)
        self.owners = owners
        self.delay = delay
        self.log = log
        self.first_seen: dict[str, float] = {}
        self.approved: list[str] = []
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.wait(5):
            for runtime, peko in self.owners:
                try:
                    listing = runtime.run("approvals", peko, timeout=30, check=False)
                except Exception:  # noqa: BLE001
                    continue
                for request in re.findall(r"^(apr_[0-9a-f]+)", listing, re.M):
                    seen = self.first_seen.setdefault(request, time.monotonic())
                    if request in self.approved or time.monotonic() - seen < self.delay:
                        continue
                    runtime.run("approve", peko, request, timeout=60, check=False)
                    self.approved.append(request)
                    self.log.write(f"{now()} approved {request} for {peko}")

    def counts(self) -> dict:
        return {"requested": len(self.first_seen), "approved": len(self.approved)}


def seed_repo(run_dir: Path) -> Path:
    work = run_dir / "repo-seed"
    origin = run_dir / "origin.git"
    work.mkdir()
    (work / "stats.py").write_text(STATS_PY)
    (work / "test_stats.py").write_text(TEST_STATS_PY)
    (work / "README.md").write_text("# stats\n\nRun the tests with `python3 -m unittest`.\n")
    git = ["git", "-c", "user.name=maya", "-c", "user.email=maya@bench.invalid"]
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work, check=True)
    subprocess.run(["git", "add", "-A"], cwd=work, check=True)
    subprocess.run([*git, "commit", "-qm", "stats helpers"], cwd=work, check=True)
    subprocess.run(["git", "clone", "-q", "--bare", str(work), str(origin)], check=True)
    return origin


def branches(origin: Path) -> list[str]:
    out = subprocess.run(["git", "ls-remote", "--heads", str(origin)], capture_output=True,
                         text=True, check=True).stdout
    return [line.split("refs/heads/")[1] for line in out.splitlines() if "refs/heads/" in line
            and not line.endswith("refs/heads/main")]


def branch_passes(origin: Path, branch: str, scratch: Path) -> bool:
    target = scratch / f"check-{branch.replace('/', '_')}"
    shutil.rmtree(target, ignore_errors=True)
    subprocess.run(["git", "clone", "-q", "-b", branch, str(origin), str(target)], check=True)
    return subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=target,
                          capture_output=True, timeout=120).returncode == 0


def commit_of(path: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "?"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--approve-after", type=float, default=30,
                        help="seconds an owner waits before approving a request (default 30)")
    parser.add_argument("--quiet", type=float, default=360,
                        help="seconds of nobody posting after the fix (default 360)")
    parser.add_argument("--skip-uc1", action="store_true", help="skip the sleeping-computer part")
    args = parser.parse_args()
    key = os.environ.get("PEKO_API_KEY", "")
    if not key:
        print("PEKO_API_KEY is required (the model key the pekos use).", file=sys.stderr)
        return 2
    if not PEKO_BIN.exists():
        print(f"no peko binary at {PEKO_BIN}; build peko-runtime first.", file=sys.stderr)
        return 2

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ROOT / "reports" / f"{run_id}-collab"
    run_dir.mkdir(parents=True)
    log = Log(run_dir / "run.log", [key])
    meta = {"run_id": run_id, "runtime_commit": commit_of(RUNTIME_DIR), "hub_commit": commit_of(HUB_DIR),
            "model": MODEL, "approve_after": args.approve_after, "quiet": args.quiet}
    log.write(f"{now()} run {json.dumps(meta)}")

    hub = Hub(run_dir, Log(run_dir / "hub.log", []))
    milestones: dict[str, float | None] = {}
    evidence: dict = {"milestones": milestones}
    runtimes: list[Runtime] = []
    approver = None

    def step(name: str, seconds):
        milestones[name] = seconds
        log.write(f"{now()} {name}: {'not reached' if seconds is None else f'{seconds}s'}")
        return seconds

    try:
        hub.start()
        maya_id, maya_token = hub.add_user("maya", "Maya")
        noah_id, noah_token = hub.add_user("noah", "Noah")
        pc1, pc2 = Runtime("pc1", run_dir, hub, key), Runtime("pc2", run_dir, hub, key)
        runtimes += [pc1, pc2]
        pc1.setup(maya_token)
        pc2.setup(noah_token)
        origin = seed_repo(run_dir)
        pc1.run("create", "juno", timeout=600)
        pc2.run("create", "otto", timeout=600)
        log.write(f"{now()} setup done")

        # 1. Maya asks juno for the group, with otto and a link for Noah.
        start = time.monotonic()
        reply = pc1.run("send", "juno", ASK_GROUP, timeout=600)
        link = re.search(r"https?://\S+/g/\S+?invite=[A-Za-z0-9._\-]+", reply)
        group = None

        def group_formed():
            nonlocal group
            group = group_of(pc1.run("channel", "ls", "juno", "--json", check=False))
            return group is not None

        formed = wait_for(group_formed, 60) if link else None
        step("group_formed", None if formed is None else round(time.monotonic() - start, 1))
        if group is None or link is None:
            raise RuntimeError("no group or invite link; stopping")

        def members() -> str:
            return pc1.run("channel", "members", group, check=False).lower()

        # 2. Noah joins with the link. A private peko is found by name only
        # by someone who shares a group with its owner (ADR-098), so on fresh
        # accounts otto comes in after Noah, by the same link.
        pc2.run("channel", "join", link.group(0))
        step("noah_joined", wait_for(lambda: "noah" in members(), 90))
        start = time.monotonic()
        if "otto" not in members():
            pc2.run("send", "otto", ASK_OTTO_JOIN.format(link=link.group(0)), timeout=600)
        reached = wait_for(lambda: "otto" in members(), 180, 5)
        step("otto_joined", None if reached is None else round(time.monotonic() - start, 1))

        approver = Approver([(pc1, "juno"), (pc2, "otto")], args.approve_after, log)
        approver.start()

        # 3. The tests, through the board.
        pc1.run("channel", "post", group, "me", REPO_NOTE.format(origin=origin))
        pc1.run("channel", "board", group, "add", TESTS_ITEM, "--for", "juno")

        def item_done(title_part: str):
            items = json.loads(pc1.run("channel", "board", group, "--json", check=False))["items"]
            return any(title_part.lower() in i["title"].lower() and i["state"] == "done" for i in items)

        step("tests_reported", wait_for(lambda: item_done("run the tests"), 600, 5))

        # 4. Both people ask their peko for the same fix at once.
        both = [threading.Thread(target=pc1.run, args=("channel", "post", group, "me", ASK_FIX_MAYA)),
                threading.Thread(target=pc2.run, args=("channel", "post", group, "me", ASK_FIX_NOAH))]
        for t in both:
            t.start()
        for t in both:
            t.join()
        step("fix_pushed", wait_for(lambda: branches(origin), 900, 10))
        pushed = branches(origin)
        step("fix_passes", 0.0 if any(branch_passes(origin, b, run_dir) for b in pushed) else None)

        # 5. Nobody posts for a while: the pekos should go quiet too.
        time.sleep(60)  # let the last turns finish before the window opens
        quiet_start = now()
        time.sleep(args.quiet)
        evidence["quiet_window"] = {"start": quiet_start, "end": now()}

        # 6. Use case 1: juno's computer sleeps; Maya asks from another one.
        if not args.skip_uc1:
            pc3 = Runtime("pc3", run_dir, hub, key)
            runtimes.append(pc3)
            pc3.setup(maya_token)
            pc1.stop()
            wait_for(lambda: hub.peko("juno").get("status") == "offline", 120, 3)
            asked_at = now()
            # From the CLI, by juno's name: pc3 has no PekoHub token of Maya's,
            # so its runtime vouches for her (pekohub PekoRuntime proof), and
            # PekoHub finds a private peko by name for its owner.
            pc3.run("channel", "dm", "@maya/juno", ASK_WHILE_ASLEEP)
            step("uc1_queued", wait_for(lambda: any(ASK_WHILE_ASLEEP in t for t in pc3.outbox_texts()), 30, 2))
            time.sleep(20)
            wake = time.monotonic()
            pc1.start()
            step("uc1_delivered", wait_for(
                lambda: not any(ASK_WHILE_ASLEEP in t for t in pc3.outbox_texts()), 300, 3))

            def answered():
                for _, events in pc1.channel_events("dm"):
                    asked = [e for e in events if e.get("text") == ASK_WHILE_ASLEEP]
                    if asked and any(collab_score.is_peko(e.get("author", "")) and e.get("at", "") > asked_at
                                     and e.get("kind") == "posted" for e in events):
                        return True
                return False

            reached = wait_for(answered, 300, 5)
            step("uc1_answered", None if reached is None else round(time.monotonic() - wake, 1))
    except Exception as e:  # noqa: BLE001 - a failed step is a result, not a crash
        log.write(f"{now()} stopped: {e!r}")
        evidence["error"] = repr(e)
    finally:
        if approver:
            approver.stop_event.set()
        try:
            home = next((r for r in runtimes if r.name == "pc1"), None)
            if home:
                groups = home.channel_events("group")
                evidence["group_events"] = groups[0][1] if groups else []
            boards = {}
            for rt in runtimes[:2]:
                try:
                    grp = group_of(rt.run("channel", "ls", "juno" if rt.name == "pc1" else "otto",
                                          "--json", check=False))
                    if grp:
                        boards[rt.name] = json.loads(rt.run("channel", "board", grp, "--json"))["items"]
                except Exception as e:  # noqa: BLE001
                    log.write(f"board read on {rt.name} failed: {e!r}")
            evidence["boards"] = boards
            evidence["approvals"] = approver.counts() if approver else {}
            origin_path = run_dir / "origin.git"
            evidence["branches_pushed"] = branches(origin_path) if origin_path.exists() else []
            evidence["spend"] = {p: rt.quota(p) for rt, p in
                                 [(r, "juno" if r.name == "pc1" else "otto") for r in runtimes[:2]]}
        except Exception as e:  # noqa: BLE001
            log.write(f"collect failed: {e!r}")
        for rt in runtimes:
            rt.stop()
        hub.stop()

    for name in ("group_formed", "noah_joined", "otto_joined", "tests_reported", "fix_pushed", "fix_passes",
                 *(() if args.skip_uc1 else ("uc1_queued", "uc1_delivered", "uc1_answered"))):
        milestones.setdefault(name, None)
    (run_dir / "evidence.json").write_text(json.dumps({"meta": meta, **evidence}, indent=2))
    result = collab_score.score(evidence)
    (run_dir / "score.json").write_text(json.dumps({"meta": meta, **result}, indent=2))
    (run_dir / "report.md").write_text(collab_score.report_markdown(result, meta))
    print(collab_score.report_markdown(result, meta))
    print(f"run directory: {run_dir}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
