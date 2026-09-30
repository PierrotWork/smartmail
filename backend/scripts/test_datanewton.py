"""Диагностический скрипт для проверки DataNewton-адаптера.

Использование:
    docker compose exec backend python scripts/test_datanewton.py list
    docker compose exec backend python scripts/test_datanewton.py sync

Команды:
    list  — показать все сегменты твоего аккаунта DataNewton
    sync  — запустить полную синхронизацию и записать клиентов в нашу БД
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.modules.clients import service as clients_service  # noqa: E402
from app.modules.integrations.crm.datanewton import DataNewtonAdapter  # noqa: E402


async def cmd_list() -> None:
    async with DataNewtonAdapter() as dn:
        segments = await dn.list_segments()

    if not segments:
        print("Сегментов нет. Создай их через веб-интерфейс DataNewton или API.")
        return

    print(f"Всего сегментов: {len(segments)}\n")
    header = f"{'ID':<8} {'Reserved':<10} {'Count':<10} {'Type':<15} Имя"
    print(header)
    print("-" * len(header))
    for s in segments:
        print(
            f"{s['id']:<8} "
            f"{str(bool(s.get('reserved'))):<10} "
            f"{str(s.get('count') or 0):<10} "
            f"{str(s.get('segment_type') or '-'):<15} "
            f"{s.get('name')}"
        )
    print("\nПодсказка: чтобы синкать только выбранные — впиши их ID в .env как")
    print("           DATANEWTON_SEGMENT_IDS=123,456,789")


async def cmd_sync() -> None:
    total_batches = 0
    total_created = 0
    total_updated = 0

    async with DataNewtonAdapter() as dn:
        async for batch in dn.fetch_clients():
            total_batches += 1
            with SessionLocal() as db:
                created, updated = clients_service.upsert_from_external(db, batch)
            total_created += created
            total_updated += updated
            print(
                f"Батч {total_batches}: получено {len(batch)}, "
                f"создано {created}, обновлено {updated}"
            )

    print()
    print(f"Итого: батчей {total_batches}, создано {total_created}, "
          f"обновлено {total_updated}")

    # Запускаем скоринг новых клиентов
    print("\nЗапускаю пересчёт скоров...")
    from app.workers.score_tasks import rescore_all_clients

    result = rescore_all_clients()
    print(f"Готово: {result}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    cmd = sys.argv[1]
    if cmd == "list":
        asyncio.run(cmd_list())
    elif cmd == "sync":
        asyncio.run(cmd_sync())
    else:
        print(f"Неизвестная команда: {cmd}")
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
