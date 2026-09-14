"""Заполнить БД тестовыми данными для локальной разработки.

Использование:
    python scripts/seed_dev_data.py

Создаёт:
  - 50 фейковых клиентов с разными атрибутами
  - 3 email-шаблона
  - Пересчитывает скоры (через mock-адаптер)

Идемпотентно: если данные уже есть — пропустит создание.
"""

import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Позволяет запускать скрипт напрямую из папки scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.modules.clients.models import Client, ClientStatus, ScoreHistory  # noqa: E402
from app.modules.integrations.scoring.mock import get_scoring_adapter  # noqa: E402
from app.modules.templates.models import EmailTemplate  # noqa: E402

# ---------- Тестовые данные ----------

FIRST_NAMES = [
    "Александр",
    "Мария",
    "Иван",
    "Ольга",
    "Дмитрий",
    "Екатерина",
    "Сергей",
    "Анна",
    "Николай",
    "Наталья",
    "Павел",
    "Юлия",
    "Артём",
    "Дарья",
    "Максим",
]
LAST_NAMES = [
    "Иванов",
    "Петров",
    "Смирнов",
    "Соколов",
    "Морозов",
    "Волков",
    "Лебедев",
    "Ковалёв",
    "Новиков",
    "Кузнецов",
    "Попов",
    "Васильев",
    "Фёдоров",
]
COMPANIES = [
    "Альфа Лаб",
    "Бета Групп",
    "Гамма Инвест",
    "Дельта Софт",
    "Эпсилон Медиа",
    "Зета Ритейл",
    "Йота Финанс",
    None,
    None,  # часть клиентов без компаний
]
CATEGORIES = ["vip", "enterprise", "partner", "retail", "basic", None]
ALL_TAGS = [
    "paying",
    "engaged",
    "recent-purchase",
    "webinar-attendee",
    "newsletter-sub",
    "trial",
    "churned",
    "high-value",
]


def random_tags() -> list[str]:
    return random.sample(ALL_TAGS, k=random.randint(0, 3))


def random_client(i: int) -> dict:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    slug = f"{first.lower()}.{last.lower()}"
    return {
        "external_id": f"seed-{i:04d}",
        "email": f"{slug}{i}@example.com",
        "first_name": first,
        "last_name": last,
        "company": random.choice(COMPANIES),
        "category": random.choice(CATEGORIES),
        "tags": random_tags(),
        "attributes": {
            "country": random.choice(["RU", "BY", "KZ", "UA"]),
            "last_activity_days": random.randint(0, 180),
            "lifetime_value": random.randint(0, 50_000),
        },
        "status": ClientStatus.ACTIVE,
        "is_unsubscribed": random.random() < 0.05,
    }


# ---------- Шаблоны ----------

