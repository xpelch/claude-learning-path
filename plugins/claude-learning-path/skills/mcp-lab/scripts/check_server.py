#!/usr/bin/env python3
"""Connect to an MCP server over stdio and check what it exposes.

Needs the `mcp` Python SDK in the interpreter that runs this script, e.g.:
  uv run python check_server.py mcp_server.py --expect-tools read_doc_contents,edit_document

Options:
  --server-python EXE        interpreter for the server (default: this one)
  --expect-tools a,b         tool names that must exist
  --expect-resources uri,..  direct resource URIs that must exist
  --expect-templates uri,..  resource template URIs that must exist
  --expect-prompts a,b       prompt names that must exist
  --call NAME JSON           call a tool (repeatable); fails on error results
  --read URI                 read a resource (repeatable)
  --get-prompt NAME JSON     render a prompt (repeatable)
Exit code 0 when every expectation and call succeeds.
"""
import argparse
import asyncio
import json
import sys


async def run(args):
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from pydantic import AnyUrl
    except ImportError:
        print("error: the `mcp` package is not installed for this interpreter "
              "(run inside the project environment, e.g. `uv run python ...`)")
        return 2

    params = StdioServerParameters(command=args.server_python or sys.executable, args=[args.server])
    failures = []

    def check(ok, msg):
        print(("  ok    " if ok else "  FAIL  ") + msg)
        if not ok:
            failures.append(msg)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name: t for t in (await session.list_tools()).tools}
            print(f"tools: {sorted(tools)}")
            for t in tools.values():
                props = (t.inputSchema or {}).get("properties", {})
                undocumented = [p for p, s in props.items() if not s.get("description")]
                if not t.description:
                    print(f"  warn  tool {t.name} has no description")
                if undocumented:
                    print(f"  warn  tool {t.name}: arguments without description: {undocumented}")
            resources, templates, prompts = [], [], []
            try:
                resources = [str(r.uri) for r in (await session.list_resources()).resources]
                templates = [t.uriTemplate for t in (await session.list_resource_templates()).resourceTemplates]
            except Exception as e:  # server may not support resources
                print(f"  note  resources not available: {e}")
            try:
                prompts = [p.name for p in (await session.list_prompts()).prompts]
            except Exception as e:
                print(f"  note  prompts not available: {e}")
            print(f"resources: {resources}\ntemplates: {templates}\nprompts: {prompts}\n")

            for name in filter(None, (args.expect_tools or "").split(",")):
                check(name in tools, f"tool {name} exists")
            for uri in filter(None, (args.expect_resources or "").split(",")):
                check(uri in resources, f"resource {uri} exists")
            for uri in filter(None, (args.expect_templates or "").split(",")):
                check(uri in templates, f"resource template {uri} exists")
            for name in filter(None, (args.expect_prompts or "").split(",")):
                check(name in prompts, f"prompt {name} exists")

            for name, raw in args.call or []:
                try:
                    res = await session.call_tool(name, json.loads(raw))
                    text = " ".join(getattr(c, "text", "") for c in res.content)
                    check(not res.isError, f"call {name}({raw}) -> {text[:200]!r}")
                except Exception as e:
                    check(False, f"call {name}({raw}) raised {e}")
            for uri in args.read or []:
                try:
                    res = await session.read_resource(AnyUrl(uri))
                    c = res.contents[0]
                    check(True, f"read {uri} [{getattr(c, 'mimeType', None)}] -> {getattr(c, 'text', '')[:200]!r}")
                except Exception as e:
                    check(False, f"read {uri} raised {e}")
            for name, raw in args.get_prompt or []:
                try:
                    res = await session.get_prompt(name, json.loads(raw))
                    first = res.messages[0].content
                    check(bool(res.messages), f"prompt {name}({raw}) -> {len(res.messages)} message(s): "
                                              f"{getattr(first, 'text', str(first))[:200]!r}")
                except Exception as e:
                    check(False, f"prompt {name}({raw}) raised {e}")

    print(f"\n{'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s))")
    return 0 if not failures else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("server", help="path to the server script (run over stdio)")
    ap.add_argument("--server-python")
    ap.add_argument("--expect-tools"); ap.add_argument("--expect-resources")
    ap.add_argument("--expect-templates"); ap.add_argument("--expect-prompts")
    ap.add_argument("--call", nargs=2, action="append", metavar=("NAME", "JSON"))
    ap.add_argument("--read", action="append", metavar="URI")
    ap.add_argument("--get-prompt", nargs=2, action="append", metavar=("NAME", "JSON"))
    return asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
