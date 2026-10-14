"""Idempotency result-store facade. Not an exactly-once execution guarantee."""
from enterprise_ai_patterns.agents.loop import InMemoryIdempotencyStore

class ResultStoreAdapter:
    def __init__(self, backing=None):
        self.backing = backing or InMemoryIdempotencyStore()

    def get(self, key):
        return self.backing.get(key)

    def put(self, key, result):
        self.backing.put(key, result)
