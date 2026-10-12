"""Runnable without dependencies/API keys. Shows the same business workflow."""
import json
from domain import get_order, calculate_exception, draft_customer_message, request_escalation

def run(order_id='SO-1001'):
    result = {'order':get_order(order_id),'exception':calculate_exception(order_id),
              'message':draft_customer_message(order_id)}
    if result['exception'].get('requires_approval'):
        result['escalation'] = request_escalation(order_id, 'Stock shortage', approved=False)
    return result

if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
