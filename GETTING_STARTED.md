# Getting Started — SmartMail Campaigns

Пошаговая инструкция от «ничего» до «первая рассылка ушла».

---

## 📋 Что нужно перед началом

- ✅ Windows 10 Pro (у тебя есть) + права администратора
- ✅ Docker Desktop установлен и **запускается без ошибок**
  (см. раздел «Если Docker не запускается» ниже)
- ⚠️ **Trial-ключ DataNewton работает для отладки API**, но НЕ позволяет
  скачивать данные экспорта (получишь 403 «limit exceeded»).
  Для реальных выгрузок нужен тариф **«Filters API — Start»** (30 000 ₽/год).

---

## 🚀 Шаг 1. Настроить .env

```powershell
cd C:\Users\User\workVScode\smartmail
Copy-Item .env.example .env
```

Открой `.env` в редакторе и заполни:

```env
# Секретный ключ — сгенерируй любую длинную случайную строку
APP_SECRET_KEY=<любые_32+_случайных_символов>

# CRM — работаем с DataNewton
CRM_PROVIDER=datanewton
DATANEWTON_API_KEY=<твой_ключ_из_личного_кабинета_datanewton>

# Список сегментов для синка — оставь пустым, приложение возьмёт все не-reserved
DATANEWTON_SEGMENT_IDS=

# Остальное менять не нужно — работает из коробки
```

