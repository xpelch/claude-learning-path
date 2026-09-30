"""Reference solution of the MCP lab server, used by the tests to validate the lab and its checker."""
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field

mcp = FastMCP("DocumentMCP", log_level="ERROR")

docs = {
    "roadmap.md": "Q1: ship the importer. Q2: add search. Q3: offline mode.",
    "incident-42.txt": "On March 3rd the sync job failed for 2 hours because a token expired.",
    "onboarding.md": "Install the CLI, run the setup script, then ask your buddy for repo access.",
}


@mcp.tool(name="read_doc_contents", description="Read the contents of a document and return it as a string.")
def read_document(doc_id: str = Field(description="Id of the document to read")):
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")
    return docs[doc_id]


@mcp.tool(name="edit_document", description="Edit a document by replacing an exact string with a new one.")
def edit_document(
    doc_id: str = Field(description="Id of the document to edit"),
    old_str: str = Field(description="Exact text to replace"),
    new_str: str = Field(description="Replacement text"),
):
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")
    docs[doc_id] = docs[doc_id].replace(old_str, new_str)
    return "ok"


@mcp.resource("docs://documents", mime_type="application/json")
def list_docs() -> list[str]:
    return list(docs)


@mcp.resource("docs://documents/{doc_id}", mime_type="text/plain")
def fetch_doc(doc_id: str) -> str:
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")
    return docs[doc_id]


@mcp.prompt(name="format", description="Rewrites the contents of the document in Markdown format.")
def format_document(doc_id: str = Field(description="Id of the document to format")) -> list[base.Message]:
    return [base.UserMessage(
        f"Reformat the document below in Markdown using the edit_document tool.\n<document_id>\n{doc_id}\n</document_id>"
    )]


if __name__ == "__main__":
    mcp.run(transport="stdio")
