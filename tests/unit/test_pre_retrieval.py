from enterprise_ai_patterns.rag.pre_retrieval import BasicQueryPlanner


def test_query_planner_normalizes_and_expands():
    planner = BasicQueryPlanner(
        intent_classifier=lambda q: "legal",
        query_expander=lambda q: ["termination rights", "termination rights"],
    )
    plan = planner.plan("  What   are termination rights?  ")
    assert plan.normalized_query == "What are termination rights?"
    assert plan.intent == "legal"
    assert plan.retrieval_queries == ("What are termination rights?", "termination rights")
