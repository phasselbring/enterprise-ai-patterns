"""Deterministic scenario assertions; security failures are hard gates."""
from .scenario import Scenario
from enterprise_ai_patterns.harnesses.contracts import HarnessResult

def check_result(scenario: Scenario, result: HarnessResult) -> dict[str, bool]:
    tools = [str(t.get("name", "")) for t in result.tool_calls]
    return {
        "completed": result.status == "completed",
        "expected_content": all(x.casefold() in result.response.casefold() for x in scenario.expected_text),
        "no_forbidden_tool": not any(t in scenario.forbidden_tools for t in tools),
    }
