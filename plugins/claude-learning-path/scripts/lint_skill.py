#!/usr/bin/env python3
"""Lint agent skills against the rules taught in "Introduction to agent skills".

Usage:
  lint_skill.py <path> [<path> ...] [--json]

<path> may be a SKILL.md file, a skill directory, or a skills root containing
several skill directories. Exit code: 0 when no errors, 1 otherwise.

Checks: file name and location, frontmatter syntax, name rules (lowercase,
digits, hyphens, max 64, matches directory), description (present, max 1024,
says when to use it), body length (< 500 lines), broken relative links,
backslash paths, bare Bash in allowed-tools, script shebang/executable bit.
"""
import json
import os
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KNOWN_KEYS = {
    "name", "description", "allowed-tools", "disallowed-tools", "model", "license", "metadata",
    "compatibility", "user-invocable", "disable-model-invocation", "argument-hint", "when_to_use",
    "context", "agent", "hooks", "effort", "paths", "shell", "version",
}
WHEN_RE = re.compile(r"\b(use (it |this )?when|use for|when the user|when you|trigger|whenever)\b", re.I)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BACKSLASH_RE = re.compile(r"(?<![\\`])\b[\w.-]+\\[\w.-]+\\?[\w.-]*")


class Report:
    def __init__(self, target):
        self.target = str(target)
        self.items = []

    def add(self, level, code, msg, line=None):
        self.items.append({"level": level, "code": code, "message": msg, **({"line": line} if line else {})})

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "error"]


def parse_frontmatter(lines, rep):
    """Tiny YAML subset: key: value, quoted values, block lists, | and > scalars."""
    if not lines or lines[0].strip() != "---":
        rep.add("error", "no-frontmatter", "SKILL.md must start with a '---' frontmatter line", 1)
        return None, 0
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        rep.add("error", "unclosed-frontmatter", "frontmatter has no closing '---'", 1)
        return None, 0
    data, key, block = {}, None, None
    for n in range(1, end):
        raw = lines[n]
        if not raw.strip() or raw.lstrip().startswith("#"):
            if block is not None and key:
                data[key] += "\n"
            continue
        indented = raw[:1] in (" ", "\t")
        if indented and key is not None:
            s = raw.strip()
            if block is not None:
                data[key] = (data[key] + " " + s).strip() if block == ">" else (data[key] + "\n" + s).lstrip("\n")
            elif s.startswith("- "):
                if not isinstance(data[key], list):
                    data[key] = []
                data[key].append(s[2:].strip().strip("'\""))
            elif isinstance(data[key], dict) or data[key] == "":
                data[key] = {} if data[key] == "" else data[key]
            else:
                rep.add("error", "yaml", f"unexpected indented line: {s!r}", n + 1)
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$", raw.rstrip())
        if not m:
            rep.add("error", "yaml", f"cannot parse frontmatter line: {raw.strip()!r}", n + 1)
            key, block = None, None
            continue
        key, val = m.group(1), (m.group(2) or "").strip()
        block = None
        if val in ("|", ">", "|-", ">-"):
            block, val = val[0], ""
        elif len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1]
        elif val.startswith(("'", '"')):
            rep.add("error", "yaml", f"unterminated quote in '{key}'", n + 1)
        elif ": " in val and not val.startswith(("[", "{")):
            rep.add("warning", "yaml-colon", f"value of '{key}' contains ': ' — quote it to be safe", n + 1)
        if key in data:
            rep.add("error", "yaml", f"duplicate key '{key}'", n + 1)
        data[key] = val
    return data, end


