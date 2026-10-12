"""Synthetic enterprise order exception domain. No client data or infrastructure."""
from dataclasses import dataclass
from typing import Any

ORDERS = {
    'SO-1001': {'customer':'Northwind Manufacturing','part':'P-42','quantity':30,'available':8,'eta_days':12,'account_owner':'alex@example.invalid'},
    'SO-1002': {'customer':'Bluebird Industries','part':'P-88','quantity':10,'available':15,'eta_days':0,'account_owner':'sam@example.invalid'},
}
POLICY = {'max_auto_shortage': 5, 'manager_approval_required': True}
AUDIT: list[dict[str,Any]] = []


def get_order(order_id: str) -> dict:
    if order_id not in ORDERS:
        return {'error':'order_not_found','order_id':order_id}
    return {'order_id':order_id, **ORDERS[order_id]}


def calculate_exception(order_id: str) -> dict:
    order = get_order(order_id)
    if 'error' in order:
        return order
    shortage = max(0,order['quantity']-order['available'])
    return {'order_id':order_id,'shortage':shortage,'at_risk':shortage>0,
            'estimated_delay_days':order['eta_days'] if shortage else 0,
            'requires_approval': shortage > POLICY['max_auto_shortage']}


def draft_customer_message(order_id: str) -> dict:
    order = get_order(order_id)
    exc = calculate_exception(order_id)
    if 'error' in order:
        return order
    if not exc['at_risk']:
        message = f"Order {order_id} is currently in stock for planned fulfillment."
    else:
        message = (f"Order {order_id} for {order['customer']} has a shortage of "
                   f"{exc['shortage']} units of {order['part']}. Current replenishment "
                   f"estimate: {exc['estimated_delay_days']} days. Please confirm alternatives.")
    return {'order_id':order_id,'draft':message,'status':'draft_only'}


def request_escalation(order_id: str, reason: str, approved: bool = False) -> dict:
    """Do not mutate unless caller explicitly supplies separately verified approval.

    In production, replace approved flag with server-side signed approval lookup.
    A model-provided boolean is NOT sufficient authorization.
    """
    if order_id not in ORDERS:
        return {'error':'order_not_found','order_id':order_id}
    if not approved:
        AUDIT.append({'order_id':order_id,'action':'escalation','result':'DENIED','reason':reason})
        return {'order_id':order_id,'status':'approval_required','executed':False}
    AUDIT.append({'order_id':order_id,'action':'escalation','result':'APPROVED','reason':reason})
    return {'order_id':order_id,'status':'escalation_recorded','executed':True}
