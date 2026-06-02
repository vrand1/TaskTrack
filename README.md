# Task Service

Сервис трекинга задач: REST API для фронта, gRPC для межсервисных вызовов и WebSocket для realtime-событий.

## Быстрый старт

1. Скопируйте `compose/.env.example` в `compose/.env`.
2. Запустите dev-окружение:
   - `docker compose -f compose/docker-compose.dev.yml up -d --build`
3. Проверьте сервис:
   - `http://localhost/api/v1/health`
   - `http://localhost/api/docs`

## Полезные команды (без make)

- Старт: `docker compose -f compose/docker-compose.dev.yml up -d --build`
- Логи API: `docker compose -f compose/docker-compose.dev.yml logs -f api`
- Тесты: `docker compose -f compose/docker-compose.dev.yml exec api pytest -q /app/tests`
- Линтер: `docker compose -f compose/docker-compose.dev.yml exec api ruff check .`
- Остановка: `docker compose -f compose/docker-compose.dev.yml down`

## Полезные команды (make)

- Старт dev-окружения: `make dev-up`
- Логи API: `make dev-logs`
- Миграции: `make migrate`
- Тесты: `make test`
- Линтер: `make lint`
- Остановка dev-окружения: `make dev-down`

## Запуск prod

- Через `make`:
  - `make up`
  - `make logs`
  - `make down`
- Без `make`:
  - `docker compose -f compose/docker-compose.yml up -d --build`
  - `docker compose -f compose/docker-compose.yml logs -f api`
  - `docker compose -f compose/docker-compose.yml down`

## Адреса

- Swagger: `http://localhost/api/docs`
- gRPC: `localhost:50051`
- WebSocket: `ws://localhost/api/v1/ws`

## Авторизация (dev)

`POST /api/v1/auth/token`

```json
{
  "email": "admin@example.dev",
  "password": "password123"
}
```

## Основной REST (кратко)

- Проекты: создание, список, получение, обновление, удаление, восстановление.
- Задачи: создание, список, получение, обновление, смена статуса, переоткрытие (`reopen`), удаление, восстановление, история, комментарии.
- Пользователи: создание, синхронизация, смена/сброс пароля, выборки задач.

## Дополнительные фичи

- Проекты (`/api/v1/projects`): отдельная сущность для группировки задач и безопасного восстановления удаленных данных.
- Reopen задачи (`POST /api/v1/tasks/{id}/reopen`): один раз переводит из `done` в `todo` вне FSM; фиксируется флаг `was_reopened`, повторный reopen запрещён.
- Подзадачи: древовидная структура задач с проверками консистентности (без циклов, в рамках одного проекта).
- История изменений и комментарии: аудит действий по задаче (`/api/v1/tasks/{id}/history`, `/api/v1/tasks/{id}/comments`).
- Поиск, сортировка, пагинация, теги, приоритет, плановые даты старта/окончания: удобная работа с большими списками задач.
- Единый формат ошибок на русском: код ошибки + понятное сообщение для клиента.
- Идемпотентность POST (`Idempotency-Key`): защита от дублей при повторных запросах.
- Redis-кэш списка задач: ускорение `GET /tasks` при сохранении актуальности через инвалидацию.
  - `TTL=300` секунд (5 минут): снижает нагрузку на БД в тяжёлых для чтения сценариях.
  - Инвалидация при изменениях — основной механизм актуальности; TTL выступает страховкой.
  - Подробности: `backend/app/cache/README.md`.
- Soft-delete + restore + retention: удаление через `deleted_at` с возможностью восстановления.
  - Практический смысл: пользователь может удалить задачу случайно и вернуться к ней позже.
  - Почему `30` дней: это компромисс между безопасностью для пользователя и контролем роста БД.
  - После `30` дней запись удаляется фоновым purge-процессом, чтобы не копить архив бесконечно.
- gRPC: контракт и использование в `backend/proto/README.md`
- WebSocket / realtime: контракты и команды в `backend/app/realtime/README.md`
- Nginx gateway + rate limit на `POST /api/v1/auth/token`:
  - проксирование HTTP-трафика через Nginx;
  - ограничение частоты запросов для защиты от брутфорса;
  - конфиги: `compose/nginx.conf`, `compose/nginx.dev.conf`.

