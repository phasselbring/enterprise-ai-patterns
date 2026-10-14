import pytest

from enterprise_ai_patterns.rag.pipeline import Caller
from enterprise_ai_patterns.rag.pre_retrieval import RuleBasedQueryPlanner, RoutedQuery
from enterprise_ai_patterns.rag.routing import RetrievalRouter


def test_rule_planner_decomposes_explicit_manufacturing_request():
    p = RuleBasedQueryPlanner()
    plan = p.plan('Compare open manufacturing orders in Florida against inventory availability and shortage escalation policy')
    assert plan.intent == 'order_exception_analysis'
    assert plan.metadata_filters == {'region': 'FL', 'order_status': 'open'}
    routes = p.routed_queries(plan)
    assert {'erp_orders', 'inventory', 'policy_documents'} <= {r.source for r in routes}
    assert len({r.query for r in routes}) == len(routes)


def test_unknown_query_does_not_invent_filters_or_business_routes():
    p = RuleBasedQueryPlanner()
    plan = p.plan('  Explain   the warranty   document  ')
    assert plan.metadata_filters == {}
    assert plan.normalized_query == 'Explain the warranty document'
    assert all(q.source == 'policy_documents' for q in p.routed_queries(plan))


def test_route_dispatch_preserves_identity_and_filters():
    calls = []
    class Backend:
        def search(self, query, *, limit, caller, metadata_filters):
            calls.append((query, limit, caller.user_id, metadata_filters))
            return ['ok']
    router = RetrievalRouter({'erp_orders': Backend()})
    assert router.search(RoutedQuery('manufacturing orders', 'erp_orders'),
                         caller=Caller('alice', ('operations',)), limit=7,
                         metadata_filters={'region':'FL'}) == ['ok']
    assert calls == [('manufacturing orders', 7, 'alice', {'region':'FL'})]


def test_route_fails_closed_for_unknown_source_and_missing_caller():
    router = RetrievalRouter({'erp_orders': object()})
    with pytest.raises(ValueError, match='Unconfigured'):
        router.search(RoutedQuery('q', 'arbitrary_endpoint'), caller=Caller('alice', ('a',)))
    with pytest.raises(PermissionError):
        router.search(RoutedQuery('q', 'erp_orders'), caller=None)
