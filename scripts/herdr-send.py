#!/usr/bin/env python3
"""Deliver a message to a staff agent safely.

`herdr agent send` injects raw keystrokes into the target's TTY and does *not*
submit; the Enter is a second, separate command. That split is the source of two
failures seen in practice:

  * the injected text lands at the cursor inside whatever the input box already
    holds, so it fuses with whatever the owner was typing; and
  * whenever the follow-up Enter is skipped, errors (stale pane id), or is eaten
    by a race, the message just sits in the draft. The box is never cleared, so
    every later message piles onto the same stale draft and none of them are
    ever sent — the receiving agent never sees any of it.

This helper closes both holes:

  1. it re-resolves the target to a pane id on every call (pane ids churn);
  2. it waits until the input box is clear, so a message never fuses with the
     owner's half-typed text;
  3. it delivers with `herdr pane run`, which writes the text bracketed-paste
     wrapped *and* the trailing Enter in one atomic write — nothing can land
     between them; and
  4. it re-reads the box afterwards and fails loudly if the text is still
     sitting there unsent.

Usage:
    python scripts/herdr-send.py <target> "<message>"
    python scripts/herdr-send.py <target> --stdin < brief.md
    python scripts/herdr-send.py <target> "<msg>" --wait 300   # wait longer
    python scripts/herdr-send.py <target> "<msg>" --force      # skip the wait

<target> is anything `herdr agent list` resolves: a terminal id, a pane id, or a
unique agent name.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time

# How long to wait for the owner to finish typing, and how often to look.
DEFAULT_WAIT_SECONDS = 120.0
POLL_SECONDS = 2.0
# The box must read clear twice in a row before we deliver, so we don't slip a
# message in during the instant between a submit and the next keystroke.
CONFIRM_SECONDS = 0.7
# After delivering, how long to let the TUI settle before checking the box, and how
# many extra Enters to try if `pane run`'s own trailing `\r` was swallowed.
SETTLE_SECONDS = 1.2
SUBMIT_RETRIES = 2
# Rows of pane to inspect. Small reads come back empty from `herdr pane read`.
READ_LINES = 40

# Prompt markers: claude renders "❯", codex renders "›".
PROMPT_MARKERS = ("❯", "›")
# The input box ends at the rule claude draws under it, or — codex draws no rule —
# at the first blank row below the prompt. Either one ends the region we inspect.
RULE_CHARS = set("─━═-")

ANSI_RE = re.compile(r"\x1b\[[0-9;:]*[A-Za-z]")
SGR_RE = re.compile(r"\x1b\[([0-9;:]*)m")


def fail(message: str) -> int:
    print(f"herdr-send: {message}", file=sys.stderr)
    return 1


def herdr(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["herdr", *args], capture_output=True, text=True, encoding="utf-8"
    )


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def visible_non_dim(line: str) -> str:
    """Text of `line` with every dim (SGR 2) run removed.

    Both TUIs render the empty-box placeholder ("Try \"fix lint errors\"",
    "Implement {feature}") dim, and real draft text undimmed. Dropping the dim
    runs is what tells a placeholder apart from something the owner typed.
    """
    out = []
    dim = False
    pos = 0
    for match in SGR_RE.finditer(line):
        if not dim:
            out.append(line[pos : match.start()])
        params = [p for p in match.group(1).split(";") if p != ""] or ["0"]
        index = 0
        while index < len(params):
            param = params[index]
            # 38/48/58 take their color as sub-parameters: `38;5;n` (indexed) or
            # `38;2;r;g;b` (truecolor). Skip them, or the "2" of a truecolor
            # colour reads as SGR 2 (dim) and swallows the rest of the line.
            if param in ("38", "48", "58"):
                mode = params[index + 1] if index + 1 < len(params) else ""
                index += {"5": 3, "2": 5}.get(mode, 1)
                continue
            if param == "2":
                dim = True
            elif param in ("0", "22"):
                dim = False
            index += 1
        pos = match.end()
    if not dim:
        out.append(line[pos:])
    return strip_ansi("".join(out))


def read_pane(pane_id: str) -> "list[str]":
    proc = herdr("pane", "read", pane_id, "--lines", str(READ_LINES), "--format", "ansi")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError(f"pane read failed{': ' + detail[0] if detail else ''}")
    return proc.stdout.splitlines()


def draft_text(pane_id: str) -> str:
    """Whatever the owner has sitting in the input box, or "" if it is clear."""
    lines = read_pane(pane_id)
    prompt_index = None
    for index, line in enumerate(lines):
        stripped = strip_ansi(line).lstrip()
        if stripped[:1] in PROMPT_MARKERS:
            prompt_index = index
    if prompt_index is None:
        # No input box on screen: a dialog, a permission prompt, or a plain
        # shell. Treat it as occupied rather than typing blindly into it.
        return "<no input box on screen>"

    parts = []
    for index in range(prompt_index, len(lines)):
        plain = strip_ansi(lines[index]).strip()
        if index > prompt_index and (not plain or set(plain) <= RULE_CHARS):
            break
        text = visible_non_dim(lines[index])
        if index == prompt_index:
            text = text.lstrip()
            for marker in PROMPT_MARKERS:
                if text.startswith(marker):
                    text = text[len(marker) :]
                    break
        # \xa0 is the non-breaking space claude pads the prompt with.
        parts.append(text.replace("\xa0", " ").strip())
    return " ".join(part for part in parts if part).strip()


def resolve_pane(target: str) -> "tuple[str, str]":
    """Resolve a target to a live (pane_id, label). Never cache the result.

    Resolution is delegated to `herdr agent get`, which accepts terminal ids,
    pane ids and agent names — so this stays correct as herdr's targeting
    evolves. It is re-run on every send because pane ids churn as tabs and
    splits change, and a stale one either errors or, worse, lands in whichever
    agent inherited the id.
    """
    proc = herdr("agent", "get", target)
    if proc.returncode != 0:
        raise RuntimeError(f"cannot resolve {target!r}: {live_agents_hint()}")
    agent = json.loads(proc.stdout).get("result", {}).get("agent", {})
    pane_id = agent.get("pane_id")
    if not pane_id:
        raise RuntimeError(f"{target!r} resolved to an agent with no pane")
    return pane_id, agent.get("terminal_title_stripped") or pane_id


def live_agents_hint() -> str:
    """One-line inventory of live agents, for error messages."""
    proc = herdr("agent", "list")
    if proc.returncode != 0:
        return "could not list live agents"
    try:
        agents = json.loads(proc.stdout).get("result", {}).get("agents", [])
    except (json.JSONDecodeError, ValueError):
        return "could not parse the live agent list"
    listed = ", ".join(
        sorted(f"{a.get('pane_id')}={a.get('terminal_title_stripped')}" for a in agents)
    )
    return f"live agents: {listed or 'none'}"


def wait_for_clear_box(pane_id: str, wait_seconds: float) -> None:
    deadline = time.monotonic() + wait_seconds
    announced = False
    while True:
        draft = draft_text(pane_id)
        if not draft:
            time.sleep(CONFIRM_SECONDS)
            if not draft_text(pane_id):
                return
            draft = draft_text(pane_id)
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"input box still busy after {wait_seconds:.0f}s — not delivering on top "
                f"of it. box holds: {draft[:120]!r}"
            )
        if not announced:
            print(
                f"herdr-send: input box busy ({draft[:60]!r}) — waiting for it to clear",
                file=sys.stderr,
            )
            announced = True
        time.sleep(POLL_SECONDS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="terminal id, pane id, or unique agent name")
    parser.add_argument("message", nargs="?", help="message text (or use --stdin)")
    parser.add_argument("--stdin", action="store_true", help="read the message from stdin")
    parser.add_argument(
        "--wait",
        type=float,
        default=DEFAULT_WAIT_SECONDS,
        metavar="SECONDS",
        help=f"how long to wait for a clear input box (default {DEFAULT_WAIT_SECONDS:.0f})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="deliver even if the owner has text in the box (it will fuse with theirs)",
    )
    args = parser.parse_args()

    message = sys.stdin.read() if args.stdin else args.message
    if not message or not message.strip():
        return fail("refusing to send an empty message")

    try:
        pane_id, label = resolve_pane(args.target)
        if not args.force:
            wait_for_clear_box(pane_id, args.wait)

        proc = herdr("pane", "run", pane_id, message)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            return fail(f"delivery failed{': ' + detail[0] if detail else ''}")

        # `pane run` writes the text and the Enter in one go, but a long paste can
        # still swallow that trailing `\r` — the text lands and nothing submits.
        # Confirm the box came back clear; if it didn't, press Enter again. That is
        # safe here precisely because we waited for an empty box first: whatever is
        # in there is our own message, not the owner's.
        for attempt in range(SUBMIT_RETRIES + 1):
            time.sleep(SETTLE_SECONDS)
            leftover = draft_text(pane_id)
            if not leftover:
                break
            if attempt == SUBMIT_RETRIES:
                return fail(
                    f"delivered to {label} ({pane_id}) but the box will not clear — the "
                    f"message is sitting unsent. box holds: {leftover[:120]!r}"
                )
            herdr("pane", "send-keys", pane_id, "Enter")
    except RuntimeError as exc:
        return fail(str(exc))
    except (json.JSONDecodeError, ValueError) as exc:
        return fail(f"could not parse herdr JSON: {exc}")
    except FileNotFoundError:
        return fail("herdr not found on PATH")
    except OSError as exc:
        return fail(f"could not run herdr: {exc}")

    print(f"delivered to {label} ({pane_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
