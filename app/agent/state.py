"""Execution state models will live here."""

from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentState:
    task: str
    status: str = "created"
    plan: list = field(default_factory=list)
    observations: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
