"""Result type for a deterministic gate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    BLOCK = "block"
    WARN = "warn"


@dataclass(frozen=True)
class GateResult:
    """One gate outcome.

    ``passed`` means the check found nothing to report. A failed check with
    severity ``block`` stops publication. A failed check with severity ``warn``
    is recorded and publication continues.
    """

    gate: str
    severity: Severity
    passed: bool
    message: str

    @property
    def blocking(self) -> bool:
        return self.severity is Severity.BLOCK and not self.passed

    @property
    def state(self) -> str:
        if self.passed:
            return "pass"
        return self.severity.value

    def to_dict(self) -> dict[str, str]:
        return {
            "gate": self.gate,
            "severity": self.severity.value,
            "state": self.state,
            "message": self.message,
        }
