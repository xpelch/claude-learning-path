"""Test PreToolUse guard: blocks pushes to main, redacts sk_live_ secrets (drops other fields on purpose)."""
import json
import re
import sys

event = json.load(sys.stdin)
command = event["tool_input"].get("command", "")
if re.search(r"git push .*\b(main|master)\b", command):
    print("pushing to main is not allowed", file=sys.stderr)
    sys.exit(2)
if "sk_live_" in command:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "updatedInput": {"command": re.sub(r"sk_live_\w+", "sk_live_REDACTED", command)},
    }}))
