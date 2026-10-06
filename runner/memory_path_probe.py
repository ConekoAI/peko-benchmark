#!/usr/bin/env python3
"""Bounded native write/read diagnostic; not a responsibility benchmark score."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import secrets
from pathlib import Path

from responsibility_drivers import PekoResponsibility
from responsibility_simulator import Simulator, load_spec

ROOT = Path(__file__).resolve().parent.parent


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "reports" / f"{stamp}-responsibility-memory-path-peko"
    run_dir.mkdir()
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for pattern in ("runner/responsibility*.py", "runner/continuity*.py",
                               "runner/prompt_profile.py", "runner/memory_path_probe.py")
               for p in ROOT.glob(pattern)}
    (run_dir / "source-manifest.json").write_text(json.dumps(sources, indent=2))
    spec = load_spec(ROOT / "scenarios/responsibility/pilot.toml", 1, 1)
    spec["profile_prompt"] = True
    sim = Simulator(spec, run_dir)
    sim.start_server()
    # Disable keepalive during native genesis; no unattended watch is scored.
    driver = PekoResponsibility(run_dir, 600, .03, sim, "persistence")
    marker = "memory-path-" + secrets.token_hex(8)
    checks, usage, errors = {}, {}, []
    intended = None
    try:
        driver.start()
        sim.phase = "conversation"
        driver.conversation(f"Record this durable fact in kb/memory-path-check.md in your "
                            f"principal's shared knowledge base: {marker}. "
                            "Leave other memory files unchanged and acknowledge briefly.")
        root = Path(driver.temp.name) / ".peko"
        intended = root / "principals" / driver.principal / "kb/memory-path-check.md"
        misplaced = root / "data/workspaces/kb/memory-path-check.md"
        checks["canonical_file_contains_marker"] = intended.is_file() and marker in intended.read_text()
        checks["no_default_directory_copy"] = not misplaced.exists()
        reply = driver.conversation("Read back the marker you just saved from the principal's shared "
                                    "knowledge base. Reply with the exact marker only.")
        checks["readback_matches"] = reply.strip() == marker
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    finally:
        if driver.temp:
            try:
                usage = driver.telemetry()
            except Exception as exc:
                errors.append(f"telemetry {type(exc).__name__}: {exc}")
        try:
            driver.close()
        except Exception as exc:
            errors.append(f"cleanup {type(exc).__name__}: {exc}")
        sim.close()
    # Require native Read evidence: a remembered answer alone cannot verify I/O.
    reads = []
    for path in (run_dir / "runtime-traces").rglob("*.jsonl"):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("role") != "assistant":
                continue
            for block in row.get("content", []):
                if block.get("type") == "tool_call" and block.get("name") == "Read":
                    reads.append(block.get("arguments", {}).get("file_path", ""))
    # /tmp may canonicalize to /private/tmp on macOS; compare resolved paths.
    checks["native_read_used_canonical_file"] = any(
        Path(p).is_absolute() and Path(p).resolve() == intended.resolve() for p in reads
    ) if intended is not None else False
    passed = (len(checks) == 4 and all(checks.values()) and not errors
              and usage.get("usage_complete", False) and usage.get("native_usage_matches", False))
    result = {"evidence_kind": "real_llm_memory_path_diagnostic", "passed": passed,
              "checks": checks, "metadata": driver.metadata, "usage": usage, "errors": errors}
    (run_dir / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"report": str(run_dir), **result}, indent=2), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
