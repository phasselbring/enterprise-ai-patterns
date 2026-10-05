# Interview map: question -> code

| Interview topic | Reference implementation |
|---|---|
| Pre-retrieval query planning | `src/enterprise_ai_patterns/rag/pre_retrieval.py` |
| Lexical + vector retrieval | `src/enterprise_ai_patterns/rag/retrieval.py` |
| Reciprocal Rank Fusion | `src/enterprise_ai_patterns/rag/hybrid_search.py` |
| Authorization filtering | `src/enterprise_ai_patterns/rag/production_pipeline.py` |
| Reranking | `src/enterprise_ai_patterns/rag/reranker.py` |
| Post-retrieval context assembly | `src/enterprise_ai_patterns/rag/post_retrieval.py` |
| Citation / grounding checks | `src/enterprise_ai_patterns/rag/grounding.py` |
| Full production RAG orchestration | `src/enterprise_ai_patterns/rag/production_pipeline.py` |
| Golden-set evaluation | `src/enterprise_ai_patterns/evaluation/golden.py` |
| Recall@K / Precision@K / MRR / nDCG | `src/enterprise_ai_patterns/evaluation/metrics.py` |
| Fine-tuning dataset construction | `src/enterprise_ai_patterns/fine_tuning/dataset.py` |
| Agent boot/state/control loop | `src/enterprise_ai_patterns/agents/loop.py`, `state.py` |
| Tool discovery / registry | `src/enterprise_ai_patterns/agents/tool_registry.py` |
| Tool policy / approval / verification | `src/enterprise_ai_patterns/agents/governed_tool_call.py` |
| MCP adapter | `src/enterprise_ai_patterns/mcp/provider.py` |
| Real MCP server/client example | `examples/mcp/legal_server.py`, `examples/mcp/client.py` |
| Contract-analysis golden cases | `examples/legal_contract_analysis/golden_cases.json` |
