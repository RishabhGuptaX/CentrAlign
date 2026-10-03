"""Base abstraction for agent tools."""

from abc import ABC, abstractmethod

class Tool(ABC):
    name = "base_tool"

    @abstractmethod
    def execute(self, **kwargs):
        raise NotImplementedError
