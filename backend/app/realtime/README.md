# Realtime Contracts

Источник контрактов: `contracts.py`.

## Подключение

- URL: `ws://<host>/api/v1/ws` (dev через nginx: `ws://localhost/api/v1/ws`)
- Auth: `Authorization: Bearer <token>`

## Команды клиента

- `ping`
- `subscribe`
- `unsubscribe`
- `ack`

## События сервера

Служебные:

- `connected`
- `pong`

События по задачам:

- `task_created`
- `task_updated`
- `task_status_changed`
- `task_deleted`
- `task_restored`
- `task_comment_added`

Формат envelope:

```json
{
  "event_id": "evt_1",
  "event": "task_created",
  "payload": {},
  "requires_ack": true
}
```

## Payload-модели

Типизированные payload-модели в `contracts.py`:

- `TaskCreatedPayload`
- `TaskUpdatedPayload`
- `TaskStatusChangedPayload`
- `TaskDeletedPayload`
- `TaskRestoredPayload`
- `TaskCommentAddedPayload`

## На будущее

- Хорошо проявила бы себя центрифуга, и логику ретраев, таймаутов на стороне бекэнда я бы не делал. И в целом более прикольно бы сокеты раскидал