TEMPLATES = [
    {
        "name": "Промо: новый продукт",
        "subject": "{{ first_name }}, встречайте наш новый продукт 🎉",
        "html_body": """<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h1>Привет, {{ first_name }}!</h1>
<p>У нас отличные новости — мы запустили новый продукт, который решает те задачи, о которых ты нам рассказывал.</p>
<p>Для клиентов из категории {{ category }} действует особая цена в первые две недели.</p>
<a href="https://example.com/product?utm_source=smartmail" style="display:inline-block;padding:12px 24px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:6px;">Посмотреть</a>
<p style="color:#666;font-size:12px;margin-top:40px;">Компания: {{ company }}</p>
</body></html>""",
        "text_body": (
            "Привет, {{ first_name }}!\n\n"
            "Мы запустили новый продукт. Для категории {{ category }} — особая цена.\n\n"
            "Посмотреть: https://example.com/product?utm_source=smartmail\n"
        ),
        "variables": ["first_name", "category", "company"],
    },
    {
        "name": "Дайджест: за неделю",
        "subject": "Дайджест недели для {{ company }}",
        "html_body": """<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2>Здравствуйте, {{ first_name }}!</h2>
<p>Собрали для вас самое интересное за неделю:</p>
<ul>
  <li>Новая функция в вашей категории — {{ category }}</li>
  <li>Кейс от коллег: как выйти на +30% выручки</li>
  <li>Открыта запись на вебинар в четверг</li>
</ul>
<p>Хорошей недели!</p>
</body></html>""",
        "text_body": (
            "Здравствуйте, {{ first_name }}!\n\n"
            "Дайджест недели:\n"
            "- Новая функция для категории {{ category }}\n"
            "- Кейс: +30% выручки\n"
            "- Вебинар в четверг\n"
        ),
        "variables": ["first_name", "category", "company"],
    },
    {
        "name": "Реактивация: давно не виделись",
        "subject": "{{ first_name }}, скучаем — вернитесь на особых условиях",
        "html_body": """<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2>{{ first_name }}, привет!</h2>
<p>Мы заметили, что давно вас не видели. Возвращайтесь — и получите промокод на скидку 30%.</p>
<p style="font-size:24px;text-align:center;padding:20px;background:#f4f4f5;border-radius:8px;">
  <code>WELCOME30</code>
</p>
<p>Промокод действует 14 дней.</p>
</body></html>""",
        "text_body": (
            "{{ first_name }}, давно не виделись!\n\n"
            "Промокод на 30% скидку: WELCOME30 (действует 14 дней).\n"
        ),
        "variables": ["first_name"],
    },
]


# ---------- Main ----------


def main() -> int:
    random.seed(42)  # чтобы данные были воспроизводимыми
    now = datetime.now(UTC)

    with SessionLocal() as db:
        # Клиенты
        existing_clients = db.scalar(select(Client).limit(1))
        if existing_clients is not None:
            print("В БД уже есть клиенты — пропускаю seed клиентов.")
        else:
            print("Создаю 50 тестовых клиентов…")
            for i in range(1, 51):
                data = random_client(i)
                client = Client(
                    external_id=data["external_id"],
                    email=data["email"],
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    company=data["company"],
                    category=data["category"],
                    tags=data["tags"],
                    attributes=data["attributes"],
                    status=data["status"],
                    is_unsubscribed=data["is_unsubscribed"],
                    synced_at=now - timedelta(minutes=random.randint(0, 60)),
                )
                db.add(client)
            db.commit()
            print("  ✔ 50 клиентов создано")

        # Шаблоны
        existing_templates = db.scalar(select(EmailTemplate).limit(1))
        if existing_templates is not None:
            print("В БД уже есть шаблоны — пропускаю seed шаблонов.")
        else:
            print("Создаю 3 email-шаблона…")
            for t in TEMPLATES:
                db.add(
                    EmailTemplate(
                        name=t["name"],
                        subject=t["subject"],
                        html_body=t["html_body"],
                        text_body=t["text_body"],
                        variables=t["variables"],
                    )
                )
            db.commit()
            print("  ✔ 3 шаблона создано")

        # Скоринг
        print("Пересчитываю скоры через mock-адаптер…")
        adapter = get_scoring_adapter()
        all_clients = list(db.scalars(select(Client)).all())
        payload = [
            {
                "id": c.id,
                "email": c.email,
                "company": c.company,
                "category": c.category,
                "tags": c.tags,
                "attributes": c.attributes,
                "is_unsubscribed": c.is_unsubscribed,
            }
            for c in all_clients
        ]
        results = adapter.score(payload)
        by_id = {c.id: c for c in all_clients}
        for res in results:
            client = by_id[res.client_id]
            client.current_score = res.score
            db.add(
                ScoreHistory(
                    client_id=client.id,
                    score=res.score,
                    factors=res.factors,
                    algorithm_version=res.algorithm_version,
                )
            )
        db.commit()
        print(f"  ✔ скоры пересчитаны для {len(results)} клиентов")

    print("\n✅ Seed завершён. Открывай http://localhost:5173 и логинься.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
