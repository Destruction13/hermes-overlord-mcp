# Как пользоваться Hermes / Overlord

Дата проверки: 2026-05-24.

## Короткий вердикт

Overlord уже похож на суперагента: есть gateway, Kanban-диспетчер, профиль-директор, роли-специалисты, MCP-инструменты, review/synthesis-гейты и локальный vault. Лимиты подняты до `agent.max_turns: 500` и `delegation.max_iterations: 500`; Kanban `failure_limit` поднят до `5`. Это сильно снижает шанс преждевременной остановки, но не делает систему бесконечной: hard-cap нужен против runaway loops, зависших tool циклов и расходов.

## Основной запуск

Если задача приходит из Codex через `/hermes`, запускай только canonical bridge:

```powershell
.\bridge.ps1 submit "Сделай X" -Workspace "dir:C:\AI" -Human
```

Codex не должен создавать swarm/граф сам. Bridge создает один root handoff, а
Overlord уже внутри Hermes решает, нужны ли council, специалисты, reviewer,
watchdog и synth.

## Ручной запуск Overlord

Для сложной задачи, которую нужно довести до результата через декомпозицию:

```powershell
.\overlord-intake.ps1 "Сделай X" -Workspace "dir:C:\AI\SomeProject"
```

После запуска смотри прогресс:

```powershell
.\overlord-dashboard.ps1 -Open
.\overlord.ps1 kanban --board overlord stats
.\overlord.ps1 kanban --board overlord diagnostics
```

## Быстрый совет без полноценного исполнения

```powershell
.\overlord-swarm.ps1 "Оцени архитектуру/риски/подход для X"
```

Это полезно для стратегического решения, но не заменяет выполнение.
Не используй `overlord-swarm.ps1` как fallback для Codex `/hermes`.

## Прямой чат с Overlord

```powershell
.\overlord.ps1 chat
```

Используй, когда нужна ручная сессия, а не фоновая Kanban-задача.

## Nerood

```powershell
.\nerood-task.ps1 "Сделай X"
```

Nerood сейчас легче Overlord: gateway не запущен, MCP не настроены. Его стоит использовать для прямых bounded-задач с delegate_task, но не как полноценный фоновой суперагент.

## Ежедневный health-check

```powershell
.\overlord.ps1 doctor
.\overlord.ps1 gateway status
.\overlord.ps1 kanban --board overlord diagnostics
.\overlord.ps1 mcp list
.\overlord-dashboard.ps1 -Open
```

## Что настроить в первую очередь

1. Разобрать заблокированную задачу `t_a09c7651`: split/retry/reassign/unblock, иначе финальный synth по тому графу не завершится.
2. Решить политику rescue: можно ли Overlord автоматически дробить и переотправлять задачи при iteration budget exhausted.
3. Telegram уже подключен к Overlord gateway; для проверки отправь боту сообщение из allowlist-пользователя и смотри `gateway.log`.
4. Storybook MCP включать только в проектах, где Storybook реально отдает `/mcp` на `127.0.0.1:6006`.

## Telegram

Telegram gateway уже настроен для Overlord, токен хранится в профильном `.env`, allowlist задан. Gateway работает в polling mode.

Для ротации токена или смены allowlist используй:

```powershell
.\telegram-connect.ps1 "<bot-token>" -AllowedUsers "<your-user-id>" -RestartGateway
```

Если хочешь отправлять уведомления в конкретный чат по умолчанию:

```powershell
.\telegram-connect.ps1 "<bot-token>" -AllowedUsers "<your-user-id>" -HomeChannel "<chat-id>" -RestartGateway
```

## Storybook

Сначала в целевом проекте должен быть поднят Storybook MCP endpoint. Потом:

```powershell
.\storybook-enable.ps1 -Endpoint "http://127.0.0.1:6006/mcp" -Enable
```

## Evidence

- `C:\AI\Hermes\README.md`
- `C:\AI\Hermes\overlord-intake.ps1`
- `C:\AI\Hermes\overlord-swarm.ps1`
- `C:\AI\Hermes\nerood-task.ps1`
- `C:\AI\Hermes\telegram-connect.ps1`
- `C:\AI\Hermes\storybook-enable.ps1`
- `C:\AI\Hermes\docs\codebase\*.md`
- Terminal checks: `status`, `doctor`, `gateway status`, `kanban diagnostics`, MCP tests.
