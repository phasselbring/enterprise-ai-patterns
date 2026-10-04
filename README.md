# Enterprise AI Patterns

Implementation-oriented reference examples for enterprise AI architecture.

Focus areas: governed RAG, agent/tool governance, identity, evaluation, Text-to-SQL safety,
database access, AWS Lambda/RDS, architecture patterns, and AI-assisted SDLC controls.

The examples use synthetic data and contain no production APEX code, client data, credentials,
internal endpoints, or proprietary deployment details.

## Tests

- `tests/unit/` — isolated behavior tests
- `tests/acceptance/` — end-to-end behavior tests across multiple components

Run:

```bash
python -m pip install -e ".[dev]"
pytest
```
