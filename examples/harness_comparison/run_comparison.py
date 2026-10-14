"""Offline harness-contract demonstration; no LLM/API keys are required."""
import asyncio
import json
from pathlib import Path
from enterprise_ai_patterns.harnesses.contracts import HarnessResult
from enterprise_ai_patterns.validation.runner import run_scenario
from enterprise_ai_patterns.validation.scenario import Scenario

class OfflineHarness:
    async def run(self, request):
        return HarnessResult("offline_reference", "none", "completed",
                             "SO-1001 shortage is 22 units with 12-day replenishment estimate.")

async def main():
    payload = json.loads((Path(__file__).parent / "scenarios/order_shortage.json").read_text())
    result, checks, card = await run_scenario(OfflineHarness(), Scenario(**payload))
    print(json.dumps({"harness": result.harness, "checks": checks, "accepted": card.accepted}, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
