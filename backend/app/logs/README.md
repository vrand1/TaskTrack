# Logging

Источник реализации: `setup.py`, `middleware.py`, `handlers.py`.

## Инициализация

- Вызов `setup_logging()` выполняется при старте приложения в `app/main.py`.
- `LoggingMiddleware` добавляется как HTTP middleware.
- `setup_exception_handlers(app)` регистрирует единые обработчики ошибок.

## Поток обработки

1. `LoggingMiddleware` генерирует `request_id` (UUID) для каждого запроса.
2. `request_id` сохраняется в `request.state` и возвращается в заголовке `X-Request-ID`.
3. Логируется входящий запрос (`REQUEST`), затем исходящий ответ (`RESPONSE`).
4. При необработанном исключении middleware пишет `CRASH` и возвращает `500` с `request_id`.
5. `AppError`, `HTTPException` и `RequestValidationError` логируются в `handlers.py` с унифицированным payload.

## Политика логирования

- Пропуск логирования для служебных путей: `/health`, `/api/docs`, `/api/openapi.json`, `/api/redoc`.
- Для `/auth/token` тело запроса маскируется (`<redacted>`).
- Уровни response-логов:
  - `2xx` -> `success`
  - `4xx` -> `warning`
  - `5xx` -> `error`

## Конфигурация

Параметры в `app/core/config.py`:

- `log_level` - явный уровень логирования.
- `app_debug` - влияет на `effective_log_level` при пустом `log_level`.
- `log_to_files` - включает файловые sink.

Поведение `setup.py`:

- Console sink: `stdout`, формат `LOG_FORMAT`, фильтр по `extra.sink`.
- File sink (при `log_to_files=true`):
  - `logs/app.log` (`DEBUG+`, rotation `10 MB`, retention `7 days`, JSON serialize)
  - `logs/errors.log` (`ERROR+`, rotation `20 MB`, retention `90 days`, JSON serialize)

## Структура ошибок

- Бизнес-ошибки: `AppError` -> `error.code`, `error.message`, опционально `request_id`.
- HTTP-ошибки: `HTTP_<status_code>`.
- Ошибки валидации: `VALIDATION_ERROR` + массив `details`.
