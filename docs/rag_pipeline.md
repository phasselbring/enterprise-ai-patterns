# Production RAG lifecycle

## Ingestion / indexing (before any user query)

Parsing, OCR, structure detection, chunking/clause segmentation, metadata, ACLs, embeddings,
and lexical/vector index construction happen here. Chunking is therefore **pre-query** work;
it is usually clearer to call it ingestion/indexing rather than query-time pre-retrieval.

## Pre-retrieval (query time)

Normalize the question, classify intent, rewrite/expand/decompose it, choose corpora/indexes, and
attach metadata/security constraints. See `rag/pre_retrieval.py`.

## Retrieval

Perform inexpensive high-recall first-stage search. `rag/retrieval.py` performs lexical and dense
retrieval and `rag/hybrid_search.py` combines their ranks with Reciprocal Rank Fusion.

## Filtering

Hard rules remove candidates that must not be used: entitlements, tenant boundaries, jurisdiction,
document type, date, etc. Push security filters into the search system where possible and enforce
again at service/tool boundaries.

## Reranking

A reranker sees the full query/candidate pair and applies a more expensive relevance function to a
small candidate set. It is not another vector lookup. Measure Recall@K/nDCG before and after the
reranker to prove lift. See `rag/reranker.py`.

## Post-retrieval

Deduplicate, diversify/compress, and assemble a bounded evidence context. See
`rag/post_retrieval.py`.

## Post-generation

Validate source IDs and—when possible—claim/evidence entailment. Citation existence is necessary
but does not prove the prose is supported. See `rag/grounding.py`.
