# gRPC Contracts

Источник контракта: `task_service.proto`.

## Сервисы

- `task.v1.SystemService/Health`
- `task.v1.ProjectService/ListProjects`
- `task.v1.TaskService/ListTasks`
- `task.v1.TaskService/CreateTask`

## Авторизация

Для защищенных методов используется metadata:

- `authorization: Bearer <token>`

## Регенерация stubs

Команда выполняется из каталога `backend/`:

- `uv run python scripts/generate_grpc_stubs.py`

## Основные сообщения

- `Project`
- `Task`
- `ListTasksRequest`
- `ListTasksResponse`
- `CreateTaskRequest`

Полный контракт — `task_service.proto`.