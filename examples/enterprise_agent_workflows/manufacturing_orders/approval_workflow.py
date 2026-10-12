"""A LangGraph approval/resume reference, with NO external side effects.

The human approval comes from an interrupt resume input, not from the model.
A real service must authenticate the approver and verify an authorization token
server-side; this reference only demonstrates the graph's pause/resume behavior.
"""
from typing import TypedDict
from uuid import uuid4

from domain import calculate_exception


class State(TypedDict, total=False):
    order_id: str
    shortage: int
    approved: bool
    outcome: str


def build_graph():
    from langgraph.graph import StateGraph, START, END
    from langgraph.types import interrupt
    from langgraph.checkpoint.memory import InMemorySaver

    def investigate(state: State):
        data = calculate_exception(state['order_id'])
        if 'error' in data:
            return {'shortage': 0, 'outcome': 'not_found'}
        return {'shortage': data['shortage']}

    def route(state: State) -> str:
        if state.get('outcome') == 'not_found':
            return 'end'
        return 'approve' if state['shortage'] > 5 else 'end'

    def approval(state: State):
        decision = interrupt({'action': 'record_escalation', 'order_id': state['order_id'],
                              'shortage': state['shortage'], 'requires_human_approval': True})
        # No model-controlled field may bypass this interrupt.
        return {'approved': decision is True}

    def finalize(state: State):
        # No real mutations here; this records a simulated outcome only.
        return {'outcome': 'simulation_approved' if state.get('approved') else 'simulation_denied'}

    builder = StateGraph(State)
    builder.add_node('investigate', investigate)
    builder.add_node('approve', approval)
    builder.add_node('finalize', finalize)
    builder.add_edge(START, 'investigate')
    builder.add_conditional_edges('investigate', route, {'approve': 'approve', 'end': END})
    builder.add_edge('approve', 'finalize')
    builder.add_edge('finalize', END)
    return builder.compile(checkpointer=InMemorySaver())


def demo(approve=False):
    from langgraph.types import Command
    graph = build_graph()
    config = {'configurable': {'thread_id': str(uuid4())}}
    initial = graph.invoke({'order_id': 'SO-1001'}, config=config)
    print('Initial result (approval requested):', initial)
    assert '__interrupt__' in initial, 'Expected human-approval interrupt'
    resumed = graph.invoke(Command(resume=approve), config=config)
    print('Resumed result:', resumed)
    assert resumed['outcome'] == ('simulation_approved' if approve else 'simulation_denied')


if __name__ == '__main__':
    demo(approve=False)
