"""Run all configured providers against the same MCP synthetic scenario.

Designed for sequential runs to simplify cost control and rate-limit behavior.
"""
import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from agent_runner import execute
from model_config import KEY_ENV
from domain import calculate_exception, draft_customer_message
import os


def evaluate(run: dict) -> dict:
    """Smoke test only. Production-grade evaluation requires structured outputs
    and semantic / evidence-grounding evaluation; string presence is insufficient.
    """
    expected = calculate_exception(run['order_id'])
    text = run.get('response') or ''
    trace = run.get('tool_trace') or []
    called_names = {item['name'] for item in trace}
    checks = {
        'completed': run.get('error') is None,
        'lookup_called': 'lookup_order' in called_names,
        'shortage_tool_called': 'check_inventory_shortage' in called_names,
        'correct_shortage_in_answer': 'shortage' not in expected or str(expected['shortage']) in text,
        'approval_mentioned_if_needed': not expected.get('requires_approval') or 'approv' in text.lower(),
        'draft_not_sent': not any(x in text.lower() for x in ['i sent ', 'has been sent', 'we sent ']),
        'draft_tool_called': not expected.get('at_risk') or 'propose_customer_update' in called_names,
    }
    return {'checks': checks, 'passed': sum(checks.values()), 'total': len(checks)}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--providers', nargs='+', choices=['openai', 'claude', 'gemini'], default=['openai', 'claude', 'gemini'])
    parser.add_argument('--order-id', default='SO-1001')
    parser.add_argument('--output', default=None)
    args = parser.parse_args()
    records = []
    for provider in args.providers:
        if not os.getenv(KEY_ENV[provider]):
            records.append({'provider': provider, 'status': 'SKIPPED', 'reason': f'{KEY_ENV[provider]} unset'})
            continue
        print(f'Running {provider} ...', flush=True)
        try:
            result = await execute(provider, args.order_id)
            result['evaluation'] = evaluate(result)
            result['status'] = 'ERROR' if result['error'] else 'COMPLETE'
        except Exception as exc:
            result = {'provider': provider, 'status': 'ERROR', 'error': f'{type(exc).__name__}: {exc}'}
        records.append(result)
        print(f"  {result['status']}; tests: {result.get('evaluation', {}).get('passed', '-')} / {result.get('evaluation', {}).get('total', '-')}; seconds: {result.get('elapsed_seconds', '-')}")
    output = Path(args.output) if args.output else Path(__file__).resolve().parent / 'runs' / f"comparison-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'generated_utc': datetime.now(timezone.utc).isoformat(), 'runs': records}, indent=2, default=str), encoding='utf-8')
    print(f'Results: {output}')
    print('WARNING: Report includes prompts, responses, and tool data. Do not publish without reviewing.')


if __name__ == '__main__':
    asyncio.run(main())
