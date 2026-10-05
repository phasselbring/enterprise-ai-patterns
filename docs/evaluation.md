# Evaluation harness

Evaluate components independently so a bad final answer can be attributed to retrieval, reranking,
generation, grounding, or policy.

A frozen golden case can contain:

- representative query + persona/domain metadata
- expected source/clause IDs
- forbidden source IDs
- expected classification
- whether the system should abstain

Useful retrieval metrics include Precision@K, Recall@K, reciprocal rank / MRR, and nDCG. For
high-consequence clause detection, also track per-clause recall and false-negative rate rather than
hiding rare failures inside one aggregate score.
