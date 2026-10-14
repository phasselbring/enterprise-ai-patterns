"""Adapter for the existing custom AgentLoop; caller binding remains on AgentLoop."""
from time import perf_counter
from .contracts import HarnessRequest, HarnessResult

class CustomAgentLoopAdapter:
    def __init__(self, agent_loop, *, provider="custom"):
        self.loop = agent_loop
        self.provider = provider

    async def run(self, request: HarnessRequest) -> HarnessResult:
        start = perf_counter()
        try:
            response = await self.loop.run(session_id=request.session_id, caller_id=request.caller_id, goal=request.prompt)
            return HarnessResult("custom_agent_loop", self.provider, "completed", response,
                                 elapsed_ms=(perf_counter()-start)*1000)
        except Exception as exc:
            return HarnessResult("custom_agent_loop", self.provider, "error", error=type(exc).__name__,
                                 elapsed_ms=(perf_counter()-start)*1000)
