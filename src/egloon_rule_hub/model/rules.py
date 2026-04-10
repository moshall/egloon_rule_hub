from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rule:
    type: str
    value: str

    def render(self) -> str:
        return f"{self.type},{self.value}"

