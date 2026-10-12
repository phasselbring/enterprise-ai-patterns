"""Reusable MCP + LangChain execution with auditable tool traces."""
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

from model_config import model_for

SERVER = Path(__file__).resolve().with_name('mcp_server.py')
PROMPT = """You are a sales-order exception investigator.
Call tools to retrieve order facts; do not fabricate numbers or ETAs.
For each order: look it up, calculate shortage, and draft a customer update if delayed.
Never claim a customer update has been sent. You cannot execute escalation.
If a tool fails, explicitly disclose the failure; do not guess.
Give order ID, shortage and estimated delay, and indicate whether approval is required.
"""


def extract_trace(messages: list[Any]) -> list[dict[str, Any]]:
    """Capture LangChain model tool calls and returned tool messages.

    This is an application-level trace, not an MCP wire trace or a full audit log.
    """
    calls: dict[str, dict[str, Any]] = {}
    for message in messages:
        for call in getattr(message, 'tool_calls', []) or []:
            calls[call.get('id') or f'call-{len(calls)}'] = {
                'tool_call_id': call.get('id'), 'name': call.get('name'),
                'args': call.get('args'), 'result': None,
            }
        call_id = getattr(message, 'tool_call_id', None)
        if call_id:
            if call_id not in calls:
                calls[call_id] = {'tool_call_id': call_id, 'name': None, 'args': None, 'result': None}
            calls[call_id]['result'] = getattr(message, 'content', None)
            calls[call_id]['status'] = getattr(message, 'status', None)
    return list(calls.values())


def normalized_response(message) -> str:
    """Extract human-readable text without provider metadata."""
    content = message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
        return "\n".join(parts)

    return str(content)


async def execute(provider: str, order_id: str = 'SO-1001') -> dict[str, Any]:
    """Launch the existing MCP server, ask a real model, return a structured record."""
    from langchain.agents import create_agent
    from langchain_mcp_adapters.client import MultiServerMCPClient

    model = model_for(provider)
    client = MultiServerMCPClient({
        'orders': {'transport': 'stdio', 'command': sys.executable, 'args': [str(SERVER)]}
    })
    start = time.perf_counter()
    tools = await client.get_tools()
    discovered = [tool.name for tool in tools]
    agent = create_agent(model=model, tools=tools, system_prompt=PROMPT)
    try:
        result = await agent.ainvoke({'messages': [{'role': 'user', 'content':
            f'Investigate {order_id}, quantify any shortage, and draft an update if delayed.'}]},
            config={'recursion_limit': 12})
        messages = result['messages']
        final = normalized_response(messages[-1])
        return {'provider': provider, 'model': model, 'order_id': order_id,
                'elapsed_seconds': round(time.perf_counter() - start, 3),
                'discovered_tools': discovered,
                'tool_trace': extract_trace(messages), 'response': final,
                'error': None}
    except Exception as exc:
        return {'provider': provider, 'model': model, 'order_id': order_id,
                'elapsed_seconds': round(time.perf_counter() - start, 3),
                'discovered_tools': discovered, 'tool_trace': [],
                'response': '', 'error': f'{type(exc).__name__}: {exc}'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=['openai', 'claude', 'gemini'], default='openai')
    parser.add_argument('--order-id', default='SO-1001')
    args = parser.parse_args()
    print(json.dumps(asyncio.run(execute(args.provider, args.order_id)), indent=2))
