"""Task memory/state persistence abstraction."""

class MemoryStore:
    def __init__(self):
        self._memory = {}

    def set(self, key, value):
        self._memory[key] = value

    def get(self, key, default=None):
        return self._memory.get(key, default)
