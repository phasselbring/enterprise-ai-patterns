"""Single-provider entry point for the same MCP/LangChain agent."""
import asyncio
import json
import os
from agent_runner import execute

if __name__ == '__main__':
    provider = os.getenv('AGENT_PROVIDER', 'openai')
    result = asyncio.run(execute(provider))
    print('MCP tools discovered:', ', '.join(result['discovered_tools']))
    print('Tool calls:', ', '.join(x['name'] or 'unknown' for x in result['tool_trace']) or '(none)')
    print('\nAgent response:\n', result['response'])
    if result['error']:
        raise SystemExit(result['error'])
