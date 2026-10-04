from enterprise_ai_patterns.agents.governed_tool_call import (
    ToolRequest, ToolResult, governed_execute
)

class Policy:
    def authorize(self, request): return request.tool_name == "customer_query"

class Approval:
    def required(self, request): return False
    def approved(self, request): return True

class Executor:
    def execute(self, request, *, idempotency_key):
        return ToolResult(True, {"rows": [{"state": "FL"}]}, "op-42")
    def verify(self, result): return result.data["rows"][0]["state"] == "FL"

class Audit:
    def __init__(self): self.events = []
    def append(self, event): self.events.append(event)

def test_authorized_read_is_verified_and_audited():
    audit = Audit()
    result = governed_execute(
        ToolRequest("u1", "customer_query", {"state": "FL"}, "trace-42"),
        policy=Policy(),
        approvals=Approval(),
        executor=Executor(),
        audit=audit,
    )
    assert result.data["rows"][0]["state"] == "FL"
    assert audit.events[-1]["event"] == "tool_completed"