💡 **Совет:** сгенерируй сильный `APP_SECRET_KEY` в PowerShell:
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | % {[char]$_})
```

---

## 🐳 Шаг 2. Поднять контейнеры

```powershell
docker compose up -d --build
```

Первый раз соберётся 3-5 минут (образы Python + Node + Postgres + Redis).

Проверь, что все контейнеры живые:
```powershell
docker compose ps
```

Должно быть 7 сервисов в статусе `running` или `healthy`:
`postgres`, `redis`, `mailhog`, `backend`, `worker`, `beat`, `frontend`.

---

## 🗄️ Шаг 3. Применить миграции БД

Первая миграция уже сгенерирована и лежит в `backend/alembic/versions/`.
Просто применяем к чистой базе:

```powershell
docker compose exec backend alembic upgrade head
```

*(Если позже поменяешь модели — сгенеришь новую миграцию через
`docker compose exec backend alembic revision --autogenerate -m "описание"`)*

---

## 👤 Шаг 4. Создать первого администратора

```powershell
docker compose exec backend python scripts/create_admin.py admin@example.com Admin12345 "Первый Админ"
```

---

## ✅ Шаг 5. Проверить, что API работает

Открой в браузере:

| URL | Что должно быть |
|---|---|
| http://localhost:8000/health | `{"status":"ok",...}` |
| http://localhost:8000/docs | Swagger UI со всеми эндпойнтами |
| http://localhost:5173 | Экран логина фронтенда |
| http://localhost:8025 | MailHog (пустой inbox — пока писем нет) |

Залогинься в http://localhost:5173 с созданными выше кредами.

---

## 🧪 Шаг 6. Быстрая проверка на fake-данных (без DataNewton)

Чтобы убедиться, что цикл рассылки работает end-to-end, засеем 50 фейковых клиентов + 3 шаблона:

```powershell
docker compose exec backend python scripts/seed_dev_data.py
```

Скрипт сам пересчитает скоры — вручную запускать `rescore_all_clients`
не нужно.

- Обнови **/clients** в браузере — 20 клиентов с цветными скор-бейджами
- В Swagger `POST /api/v1/campaigns` собери тестовую рассылку
- `POST /api/v1/campaigns/{id}/send` — отправить
- Открой http://localhost:8025 — там будут все отправленные письма

---

## 🌐 Шаг 7. Подключить настоящий DataNewton

### 7.1. Проверить, что ключ виден приложению и API отвечает

```powershell
docker compose exec backend python scripts/test_datanewton.py list
```

Ожидаемый вывод: таблица с твоими сегментами DataNewton.
У тебя сейчас будет 3 системных (`Отслеживаемые`, `Поставщики`, `Клиенты`)
+ **один тестовый `tmp-static-probe`, который я не смог доудалить —
удали его вручную через веб-интерфейс DataNewton.**

### 7.2. Наполнить сегмент клиентами в DataNewton

Вариант A — **вручную**: в веб-интерфейсе DataNewton найди раздел
«Сегменты», открой «Клиенты» (или любой свой) и добавь в него компании
через поиск/фильтры.

Вариант B — **через API** (для filter_based-сегментов):
```powershell
# Пример: создать сегмент "IT Москвы" с фильтром
$key = (Get-Content .env | Select-String "DATANEWTON_API_KEY").Line.Split('=')[1]
$body = @{
  name = "IT Москвы"
  tag_type = "filter_based"
  filter_config = @{
    region_codes = @("77")
    only_active = $true
    # добавь другие фильтры, когда узнаешь их точные имена из документации
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method POST -Uri "https://api.datanewton.ru/v1/segment?key=$key" `
  -Body $body -ContentType "application/json"
# Запиши возвращённый id — это твой сегмент
```

### 7.3. Оплатить тариф (если ещё не оплачен)

Trial НЕ даёт скачивать данные. Иди на https://datanewton.ru/prices,
покупай **«Filters API — Start»** (30 000 ₽/год, 50 000 компаний).
Ключ останется тот же, просто разблокируются данные.

### 7.4. Запустить первую живую синхронизацию

```powershell
docker compose exec backend python scripts/test_datanewton.py sync
```

Что произойдёт:
- Приложение возьмёт все не-reserved и непустые сегменты из твоего аккаунта
  (или только те, что ты перечислил в `DATANEWTON_SEGMENT_IDS`)
- Для каждого: запустит экспорт → подождёт материализации → скачает данные
  пачками → запишет клиентов в нашу БД
- Автоматически пересчитает скоры (пока mock, потом заменим на реальный алгоритм)

После этого обнови **/clients** во фронтенде — увидишь реальных клиентов
с реальными атрибутами.

---

## 📮 Шаг 8. Первая настоящая рассылка

1. Открой http://localhost:5173/campaigns → «Новая рассылка»
2. Собери сегмент (например, «скор ≥ 70»)
3. Выбери или создай шаблон (`/templates`)
4. Нажми «Отправить»
5. **На dev-окружении** письма ловит MailHog (http://localhost:8025).
   Чтобы отправлять по-настоящему, поменяй в `.env`:
   ```env
   ESP_PROVIDER=unisender      # или sendgrid, mailgun, smtp с реальным SMTP
   UNISENDER_API_KEY=<...>
   ```
   и перезапусти: `docker compose restart backend worker`

---

## 🔧 Полезные команды

```powershell
# Логи (в реальном времени)
docker compose logs -f backend
docker compose logs -f worker

# Перезапуск после правки .env
docker compose restart backend worker beat

# Открыть shell в контейнере
docker compose exec backend bash

# Открыть psql к БД
docker compose exec postgres psql -U smartmail -d smartmail

# Полностью пересобрать всё с нуля (удалит данные!)
docker compose down -v
docker compose up -d --build
```

---

## 🛠️ Если Docker не запускается

**Симптом:** «Docker Desktop stuck at Starting the Docker Engine…»

Порядок действий:
1. Проверь, что WSL установлен полноценно (не только заглушка):
   ```powershell
   wsl --status
   ```
   Если печатается справка — WSL не установлен. Открой PowerShell **от админа**:
   ```powershell
   wsl --install --no-distribution
   ```
   → **перезагрузка**.

2. После перезагрузки, если Docker всё равно висит:
   ```powershell
   wsl --shutdown
   wsl --unregister docker-desktop
   wsl --unregister docker-desktop-data
   ```
   и снова запусти Docker Desktop.

3. Если и это не помогло — **Settings → Troubleshoot → Reset to factory
   defaults** в Docker Desktop.

4. Проверь антивирус и VPN — иногда блокируют.

Подробнее — в чате выше или в `docs/ARCHITECTURE.md`.

---

## 🔐 Безопасность API-ключа DataNewton

**После завершения настройки:**
1. Зайди в личный кабинет DataNewton
2. Отзови текущий ключ (он мог засветиться в чате/логах)
3. Сгенерируй новый
4. Впиши только в `.env` (в git не уйдёт — `.gitignore` защищает)
5. `docker compose restart backend worker`

---

## 📌 Что уже работает / что не сделано

**✅ Работает:**
- Полный скелет приложения (backend + frontend + workers)
- Auth, роли, JWT
- CRUD клиентов, шаблонов, рассылок
- Асинхронная отправка через Celery
- MailHog для локальной проверки писем
- Mock-скоринг
- **Полноценный DataNewton-адаптер** (создание сегментов, экспорт, стриминг,
  корректная обработка session_id, устойчивый маппинг)

**🚧 Нужно доделать позже:**
- UI-мастер создания рассылки (сейчас через Swagger)
- WYSIWYG-редактор шаблонов (сейчас HTML-текстом через API)
- Реальный ESP-адаптер (Unisender / SendGrid) — сейчас только SMTP+MailHog
- Вебхуки от ESP для трекинга открытий/кликов
- Реальный алгоритм скоринга (сейчас mock)
- Обработчик отписок `/unsubscribe?token=...`
- Тесты
- CI/CD

Полный roadmap — в `docs/ARCHITECTURE.md`.

---

## 🎯 Порядок действий на завтра

1. Починить Docker (шаг «Если Docker не запускается»)
2. Пройти шаги 1-6 — убедиться, что приложение работает на fake-данных
3. Решить, оплачивать ли **«Filters API — Start»** сейчас или сначала
   допилить UI на mock-данных
4. Если оплачиваешь — сделать шаг 7 и первую реальную выгрузку
5. Скинуть мне JSON одной записи из `/export/batch` — я подкручу
   маппинг под реальную структуру
