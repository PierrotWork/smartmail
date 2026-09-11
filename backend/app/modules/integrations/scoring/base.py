"""Интерфейс алгоритма скоринга клиентов."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class ScoreResult:
    client_id: int
    score: float           # 0..100
    factors: dict[str, Any]  # объяснение (какие признаки повлияли)
    algorithm_version: str


@runtime_checkable
class ScoringAdapter(Protocol):
    """
    Реализация алгоритма скоринга.

    На входе — список нормализованных клиентов; на выходе — список
    оценок. Порядок ответа не гарантируется — сопоставление через client_id.
    """

    version: str

    def score(self, clients: list[dict[str, Any]]) -> list[ScoreResult]:
        ...
