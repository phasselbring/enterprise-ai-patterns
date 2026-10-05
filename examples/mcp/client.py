import anyio
from mcp import Client


async def main() -> None:
    async with Client("http://localhost:8000/mcp") as client:
        tools = await client.list_tools()
        print([tool.name for tool in tools.tools])

        result = await client.call_tool(
            "lookup_clause",
            {"contract_id": "msa-42", "clause_type": "termination"},
        )
        print(result.structured_content)
        print("is_error:", result.is_error)


if __name__ == "__main__":
    anyio.run(main)
