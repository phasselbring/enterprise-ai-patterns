"""Synthetic MCP server for interview/demo use.

Install:  python -m pip install -e ".[mcp]"
Run:      mcp run examples/mcp/legal_server.py --transport streamable-http
Default:  http://localhost:8000/mcp
"""

from mcp.server import MCPServer

mcp = MCPServer(
    "Synthetic Legal Tools",
    instructions="Use contract tools only for synthetic demonstration data.",
)


@mcp.tool()
def lookup_clause(contract_id: str, clause_type: str) -> dict:
    """Look up a synthetic contract clause by type."""
    synthetic = {
        ("msa-42", "termination"): {
            "source_id": "msa-42:12.4",
            "heading": "Termination for Convenience",
            "text": "Either party may terminate with thirty days written notice.",
        },
        ("msa-42", "liability"): {
            "source_id": "msa-42:10.2",
            "heading": "Limitation of Liability",
            "text": "The liability cap does not apply to IP infringement indemnity.",
        },
    }
    return synthetic.get(
        (contract_id, clause_type.lower()),
        {"error": "clause not found", "contract_id": contract_id, "clause_type": clause_type},
    )


@mcp.tool()
def search_playbook(topic: str) -> dict:
    """Return a synthetic legal-playbook position."""
    return {
        "topic": topic,
        "preferred": "Mutual limitation of liability with a negotiated cap.",
        "escalate_if": "IP, confidentiality, or data obligations are uncapped.",
    }
