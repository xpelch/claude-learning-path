"""MCP lab: client starter (claude-learning-path).

Run:  uv run python client_starter.py server_starter.py
"""
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters, types
from pydantic import AnyUrl  # noqa: F401  (needed for read_resource)
from mcp.client.stdio import stdio_client


class MCPClient:
    """Wraps a ClientSession and cleans up the connection."""

    def __init__(self, command: str, args: list[str]):
        self._params = StdioServerParameters(command=command, args=args)
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def connect(self):
        read, write = await self._stack.enter_async_context(stdio_client(self._params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("not connected")
        return self._session

    # --- Lab client ------------------------------------------------------------
    async def list_tools(self) -> list[types.Tool]:
        raise NotImplementedError("TODO: return the server's tools")

    async def call_tool(self, tool_name: str, tool_input: dict) -> types.CallToolResult | None:
        raise NotImplementedError("TODO: call the tool on the server")

    # --- Lab resources ---------------------------------------------------------
    async def read_resource(self, uri: str) -> Any:
        raise NotImplementedError("TODO: read the resource; json.loads it when the MIME type is application/json")

    # --- Lab prompts -----------------------------------------------------------
    async def list_prompts(self) -> list[types.Prompt]:
        raise NotImplementedError("TODO")

    async def get_prompt(self, prompt_name: str, args: dict[str, str]):
        raise NotImplementedError("TODO: return the rendered messages")

    async def cleanup(self):
        await self._stack.aclose()
        self._session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.cleanup()


async def main():
    server = sys.argv[1] if len(sys.argv) > 1 else "server_starter.py"
    async with MCPClient(sys.executable, [server]) as client:
        tools = await client.list_tools()
        print("tools:", [t.name for t in tools])
        result = await client.call_tool("read_doc_contents", {"doc_id": "roadmap.md"})
        print("read_doc_contents:", result)
        # Uncomment as you complete the resources and prompts labs:
        # print(json.dumps(await client.read_resource("docs://documents")))
        # print(await client.get_prompt("format", {"doc_id": "roadmap.md"}))


if __name__ == "__main__":
    asyncio.run(main())