### Расширения модели (зачем команде)
- `project_id` — задачи не в вакууме, а в контексте продукта/спринта/идеи
- `priority`, `start_at`, `end_at`, tags — приоритизация, тайм-менеджмент и фильтры в списках
- `parent_task_id` — декомпозиция больших задач (Epic - SubEpic - Task и др.)
- `was_reopened` — видно, что задача уже проходила цикл до done, но возникли технические шоколадки 
- `deleted_at` — безопасное удаление с restore, вариант с полным удалением и мягким удалением не понравился, а мягкое удаление с последующим удалением после мариновки вполне 

## Архитектурные заметки по слоям
- Auth и Users нарушают DDD, не ответственность модуля думать об авторизации и юзерах. Только через nginx прокинуть в проксю запросик, распарсить JWT и дать права вошедшему. А про юзеров узнавать из сервиса пользователей. Без хранения на своей стороне
> Авторизация процесс сложный, 100% есть корпоративный LDAP или своя SSO, и чтобы была возможность не костыльно сделать этот модуль частью ИС был сделан порт и конкретные контракты для внутреннего, самодостаточного решения и возможность описать контракт самостоятельно(что придётся сделать рано или поздно, ресурс на поддержание консистентности данных не вечный), без ломания всего кода. С переключением в одну переменную env
- Auth и порты/шины: `backend/app/domains/auth/README.MD`
> Такая же история, что с авторизацией, гарантированно есть свой домен юзеров, и даже возможно соединённый с 1С или подобным. И легче к нему подключиться нежели костылить ещё один источник истины. Вообще таблица излишняя в рамках микросервисной архитектуры, но для самодостаточности модуля без других необходима
- Users: `backend/app/domains/users/README.md`


- Projects: `backend/app/domains/projects/README.md`
- Tasks: `backend/app/domains/tasks/README.md`

> gRPC для межсервисного взаимодействия, только набросок с простымы командами, сделана возможность под расширение. REST конечно неплох, но со скоростью gRPC не сравнится.
- gRPC слой: `backend/app/grpc/README.md`
> Сокеты и контракты под ивенты для того, чтобы подключить фронт и получать изменения других пользователей в реальном времени. В таск трекере будто необходимо это. 
- Realtime (WebSocket): `backend/app/realtime/README.md`

- Кэш: `backend/app/cache/README.md`
> Логи всему голова, без них жизнь сложна и дебаг инцедента на проде (сбор проблематики или помощь юзеру) довольно страшная тема. 
- Логирование: `backend/app/logs/README.md`

## Закрытие минимума ТЗ

- Python `>=3.11`, FastAPI, Docker / docker compose:
  - `backend/pyproject.toml`
  - `backend/app/main.py`
  - `compose/docker-compose.yml`
  - `compose/docker-compose.dev.yml`
- JWT-авторизация (`POST /api/v1/auth/token` + Bearer-токен):
  - `backend/app/domains/auth/router.py`
  - `backend/app/domains/auth/service.py`
  - `backend/app/domains/auth/providers/local_jwt.py`
- PostgreSQL + Alembic миграции:
  - `backend/alembic.ini`
  - `backend/alembic/env.py`
  - `backend/alembic/versions/001_initial_schema.py`
- Валидация входных данных и единый формат ошибок:
  - `backend/app/shared/schemas/` (И другие схемы доменов)
  - `backend/app/core/exceptions.py`
  - `backend/app/main.py`
- Кэширование списка задач в Redis (TTL + инвалидация):
  - `backend/app/cache/task_list.py`
  - `backend/app/cache/redis_client.py`
  - `backend/app/domains/tasks/service.py`
- Тесты на создание задачи и смену статуса + дополнительные сценарии:
  - `backend/tests/test_tasks.py`
  - `backend/tests/test_status_fsm.py`
  - `backend/tests/`
- CI: линтер и тесты в GitHub Actions:
  - `.github/workflows/ci.yml`

## Миграции и тесты

- Схема: `backend/alembic/versions/001_initial_schema.py`
- Тесты: `backend/tests`

> Примечание: для прода аудит действий пользователей и большие объемы логов обычно лучше выносить в ClickHouse (или аналогичное аналитическое хранилище), или же на сервис, который подключён к подобному хранилищу. В рамках этого тестового задания оставлена более простая реализация через таблицу.
> Вебсокеты я бы гонял через центрифугу, а не как в текущей реализации, так гораздо удобнее было бы. Один раз настроить и потом подключать сервисы туда без лишних дум о поддержке подключения в определённом сервисе


