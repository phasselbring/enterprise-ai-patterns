"""Optional OpenAI Agents SDK adapter; inject runner and agent to keep tests offline.

This adapter does NOT itself enforce allowed_tools. Supply an agent with tools
restricted by the governance gateway and server-side authorization.
"""
from time import perf_counter
from .contracts import HarnessRequest, HarnessResult

class OpenAIAgentsAdapter:
    def __init__(self, agent, runner, *, provider="openai"):
        self.agent, self.runner, self.provider = agent, runner, provider

    async def run(self, request: HarnessRequest) -> HarnessResult:
        start = perf_counter()
        try:
            output = await self.runner.run(self.agent, request.prompt, max_turns=request.max_steps)
            return HarnessResult("openai_agents", self.provider, "completed", str(output.final_output),
                                 elapsed_ms=(perf_counter()-start)*1000)
        except Exception as exc:
            return HarnessResult("openai_agents", self.provider, "error", error=type(exc).__name__,
                                 elapsed_ms=(perf_counter()-start)*1000)
