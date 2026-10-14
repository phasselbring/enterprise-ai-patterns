"""Wrap a supplied LangChain/LangGraph runnable; no hidden network calls."""
from time import perf_counter
from .contracts import HarnessRequest, HarnessResult

class LangChainHarnessAdapter:
    def __init__(self, runnable, *, provider="configured", tool_names=()):
        self.runnable = runnable
        self.provider = provider
        self.tool_names = frozenset(tool_names)

    async def run(self, request: HarnessRequest) -> HarnessResult:
        start = perf_counter()
        if not set(request.allowed_tools).issubset(self.tool_names):
            return HarnessResult("langchain", self.provider, "denied", error="unregistered allowed tool")
        try:
            result = await self.runnable.ainvoke({"messages": [{"role": "user", "content": request.prompt}]},
                    config={"configurable": {"thread_id": request.session_id}})
            messages = result.get("messages", [])
            response = str(getattr(messages[-1], "content", "")) if messages else ""
            return HarnessResult("langchain", self.provider, "completed", response,
                                 elapsed_ms=(perf_counter()-start)*1000)
        except Exception as exc:
            return HarnessResult("langchain", self.provider, "error", error=type(exc).__name__,
                                 elapsed_ms=(perf_counter()-start)*1000)
