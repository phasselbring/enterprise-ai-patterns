"""Run a scenario through any harness implementing AgentHarness."""
from uuid import uuid4
from .scenario import Scenario
from .assertions import check_result
from .scorecard import score
from enterprise_ai_patterns.harnesses.contracts import HarnessRequest

async def run_scenario(harness, scenario: Scenario):
    request = HarnessRequest(str(uuid4()), str(uuid4()), scenario.caller_id,
                             scenario.prompt, scenario.allowed_tools, metadata=scenario.metadata)
    result = await harness.run(request)
    checks = check_result(scenario, result)
    return result, checks, score(checks)
