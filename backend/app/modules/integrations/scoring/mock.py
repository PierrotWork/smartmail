"""Заглушка скоринга — простые эвристики.

Используется, пока настоящий алгоритм не готов.
Правила:
  - базовый скор = 50
  - +10 если есть company
  - +15 если категория в 'vip', 'enterprise', 'partner'
  - +5 за каждый тег из белого списка (максимум +20)
  - -30 если is_unsubscribed
  - -20 если email давно не активен (attributes.last_activity_days > 90)
"""

from datetime import datetime, timezone
from typing import Any

from app.modules.integrations.scoring.base import ScoreResult


class MockScoringAdapter:
    version = "mock-0.1"

    HIGH_VALUE_CATEGORIES = {"vip", "enterprise", "partner"}
    HIGH_VALUE_TAGS = {"paying", "engaged", "recent-purchase", "webinar-attendee"}

    def score(self, clients: list[dict[str, Any]]) -> list[ScoreResult]:
        results: list[ScoreResult] = []
        for c in clients:
            score = 50.0
            factors: dict[str, Any] = {}

            if c.get("company"):
                score += 10
                factors["has_company"] = +10

            category = (c.get("category") or "").lower()
            if category in self.HIGH_VALUE_CATEGORIES:
                score += 15
                factors["high_value_category"] = +15

            tags = set(c.get("tags", []))
            tag_bonus = min(len(tags & self.HIGH_VALUE_TAGS) * 5, 20)
            if tag_bonus:
                score += tag_bonus
                factors["valuable_tags"] = tag_bonus

            if c.get("is_unsubscribed"):
                score -= 30
                factors["unsubscribed"] = -30

            last_activity = c.get("attributes", {}).get("last_activity_days")
            if isinstance(last_activity, (int, float)) and last_activity > 90:
                score -= 20
                factors["stale"] = -20

            score = max(0.0, min(100.0, score))

            results.append(
                ScoreResult(
                    client_id=c["id"],
                    score=score,
                    factors=factors,
                    algorithm_version=self.version,
                )
            )
        return results


def get_scoring_adapter() -> MockScoringAdapter:
    from app.config import settings

    if settings.scoring_provider == "http":
        # TODO: реализовать HTTPScoringAdapter, когда алгоритм готов
        pass
    return MockScoringAdapter()
