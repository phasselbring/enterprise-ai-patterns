# Harness comparison

Run from the repository root after `python -m pip install -e .`:

```powershell
.\.venv\Scripts\python.exe .\examples\harness_comparison\run_comparison.py
```

The bundled runnable is **offline and deterministic**. It validates the framework-neutral contract and scorecard; it does not exercise a live model, MCP transport, or business-side authorization. The custom, LangChain and OpenAI Agents adapters are injection-ready reference adapters; connect them to governed tools before using them for enterprise workflows.
