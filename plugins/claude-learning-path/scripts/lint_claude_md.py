#!/usr/bin/env python3
"""Audit a CLAUDE.md against "Claude Code in Action — A CLAUDE.md that follows".

Usage:
  lint_claude_md.py <CLAUDE.md> [--json]

Advice only (exit code 0 unless the file is missing). Flags:
  size        long files compete with themselves (imports are counted too,
              because they expand inline at launch)
  vague       rules nobody can check ("best practices", "clean", "properly")
  no-replace  bans that don't name what to do instead
  hard-rule   rules that sound like they must never be broken -> use a hook
  emphasis    too many IMPORTANT/MUST/NEVER: emphasis is a budget
  import      @imports that don't exist
  duplicate   repeated lines
"""
import json
import re
import sys
from pathlib import Path

VAGUE = re.compile(r"\b(best practices?|clean code|properly|appropriate(ly)?|as needed|good (code|practice)|"
                   r"high[- ]quality|well[- ]structured|nice|make sure it works|be careful|when relevant)\b", re.I)
BAN = re.compile(r"^\s*(?:[-*]\s+|\d+\.\s+)?(?:don'?t|do not|never|avoid|no)\b", re.I)
BAN_PREFIX = re.compile(r"^\s*(?:[-*]\s+|\d+\.\s+)?(?:don'?t|do not|never|avoid|no)\s+(?:use\s+)?", re.I)
REPLACEMENT = re.compile(r"\b(instead|use|prefer|rather than|replace)\b|, not\b", re.I)
HARD = re.compile(r"(push(ing)? (directly )?to (main|master)|force[- ]push|rm -rf|drop (table|database)|"
                  r"delete (the )?(database|prod)|production|deploy|secrets?|credentials?|api keys?|\.env\b|"
                  r"migrations?)", re.I)
EMPHASIS = re.compile(r"\b(IMPORTANT|MUST|NEVER|ALWAYS|CRITICAL|REQUIRED)\b|!!")
IMPORT = re.compile(r"(?:^|\s)@((?:~|\.{1,2})?/?[\w./-]+\.\w+)")


def audit(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    items = []

    def add(level, code, msg, line=None):
        items.append({"level": level, "code": code, "message": msg, **({"line": line} if line else {})})

    imported_lines = 0
    in_code = False
    seen = {}
    emphasis = 0
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s:
            continue
        for m in IMPORT.finditer(line):
            target = Path(m.group(1)).expanduser()
            target = target if target.is_absolute() else (p.parent / target)
            if target.exists():
                imported_lines += len(target.read_text(encoding="utf-8", errors="replace").splitlines())
            else:
                add("warning", "import", f"imported file not found: {m.group(1)}", n)
        if s.startswith("#"):
            continue
        if VAGUE.search(s):
            add("warning", "vague", f"not checkable: \"{VAGUE.search(s).group(0)}\" — say exactly what to do "
                                    f"so the result can be verified", n)
        if BAN.search(s) and not REPLACEMENT.search(BAN_PREFIX.sub("", s)):
            add("info", "no-replace", "ban without a replacement — name what to do instead "
                                      "(e.g. \"use named exports, not default exports\")", n)
        if HARD.search(s) and BAN.search(s):
            add("warning", "hard-rule", f"sounds like a rule that must never break (\"{HARD.search(s).group(0)}\"); "
                                        "enforce it with a PreToolUse hook instead of hoping it's followed", n)
        emphasis += len(EMPHASIS.findall(line))
        key = re.sub(r"\W+", " ", s.lower()).strip()
        if len(key) > 20:
            if key in seen:
                add("info", "duplicate", f"same rule as line {seen[key]}", n)
            else:
                seen[key] = n

    total = len(lines) + imported_lines
    if total > 200:
        add("warning", "size", f"{total} lines loaded at launch ({len(lines)} here + {imported_lines} imported); "
                               "every line competes for attention — cut what you can't justify")
    elif imported_lines:
        add("info", "size", f"{total} lines loaded at launch; imports organize but don't reduce context")
    if emphasis > 3:
        add("warning", "emphasis", f"{emphasis} emphasis markers (IMPORTANT/MUST/NEVER/…); keep them for the "
                                   "2–3 rules that hurt most when broken")
    return {"target": str(p), "lines": len(lines), "imported_lines": imported_lines, "items": items}


def main(argv):
    as_json = "--json" in argv
    paths = [a for a in argv if a != "--json"]
    if not paths:
        print(__doc__)
        return 2
    if not Path(paths[0]).is_file():
        print(f"error: {paths[0]} not found")
        return 1
    rep = audit(paths[0])
    if as_json:
        print(json.dumps(rep, indent=2))
        return 0
    print(f"{rep['target']}: {rep['lines']} lines (+{rep['imported_lines']} imported)")
    order = {"warning": 0, "info": 1}
    for i in sorted(rep["items"], key=lambda i: (order[i["level"]], i.get("line", 0))):
        loc = f":{i['line']}" if "line" in i else ""
        print(f"  {i['level']:<7} {i['code']}{loc}  {i['message']}")
    n = sum(i["level"] == "warning" for i in rep["items"])
    print(f"\n{n} warning(s). The leaner the file, the more of it Claude follows.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
