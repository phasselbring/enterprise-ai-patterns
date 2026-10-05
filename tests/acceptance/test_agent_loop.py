import asyncio

from enterprise_ai_patterns.agents.loop import AgentDecision, AgentLoop, DecisionKind
from enterprise_ai_patterns.agents.state import InMemoryStateStore
from enterprise_ai_patterns.agents.tool_registry import LocalToolProvider, ToolDefinition, ToolRegistry


class Model:
    async def decide(self, turn):
        used_tool = any(event.kind == "tool_result" for event in turn.prior_events)
        if not used_tool:
            return AgentDecision(DecisionKind.TOOL, "lookup_clause", {"type": "termination"})
        return AgentDecision(DecisionKind.FINAL, answer="Termination requires 30 days notice.")


class ContextLoader:
    async def load(self, *, caller_id, goal):
        return {"domain": "legal", "caller_id": caller_id}


class Policy:
    def authorize(self, request): return request.tool_name == "lookup_clause"


class Approvals:
    def required(self, request): return False
    def approved(self, request): return True


class Verifier:
    async def verify(self, result): return result.ok and "text" in result.data


class Audit(list): pass


def test_agent_control_loop_boots_uses_tool_updates_state_then_finishes():
    async def run():
        provider = LocalToolProvider()
        async def lookup(args): return {"text": "Either party may terminate with 30 days notice."}
        provider.register(
            ToolDefinition("lookup_clause", "Look up a clause", {"type": "object"}),
            lookup,
        )
        store = InMemoryStateStore()
        loop = AgentLoop(
            model=Model(),
            context_loader=ContextLoader(),
            tool_registry=ToolRegistry([provider]),
            state_store=store,
            policy=Policy(),
            approvals=Approvals(),
            verifier=Verifier(),
            audit=Audit(),
            max_steps=4,
        )
        answer = await loop.run(session_id="s1", caller_id="u1", goal="review termination")
        state = store.load("s1")
        assert answer.startswith("Termination")
        assert state is not None and state.completed
        assert [e.kind for e in state.events] == ["tool_result", "final"]
    asyncio.run(run())
