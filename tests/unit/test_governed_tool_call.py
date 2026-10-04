import pytest
from enterprise_ai_patterns.agents.governed_tool_call import (
    ToolRequest, ToolResult, governed_execute
)

class Policy:
    def __init__(self, allowed=True): self.allowed = allowed
    def authorize(self, request): return self.allowed

class Approvals:
    def required(self, request): return False
    def approved(self, request): return True

class Executor:
    def __init__(self): self.called = False
    def execute(self, request, *, idempotency_key):
        self.called = True
        return ToolResult(True, {"rows": 1}, "op-1")
    def verify(self, result): return True

class Audit(list): pass

def req():
    return ToolRequest("u1", "customer_query", {"state": "FL"}, "t1")

def test_denied_tool_never_executes():
    ex = Executor()
    with pytest.raises(PermissionError):
        governed_execute(req(), policy=Policy(False), approvals=Approvals(), executor=ex, audit=Audit())
    assert ex.called is False
