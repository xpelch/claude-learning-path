"""MCP lab: document server starter (claude-learning-path).

Run the inspector:   uv run mcp dev server_starter.py
Check with the lab:  uv run python <plugin>/skills/mcp-lab/scripts/check_server.py server_starter.py ...
Requires: uv add "mcp[cli]<2" pydantic   (or pip install "mcp[cli]<2" pydantic)
"""
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base  # noqa: F401  (needed for the prompts lab)
from pydantic import Field  # noqa: F401  (describe tool and prompt arguments)

mcp = FastMCP("DocumentMCP", log_level="ERROR")

docs = {
    "roadmap.md": "Q1: ship the importer. Q2: add search. Q3: offline mode.",
    "incident-42.txt": "On March 3rd the sync job failed for 2 hours because a token expired.",
    "onboarding.md": "Install the CLI, run the setup script, then ask your buddy for repo access.",
    "budget.csv": "team,amount\nplatform,120000\nmobile,80000",
}

# --- Lab server-tools --------------------------------------------------------
# TODO: a tool `read_doc_contents(doc_id)` returning the document's text.
#       Raise ValueError with a clear message when the id is unknown.
# TODO: a tool `edit_document(doc_id, old_str, new_str)` doing a find-and-replace.
#       Give every argument a Field(description=...).

# --- Lab resources -------------------------------------------------------------
# TODO: a direct resource  docs://documents            (application/json) listing the ids.
# TODO: a templated one    docs://documents/{doc_id}   (text/plain) returning one document.

# --- Lab prompts ---------------------------------------------------------------
# TODO: a prompt `format(doc_id)` returning [base.UserMessage(...)] that asks Claude to
#       rewrite the document in Markdown using the edit_document tool.


if __name__ == "__main__":
    mcp.run(transport="stdio")
