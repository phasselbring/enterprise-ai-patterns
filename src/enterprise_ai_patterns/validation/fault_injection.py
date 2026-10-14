"""Deterministic failure injector for offline harness tests."""
class InjectedToolFailure(RuntimeError):
    pass

class FailingTool:
    def __init__(self, message="simulated backend failure"):
        self.message = message
        self.calls = 0

    async def __call__(self, arguments):
        self.calls += 1
        raise InjectedToolFailure(self.message)
