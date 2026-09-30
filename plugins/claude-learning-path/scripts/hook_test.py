#!/usr/bin/env python3
"""Dry-run a Claude Code hook against a synthetic event and explain the outcome.

Usage:
  hook_test.py --event PreToolUse --tool Bash --input '{"command": "git push origin main"}' -- <hook command...>
  hook_test.py --event PreToolUse --tool Bash --input '{...}' --settings .claude/settings.json
  hook_test.py --event Stop -- <hook command...>

With --settings, every hook in that file whose event and matcher fit is run.
The hook receives the event JSON on stdin, like in Claude Code. The report
applies the rules from "Claude Code in Action — Hooks":
  exit 0  -> success; stdout JSON is parsed (plain text only reaches context
             on SessionStart, UserPromptSubmit, UserPromptExpansion)
  exit 2  -> blocking error, stderr is fed back to Claude
  other   -> non-blocking (exit 1 does NOT block)
This is a local approximation for learning, not Claude Code itself.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CONTEXT_EVENTS = {"SessionStart", "UserPromptSubmit", "UserPromptExpansion"}
NO_BLOCK_EVENTS = {"Notification", "SessionStart"}
TOOL_EVENTS = {"PreToolUse", "PostToolUse"}


def payload(args, tool_input):
    p = {"session_id": "hook-test", "hook_event_name": args.event, "cwd": str(Path.cwd())}
    if args.event in TOOL_EVENTS:
        p.update(tool_name=args.tool, tool_input=tool_input)
    if args.event == "PostToolUse":
        p["tool_response"] = {"success": True}
    if args.event in ("Stop", "SubagentStop"):
        p["stop_hook_active"] = False
    if args.event == "SessionStart":
        p["source"] = args.source
    if args.event == "UserPromptSubmit":
        p["prompt"] = args.prompt or ""
    return p


def hooks_from_settings(path, event, tool):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    found = []
    for group in cfg.get("hooks", {}).get(event, []):
        matcher = group.get("matcher", "")
        if event in TOOL_EVENTS and matcher not in ("", "*") and not re.fullmatch(matcher, tool or ""):
            continue
        if event == "SessionStart" and matcher not in ("", "*") and not re.fullmatch(matcher, tool or ""):
            continue
        for h in group.get("hooks", []):
            if h.get("type", "command") == "command":
                found.append((matcher, h["command"]))
    return found


def explain(args, tool_input, code, out, err):
    lines = [f"exit code: {code}"]
    verdict = "PROCEEDS"
    if code == 2:
        if args.event in NO_BLOCK_EVENTS:
            lines.append(f"exit 2 on {args.event}: this event ignores blocking; stderr is shown and it carries on.")
        elif args.event == "PostToolUse":
            verdict = "FEEDBACK"
            lines.append("exit 2 on PostToolUse: the tool already ran (too late to stop it), "
                         "but stderr is fed back to Claude.")
        elif args.event in ("Stop", "SubagentStop"):
            verdict = "BLOCKED"
            lines.append("exit 2 on Stop: Claude is NOT allowed to finish; stderr tells it why.")
        else:
            verdict = "BLOCKED"
            lines.append("exit 2: blocking error; stderr is fed back to Claude.")
        if not err.strip():
            lines.append("warning: exit 2 with empty stderr gives Claude no reason to act on.")
    elif code == 0:
        data = None
        if out.strip():
            try:
                data = json.loads(out)
            except json.JSONDecodeError:
                if args.event in CONTEXT_EVENTS:
                    lines.append("plain-text stdout will be ADDED TO CONTEXT on this event.")
                else:
                    lines.append("plain-text stdout is ignored on this event.")
        if isinstance(data, dict):
            hso = data.get("hookSpecificOutput", {})
            decision = hso.get("permissionDecision")
            if decision:
                verdict = {"deny": "BLOCKED", "ask": "ASKS USER", "allow": "ALLOWED", "defer": "DEFERRED"}.get(decision, "?")
                lines.append(f"permissionDecision: {decision}"
                             + (f" — reason: {hso.get('permissionDecisionReason')}" if hso.get("permissionDecisionReason") else ""))
                if decision == "defer":
                    lines.append("note: defer only applies to non-interactive -p runs.")
                if args.event != "PreToolUse":
                    lines.append("warning: permissionDecision is a PreToolUse field.")
            if "updatedInput" in hso:
                new = hso["updatedInput"]
                verdict = "REWRITTEN" if verdict in ("PROCEEDS", "ALLOWED") else verdict
                lines.append(f"updatedInput: {json.dumps(new)}")
                missing = sorted(set(tool_input) - set(new or {}))
                if missing:
                    lines.append(f"warning: updatedInput replaces the WHOLE input; fields dropped: {', '.join(missing)}")
            if data.get("decision") == "block":
                verdict = "BLOCKED"
                lines.append(f"decision: block — {data.get('reason', '')}")
    else:
        lines.append(f"exit {code} is NON-BLOCKING: stderr is logged and the action goes ahead."
                     + (" (Use exit 2 to block, not 1.)" if code == 1 else ""))
    if err.strip():
        lines.append("stderr: " + err.strip()[:500])
    if out.strip():
        lines.append("stdout: " + out.strip()[:500])
    return verdict, lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--event", required=True)
    ap.add_argument("--tool", default="Bash")
    ap.add_argument("--input", default="{}", help="tool_input as JSON")
    ap.add_argument("--source", default="startup", help="SessionStart source (startup, resume, compact, clear)")
    ap.add_argument("--prompt", help="prompt text for UserPromptSubmit")
    ap.add_argument("--settings", help="settings.json to read hooks from")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("command", nargs=argparse.REMAINDER, help="-- <hook command>")
    args = ap.parse_args()

    tool_input = json.loads(args.input)
    cmd = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.settings:
        match_on = args.source if args.event == "SessionStart" else args.tool
        hooks = hooks_from_settings(args.settings, args.event, match_on)
        if not hooks:
            print(f"No {args.event} hook in {args.settings} matches '{match_on}'.")
            return 0
    elif cmd:
        joined = cmd[0] if len(cmd) == 1 else (subprocess.list2cmdline(cmd) if os.name == "nt" else shlex.join(cmd))
        hooks = [("(cli)", joined)]
    else:
        ap.error("give a hook command after -- or use --settings")

    event = json.dumps(payload(args, tool_input))
    print(f"event: {event}\n")
    final = "PROCEEDS"
    for matcher, command in hooks:
        try:
            r = subprocess.run(command, shell=True, input=event, capture_output=True, text=True,
                               timeout=args.timeout, encoding="utf-8")
            verdict, lines = explain(args, tool_input, r.returncode, r.stdout, r.stderr)
        except subprocess.TimeoutExpired:
            verdict, lines = "PROCEEDS", [f"timed out after {args.timeout}s (non-blocking)"]
        print(f"hook [{matcher}] {command}\n  -> {verdict}")
        for l in lines:
            print("     " + l)
        if verdict == "BLOCKED":
            final = "BLOCKED"
        elif verdict in ("REWRITTEN", "ASKS USER") and final != "BLOCKED":
            final = verdict
    print(f"\nresult: {final}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