def lint_file(skill_md):
    skill_md = Path(skill_md)
    rep = Report(skill_md)
    skill_dir = skill_md.parent
    if skill_md.name != "SKILL.md":
        rep.add("error", "file-name", f"file must be named exactly SKILL.md (found {skill_md.name})")
    if skill_dir.name == "skills":
        rep.add("error", "skills-root", "SKILL.md sits at the skills root; put it inside a named directory, "
                                        "e.g. skills/<skill-name>/SKILL.md")
    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        rep.add("error", "encoding", "SKILL.md is not valid UTF-8")
        return rep
    lines = text.splitlines()
    fm, end = parse_frontmatter(lines, rep)
    if fm is None:
        return rep

    name = fm.get("name")
    if not name:
        rep.add("error", "name-missing", "frontmatter is missing 'name'")
    else:
        if not NAME_RE.match(name):
            rep.add("error", "name-format", f"name '{name}' must use lowercase letters, digits and single hyphens")
        if len(name) > 64:
            rep.add("error", "name-length", f"name is {len(name)} characters (max 64)")
        if skill_dir.name != "skills" and name != skill_dir.name:
            rep.add("warning", "name-dir", f"name '{name}' differs from directory '{skill_dir.name}'")

    desc = fm.get("description")
    if not desc:
        rep.add("error", "description-missing", "frontmatter is missing 'description' (it is what triggers the skill)")
    elif isinstance(desc, str):
        if len(desc) > 1024:
            rep.add("error", "description-length", f"description is {len(desc)} characters (max 1024)")
        if len(desc) < 40:
            rep.add("warning", "description-short", "description is very short; say what the skill does and when to use it")
        if not WHEN_RE.search(desc):
            rep.add("warning", "description-when", "description doesn't say when to use the skill "
                                                   "(add e.g. 'Use when the user asks to ...' with real trigger phrases)")

    tools = fm.get("allowed-tools")
    tool_list = tools if isinstance(tools, list) else [t.strip() for t in str(tools or "").split(",")]
    if "Bash" in tool_list:
        rep.add("warning", "bare-bash", "allowed-tools pre-approves bare 'Bash' (any command); narrow it, "
                                        "e.g. Bash(git status *)")

    for k in fm:
        if k not in KNOWN_KEYS:
            rep.add("info", "unknown-key", f"frontmatter key '{k}' is not a common skill field")

    body = lines[end + 1:]
    if not any(l.strip() for l in body):
        rep.add("warning", "empty-body", "no instructions after the frontmatter")
    if len(lines) > 500:
        rep.add("warning", "too-long", f"SKILL.md has {len(lines)} lines; keep it under 500 and move detail "
                                       "to references/ (progressive disclosure)")

    in_code = False
    for i, line in enumerate(body, start=end + 2):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        for target in LINK_RE.findall(line):
            if re.match(r"^[a-z][a-z0-9+.-]*:|^#|^\$\{", target, re.I):
                continue
            if not (skill_dir / target.split("#")[0]).exists():
                rep.add("error", "broken-link", f"linked file not found: {target}", i)
        if not in_code and BACKSLASH_RE.search(line.replace("\\n", "")) and "\\" in line:
            rep.add("warning", "backslash-path", "path uses backslashes; use forward slashes everywhere", i)

    scripts = skill_dir / "scripts"
    if scripts.is_dir():
        for f in sorted(scripts.iterdir()):
            if f.suffix in (".sh", ".py", ".bash") and f.is_file():
                head = f.read_bytes()[:2]
                if head != b"#!":
                    rep.add("info", "no-shebang", f"scripts/{f.name} has no shebang line")
                if os.name != "nt" and not os.access(f, os.X_OK):
                    rep.add("warning", "not-executable", f"scripts/{f.name} is not executable (chmod +x)")
    return rep


def actual(path):
    """Path with the on-disk spelling of its name (file systems may be case-insensitive)."""
    path = Path(path)
    for f in path.parent.iterdir():
        if f.name.lower() == path.name.lower():
            return f
    return path


def collect(path):
    p = Path(path)
    if p.is_file():
        return [actual(p)]
    if not p.is_dir():
        r = Report(p)
        r.add("error", "not-found", "path does not exist")
        return [r]
    def skill_files(d):
        return [f for f in d.iterdir() if f.is_file() and f.name.lower() == "skill.md"]

    here = skill_files(p)
    if here:
        return here
    found = [f for d in sorted(p.iterdir()) if d.is_dir() for f in skill_files(d)]
    if not found:
        r = Report(p)
        r.add("error", "no-skill", "no SKILL.md found in this directory or its subdirectories")
        return [r]
    return found


def main(argv):
    as_json = "--json" in argv
    paths = [a for a in argv if a != "--json"]
    if not paths:
        print(__doc__)
        return 2
    reports = []
    for p in paths:
        for item in collect(p):
            reports.append(item if isinstance(item, Report) else lint_file(item))
    if as_json:
        print(json.dumps([{"target": r.target, "items": r.items} for r in reports], indent=2))
    else:
        for r in reports:
            status = "FAIL" if r.errors else "ok"
            print(f"{status}  {r.target}")
            for i in r.items:
                loc = f":{i['line']}" if "line" in i else ""
                print(f"  {i['level']:<7} {i['code']}{loc}  {i['message']}")
        n_err = sum(len(r.errors) for r in reports)
        print(f"\n{len(reports)} skill(s) checked, {n_err} error(s)")
    return 1 if any(r.errors for r in reports) else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
