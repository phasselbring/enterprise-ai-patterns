"""MCP tool server; requires: pip install 'mcp>=2,<3'."""
from mcp.server.fastmcp import FastMCP
from domain import get_order, calculate_exception, draft_customer_message

mcp = FastMCP('synthetic-order-exceptions')

@mcp.tool()
def lookup_order(order_id: str) -> dict:
    """Read one synthetic sales order by its identifier."""
    return get_order(order_id)

@mcp.tool()
def check_inventory_shortage(order_id: str) -> dict:
    """Calculate shortfall and whether escalation approval is required."""
    return calculate_exception(order_id)

@mcp.tool()
def propose_customer_update(order_id: str) -> dict:
    """Draft (never send) a customer status message."""
    return draft_customer_message(order_id)

if __name__ == '__main__':
    mcp.run(transport='stdio')
