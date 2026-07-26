#!/usr/bin/env python3
"""Fleet-triage board for the chief of staff.

Runs `herdr agent list`, parses the JSON, and prints every agent grouped by
status (blocked first, then working, then idle, then anything else), one line
each as:

    <STATUS>  <pane_id>  <cwd-basename>  <title>

On any failure (herdr missing/unreachable, non-zero exit, unparseable or
unexpected JSON) it prints a single clear line to stderr and exits non-zero.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

# Status buckets in triage priority order. Any status not listed here is
# collected under the trailing "unknown" bucket so nothing is ever dropped.
STATUS_ORDER = ["blocked", "working", "idle"]


def fail(message: str) -> "int":
    """Print one clear line to stderr and return a non-zero exit code."""
    print(f"board: {message}", file=sys.stderr)
    return 1


def basename(path: str) -> str:
    """Last path component, tolerant of trailing separators and \\ or /."""
    normalized = (path or "").replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", 1)[-1] if normalized else ""


def main() -> int:
    try:
        proc = subprocess.run(
            ["herdr", "agent", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        return fail("herdr not found on PATH")
    except OSError as exc:
        return fail(f"could not run herdr: {exc}")

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        hint = f": {detail[0]}" if detail else ""
        return fail(f"herdr agent list exited {proc.returncode}{hint}")

    try:
        payload = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        return fail(f"could not parse herdr JSON: {exc}")

    try:
        agents = payload["result"]["agents"]
    except (KeyError, TypeError):
        return fail("unexpected herdr JSON: no result.agents")

    if not isinstance(agents, list):
        return fail("unexpected herdr JSON: agents is not a list")

    # Group agents by status.
    groups: dict[str, list[dict]] = {}
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        status = str(agent.get("agent_status") or "unknown").lower()
        bucket = status if status in STATUS_ORDER else "unknown"
        groups.setdefault(bucket, []).append(agent)

    ordered_buckets = STATUS_ORDER + ["unknown"]
    for bucket in ordered_buckets:
        for agent in groups.get(bucket, []):
            status = str(agent.get("agent_status") or "unknown")
            pane_id = str(agent.get("pane_id") or "-")
            cwd = basename(str(agent.get("cwd") or ""))
            title = str(
                agent.get("terminal_title_stripped")
                or agent.get("terminal_title")
                or ""
            ).strip()
            print(f"{status.upper()}  {pane_id}  {cwd}  {title}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
