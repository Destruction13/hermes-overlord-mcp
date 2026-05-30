from __future__ import annotations

import json
import os
import sqlite3
from datetime import date
from pathlib import Path

import yaml


HERMES_ROOT = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
PROFILES_ROOT = HERMES_ROOT / "profiles"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


ROLE_META = {
    "overlord": {
        "phase": "director",
        "title": "Executive Director",
        "responsibility": "Turns one user goal into spec, Kanban graph, specialist work, review, and final synthesis.",
        "owns": ["Goal classification", "Spec-first contract", "Kanban graph", "Final accountability"],
        "receivesFrom": ["CLI", "Telegram", "Gateway"],
        "handsTo": ["olproduct", "olarchitect", "olresearcher", "olrisk", "olux", "olfrontend", "olbackend", "olautomation", "olwatchdog", "olreviewer", "olsynth"],
    },
    "olproduct": {
        "phase": "council",
        "title": "Product Strategist",
        "responsibility": "Clarifies value, scope, non-goals, acceptance criteria, and reviewable product target.",
        "owns": ["User outcome", "Scope", "Acceptance criteria", "Non-goals"],
        "receivesFrom": ["overlord"],
        "handsTo": ["olarchitect", "olux", "olsynth"],
    },
    "olarchitect": {
        "phase": "council",
        "title": "Architecture Officer",
        "responsibility": "Designs modules, boundaries, contracts, dependencies, data flow, sequence, and risks.",
        "owns": ["System design", "Contracts", "Module boundaries", "Migration path"],
        "receivesFrom": ["overlord", "olproduct", "olresearcher"],
        "handsTo": ["olfrontend", "olbackend", "olautomation", "olreviewer"],
    },
    "olresearcher": {
        "phase": "council",
        "title": "Research Specialist",
        "responsibility": "Finds external evidence, docs, repos, examples, and source-grounded decision inputs.",
        "owns": ["External docs", "Repo examples", "Source ledger", "Evidence quality"],
        "receivesFrom": ["overlord"],
        "handsTo": ["olproduct", "olarchitect", "olreviewer", "olsynth"],
    },
    "olrisk": {
        "phase": "council",
        "title": "Risk Officer",
        "responsibility": "Checks security, privacy, destructive actions, reliability, cost, and compliance risk.",
        "owns": ["Risk register", "Approval gates", "Security posture", "Mitigations"],
        "receivesFrom": ["overlord", "olarchitect", "olautomation"],
        "handsTo": ["olautomation", "olreviewer", "overlord"],
    },
    "olux": {
        "phase": "council",
        "title": "UX Officer",
        "responsibility": "Turns flows, screenshots, dashboards, copy, and taste into executable UX criteria.",
        "owns": ["Experience quality", "Accessibility", "Interface acceptance criteria", "Design handoff"],
        "receivesFrom": ["overlord", "olproduct"],
        "handsTo": ["olfrontend", "olreviewer", "olsynth"],
    },
    "olfrontend": {
        "phase": "execution",
        "title": "Frontend Implementer",
        "responsibility": "Builds production-grade UI and verifies render, interaction, responsiveness, and browser behavior.",
        "owns": ["Frontend code", "Browser verification", "UI state", "Visual polish"],
        "receivesFrom": ["overlord", "olarchitect", "olux"],
        "handsTo": ["olreviewer", "olsynth"],
    },
    "olbackend": {
        "phase": "execution",
        "title": "Backend Implementer",
        "responsibility": "Builds APIs, services, jobs, schemas, migrations, auth flows, tests, and observability.",
        "owns": ["APIs", "Services", "Database", "Backend tests"],
        "receivesFrom": ["overlord", "olarchitect"],
        "handsTo": ["olreviewer", "olsynth"],
    },
    "olautomation": {
        "phase": "execution",
        "title": "Automation Officer",
        "responsibility": "Builds scripts, Docker/CI/CD plumbing, browser automations, local daemons, runbooks, and MCP wiring.",
        "owns": ["Scripts", "CI/CD", "Docker", "MCP plumbing", "Runbooks"],
        "receivesFrom": ["overlord", "olarchitect", "olrisk"],
        "handsTo": ["olreviewer", "olwatchdog", "olsynth"],
    },
    "olwatchdog": {
        "phase": "control",
        "title": "Progress Watchdog",
        "responsibility": "Detects stalls, blockers, dependency drift, goal drift, and when to wait/intervene/split/reassign.",
        "owns": ["Heartbeat", "Stale-task detection", "Blocker evidence", "Reassignment signal"],
        "receivesFrom": ["overlord", "Kanban"],
        "handsTo": ["overlord", "olreviewer"],
    },
    "olreviewer": {
        "phase": "control",
        "title": "Review Gate",
        "responsibility": "Checks whether work is actually done and returns pass, pass_with_conditions, needs_input, or block.",
        "owns": ["Acceptance review", "Regression risk", "Evidence mapping", "Security scan posture"],
        "receivesFrom": ["olfrontend", "olbackend", "olautomation", "olrisk", "olwatchdog"],
        "handsTo": ["overlord", "olsynth"],
    },
    "olsynth": {
        "phase": "output",
        "title": "Final Synthesizer",
        "responsibility": "Turns scattered worker evidence into final answer, decision record, vault note, or handoff.",
        "owns": ["Final synthesis", "Decision records", "Durable notes", "User-ready summary"],
        "receivesFrom": ["overlord", "olreviewer", "olfrontend", "olbackend", "olautomation", "olresearcher", "olux", "olproduct", "olarchitect", "olrisk"],
        "handsTo": ["User", "Vault", "Memory"],
    },
    "nerood": {
        "phase": "auxiliary",
        "title": "Lightweight Orchestrator",
        "responsibility": "Practical bounded coding orchestration outside the full Overlord council graph.",
        "owns": ["Small hierarchy", "Direct delegated work", "Bounded verification"],
        "receivesFrom": ["Codex", "User"],
        "handsTo": ["Worker children", "User"],
    },
    "diana": {
        "phase": "auxiliary",
        "title": "General Hermes Profile",
        "responsibility": "Общий Hermes-профиль без проектных MCP: простой помощник для легких задач и разговора.",
        "owns": ["General chat", "Light assistance"],
        "receivesFrom": ["User"],
        "handsTo": ["User"],
    },
}


RU_ROLE_META = {
    "overlord": {
        "summary": "Директор всей системы: принимает цель, превращает ее в понятную спецификацию, строит граф задач и отвечает за итоговый результат.",
        "does": "Классифицирует запрос, выбирает режим работы, заводит Kanban-граф, назначает специалистов и собирает финальное решение.",
        "responsible": "Фокус, критерии приемки, маршрутизация задач, контроль доказательств и финальная ответственность перед пользователем.",
        "communicates": "Получает вход из CLI, Telegram или gateway; отдает задачи council/workers; принимает verdict от reviewer/watchdog/synth.",
    },
    "olproduct": {
        "summary": "Продуктовый стратег: переводит размытое желание в ценность, границы, non-goals и измеримые критерии приемки.",
        "does": "Превращает желание пользователя в проверяемые критерии готовности.",
        "responsible": "Чтобы команда строила не просто что-то техническое, а именно полезный и проверяемый результат.",
        "communicates": "Передает scope архитектору, UX-офицеру и синтезатору.",
    },
    "olarchitect": {
        "summary": "Архитектор: превращает цель и критерии в системный план, границы модулей, контракты и последовательность работ.",
        "does": "Проектирует компоненты, зависимости, данные, интеграции, миграции и технические trade-off'ы.",
        "responsible": "Чтобы реализация была связной, расширяемой и не ломала соседние части системы.",
        "communicates": "Берет scope от Overlord/product/research и передает контракты frontend, backend, automation и reviewer.",
    },
    "olresearcher": {
        "summary": "Исследователь: находит внешние источники, документацию, примеры, репозитории и отделяет факты от шума.",
        "does": "Проверяет актуальные best practices, API, библиотеки, аналоги, ограничения и источники истины.",
        "responsible": "Чтобы решения опирались на проверяемые источники, а не на догадки.",
        "communicates": "Передает evidence ledger продукту, архитектору, reviewer и synth.",
    },
    "olrisk": {
        "summary": "Риск-офицер: заранее ищет, где план может навредить безопасности, приватности, надежности, бюджету или данным.",
        "does": "Проверяет опасные действия, секреты, доступы, compliance и operational risk.",
        "responsible": "За stop/go/needs-input решение по рискам и минимальные практичные mitigations.",
        "communicates": "Отдает automation, Overlord и reviewer risk verdict, blockers и условия продолжения.",
    },
    "olux": {
        "summary": "UX-офицер: делает интерфейсы понятными, спокойными, доступными и пригодными для реализации.",
        "does": "Разбирает flow, dashboard, copy, визуальные состояния, доступность и пользовательскую эргономику.",
        "responsible": "Чтобы UI был не просто работающим, а читаемым, удобным и проверяемым.",
        "communicates": "Передает frontend конкретные UX-критерии, а reviewer — что именно проверять глазами и браузером.",
    },
    "olfrontend": {
        "summary": "Frontend-исполнитель: строит интерфейсы, проверяет браузерное поведение, responsive-состояния и визуальную полировку.",
        "does": "Пишет UI-код, проверяет рендер, состояния, интеракции и console errors.",
        "responsible": "За пользовательскую поверхность, которая реально открывается, не разваливается и ощущается качественно.",
        "communicates": "Получает handoff от architect/UX, передает evidence и проверки reviewer/synth.",
    },
    "olbackend": {
        "summary": "Backend-исполнитель: отвечает за API, сервисы, базы, auth, миграции, интеграции и серверные тесты.",
        "does": "Реализует backend-контракты, схемы данных, jobs, observability и проверяемую серверную логику.",
        "responsible": "За надежность серверной части, корректность данных и совместимость API.",
        "communicates": "Получает архитектурный контракт и возвращает reviewer доказательства, тесты и риски.",
    },
    "olautomation": {
        "summary": "Automation/ops-офицер: превращает ручные действия в безопасные скрипты, runbooks, CI/CD и MCP-проводку.",
        "does": "Чинит Docker, PowerShell, gateway, MCP, browser automation, локальные демоны и deploy-процедуры.",
        "responsible": "За повторяемость, наблюдаемость и восстановимость операций.",
        "communicates": "Получает план от architect/risk, передает runbook и verification reviewer/watchdog/synth.",
    },
    "olwatchdog": {
        "summary": "Watchdog: следит, чтобы длинная работа не зависла, не ушла от цели и не потеряла владельца.",
        "does": "Мониторит heartbeat, stale tasks, blockers, dependency drift и необходимость split/reassign/rescue.",
        "responsible": "За темп, прозрачность статуса и раннее обнаружение остановок.",
        "communicates": "Читает Kanban/gateway состояние и отправляет Overlord сигнал вмешаться, ждать, дробить или блокировать.",
    },
    "olreviewer": {
        "summary": "Reviewer: последний контроль качества перед тем, как результат можно считать готовым.",
        "does": "Сверяет работу с acceptance criteria, проверяет тесты, диффы, регрессии, security/supply-chain сигналы.",
        "responsible": "За verdict: pass, pass_with_conditions, needs_input или block.",
        "communicates": "Получает evidence от исполнителей и risk, возвращает Overlord/synth четкое решение.",
    },
    "olsynth": {
        "summary": "Финальный синтезатор: превращает разрозненные выводы агентов в понятный пользователю итог.",
        "does": "Собирает evidence, решения, риски и изменения в одну финальную картину.",
        "responsible": "За короткий, проверяемый и пригодный к использованию финальный ответ.",
        "communicates": "Получает outputs от Overlord/reviewer/специалистов и пишет пользователю, vault или memory.",
    },
    "nerood": {
        "summary": "Легкий оркестратор для bounded-задач, когда полный совет Overlord не нужен.",
        "does": "Декомпозирует небольшую работу в простую иерархию и доводит ее через прямые worker-сессии.",
        "responsible": "За практичное выполнение небольших coding-задач без тяжелого Kanban-графа.",
        "communicates": "Получает задачу от пользователя/Codex и возвращает результат напрямую.",
    },
    "diana": {
        "summary": "Общий Hermes-профиль без проектных MCP: простой помощник для легких задач и разговора.",
        "does": "Отвечает, помогает анализировать, писать и объяснять без роли в Overlord-графе.",
        "responsible": "За быстрые общие ответы, когда не нужен специализированный профиль.",
        "communicates": "Работает напрямую с пользователем.",
    },
}


MCP_HEALTH = {
    "filesystem": ["healthy", "14 tools"],
    "sequential-thinking": ["healthy", "1 tool"],
    "mem0": ["healthy", "11 tools"],
    "github": ["healthy", "26 tools"],
    "deepcontext": ["healthy", "4 tools"],
    "ref-tools": ["healthy", "2 tools"],
    "openaiDeveloperDocs": ["healthy", "5 tools"],
    "context7": ["healthy", "2 tools"],
    "exa": ["healthy", "2 tools"],
    "tavily": ["healthy", "5 tools"],
    "obsidian": ["healthy", "15 tools; local endpoint reachable"],
    "notion": ["healthy", "HTTP OAuth server healthy; stdio healthy on olwatchdog"],
    "linear": ["healthy", "35 tools"],
    "codegraph": ["healthy", "34 tools"],
    "codegraphcontext": ["healthy", "25 tools"],
    "chrome-devtools": ["healthy", "29 tools"],
    "playwright": ["healthy", "23 tools"],
    "magic": ["healthy", "4 tools"],
    "shadcn": ["healthy", "7 tools"],
    "prisma": ["healthy", "4 tools"],
    "semgrep": ["healthy", "7 tools"],
    "socket": ["healthy", "1 tool"],
    "trivy": ["healthy", "6 tools"],
    "gitguardian": ["healthy", "18 tools"],
    "cloudflare-api": ["healthy", "2 tools"],
    "canva": ["healthy", "30 tools"],
    "vercel": ["healthy", "18 tools after OAuth refresh"],
    "browserstack": ["healthy", "29 tools after OAuth refresh"],
    "canva-dev": ["failed", "Timed out"],
    "storybook": ["gated", "Project-local; enable only when /mcp endpoint is reachable"],
    "docker-gateway": ["healthy", "8 tools through Docker MCP CLI plugin"],
    "serena": ["healthy", "22 tools"],
}


MCP_HUMAN_NOTES = {
    "browserstack": "Облачные браузеры и устройства для тестов сайта.",
    "canva": "Дизайн-полотна Canva: открыть, редактировать, экспорт.",
    "canva-dev": "Canva developer API для шаблонов и автоматизации.",
    "chrome-devtools": "Управление реальным Chrome: клики, скрины, DOM.",
    "cloudflare-api": "DNS, Pages, Workers и кеш в Cloudflare.",
    "codegraph": "Карта зависимостей кода: кто кого вызывает.",
    "codegraphcontext": "Точное окно кода вокруг функции/символа.",
    "context7": "Свежая документация популярных библиотек.",
    "deepcontext": "Глубокое чтение длинных файлов и репо целиком.",
    "docker-gateway": "Запуск других MCP-серверов через Docker.",
    "exa": "Web-поиск, который возвращает смысл, а не SEO-мусор.",
    "filesystem": "Чтение и запись файлов в sandbox-папках.",
    "github": "Чтение, коммиты, PR, issues, code-review на GitHub.",
    "gitguardian": "Поиск утечек секретов в коде и истории git.",
    "linear": "Задачи, проекты и циклы в Linear.",
    "magic": "Готовые UI-компоненты по описанию.",
    "mem0": "Долговременная память агента между сессиями.",
    "notion": "База знаний Notion: страницы, БД, заметки.",
    "obsidian": "Локальный vault Obsidian: markdown и бэклинки.",
    "openaiDeveloperDocs": "Официальные доки OpenAI: модели, API, лимиты.",
    "playwright": "Скриптовая автоматизация браузера для тестов.",
    "prisma": "Работа со схемой БД и миграциями Prisma.",
    "ref-tools": "Унифицированный поиск по техническим докам.",
    "semgrep": "Статический поиск багов и уязвимостей по правилам.",
    "sequential-thinking": "Структурированное думать шаг-за-шагом.",
    "serena": "LSP-анализ кода: символы, ссылки, безопасные правки.",
    "shadcn": "Готовые компоненты shadcn/ui для React.",
    "socket": "Аудит npm: безопасность, лицензии, supply-chain.",
    "storybook": "Каталог UI-компонентов и их состояний.",
    "tavily": "Web-поиск с источниками для ресерча.",
    "trivy": "Сканер уязвимостей образов и пакетов.",
    "vercel": "Деплои, превью и логи в Vercel.",
}


MCP_TAGS = {
    "filesystem": ["files", "core", "write"],
    "github": ["code", "repo", "review"],
    "mem0": ["memory", "context"],
    "sequential-thinking": ["reasoning", "planning"],
    "deepcontext": ["code-analysis", "context"],
    "serena": ["code-analysis", "lsp"],
    "codegraph": ["code-analysis", "graph"],
    "codegraphcontext": ["code-analysis", "graph"],
    "context7": ["docs", "reference"],
    "ref-tools": ["docs", "reference"],
    "openaiDeveloperDocs": ["docs", "openai"],
    "exa": ["web-search", "research"],
    "tavily": ["web-search", "research"],
    "obsidian": ["notes", "knowledge"],
    "notion": ["workspace", "knowledge"],
    "linear": ["tasks", "product"],
    "chrome-devtools": ["browser", "debug"],
    "playwright": ["browser", "testing"],
    "magic": ["ui", "components"],
    "shadcn": ["ui", "components"],
    "vercel": ["deploy", "frontend"],
    "canva": ["design", "assets"],
    "canva-dev": ["design", "api"],
    "browserstack": ["testing", "devices"],
    "storybook": ["ui", "catalog"],
    "prisma": ["database", "backend"],
    "semgrep": ["security", "static-analysis"],
    "socket": ["security", "supply-chain"],
    "trivy": ["security", "containers"],
    "gitguardian": ["security", "secrets"],
    "docker-gateway": ["runtime", "mcp"],
    "cloudflare-api": ["deploy", "platform"],
}


PROFILE_TAGS = {
    "overlord": ["orchestration", "director"],
    "olproduct": ["product", "scope"],
    "olarchitect": ["architecture", "contracts"],
    "olresearcher": ["research", "evidence"],
    "olrisk": ["risk", "security"],
    "olux": ["ux", "design"],
    "olfrontend": ["frontend", "ui"],
    "olbackend": ["backend", "api"],
    "olautomation": ["automation", "ops"],
    "olwatchdog": ["monitoring", "ops"],
    "olreviewer": ["review", "qa"],
    "olsynth": ["synthesis", "docs"],
    "nerood": ["auxiliary"],
    "diana": ["auxiliary"],
}


PHASES = {
    "ingress": {"label": "Ingress", "order": 0},
    "director": {"label": "Director", "order": 1},
    "council": {"label": "Council", "order": 2},
    "execution": {"label": "Execution", "order": 3},
    "control": {"label": "Control", "order": 4},
    "output": {"label": "Output", "order": 5},
    "storage": {"label": "Memory / Systems", "order": 6},
    "auxiliary": {"label": "Auxiliary", "order": 7},
}


FLOW_NODES = [
    {"id": "user", "label": "User", "phase": "ingress", "type": "external", "summary": "Starts goals and receives final results.", "ru": {"summary": "Ты — источник цели и адресат финального ответа."}},
    {"id": "cli", "label": "CLI wrappers", "phase": "ingress", "type": "gateway", "summary": "overlord-intake.ps1, overlord-swarm.ps1, direct overlord.ps1 commands.", "ru": {"summary": "PowerShell-обертки intake/swarm/chat для запуска задач."}},
    {"id": "telegram", "label": "Telegram", "phase": "ingress", "type": "gateway", "summary": "External bot gateway; configured, gateway currently stopped after cleanup.", "ru": {"summary": "Telegram-бот как внешний канал ввода задач."}},
    {"id": "gateway", "label": "Hermes gateway", "phase": "ingress", "type": "gateway", "summary": "Runs messaging adapters, cron ticker, and Kanban dispatcher when started.", "ru": {"summary": "Шлюз Hermes: мессенджеры, cron, диспатч в Kanban."}},
    {"id": "kanban", "label": "Kanban board", "phase": "storage", "type": "system", "summary": "Durable task graph; currently empty after cleanup.", "ru": {"summary": "Доска задач Overlord: спецификация, граф работ, статусы."}},
    {"id": "vault", "label": "OverlordVault", "phase": "storage", "type": "system", "summary": "Durable reports, runbooks, research, and decisions.", "ru": {"summary": "Хранилище итоговых решений и долговременных заметок Overlord."}},
    {"id": "memory", "label": "Memory layer", "phase": "storage", "type": "system", "summary": "Built-in memory plus Mem0, Obsidian, Notion, Linear, GitHub evidence lanes.", "ru": {"summary": "Долговременная память: Mem0, Obsidian, Notion, Linear, GitHub."}},
]


FLOW_EDGES = [
    ["user", "cli", "new goal"],
    ["user", "telegram", "message"],
    ["telegram", "gateway", "platform adapter"],
    ["cli", "kanban", "create intake card"],
    ["gateway", "kanban", "dispatch / monitor"],
    ["kanban", "overlord", "triage owner"],
    ["overlord", "olproduct", "scope"],
    ["overlord", "olarchitect", "architecture"],
    ["overlord", "olresearcher", "research"],
    ["overlord", "olrisk", "risk"],
    ["overlord", "olux", "UX"],
    ["overlord", "olfrontend", "dispatch"],
    ["overlord", "olbackend", "dispatch"],
    ["overlord", "olautomation", "dispatch"],
    ["overlord", "olreviewer", "gate"],
    ["olproduct", "olarchitect", "criteria"],
    ["olproduct", "olux", "scope"],
    ["olproduct", "olsynth", "rationale"],
    ["olresearcher", "olproduct", "evidence"],
    ["olresearcher", "olarchitect", "evidence"],
    ["olresearcher", "olreviewer", "evidence"],
    ["olresearcher", "olsynth", "evidence"],
    ["olux", "olfrontend", "UX handoff"],
    ["olux", "olreviewer", "UX review"],
    ["olux", "olsynth", "UX rationale"],
    ["olarchitect", "olfrontend", "frontend contract"],
    ["olarchitect", "olbackend", "backend contract"],
    ["olarchitect", "olautomation", "ops contract"],
    ["olarchitect", "olreviewer", "design review"],
    ["overlord", "olwatchdog", "heartbeat"],
    ["olfrontend", "olreviewer", "evidence"],
    ["olfrontend", "olsynth", "frontend evidence"],
    ["olbackend", "olreviewer", "evidence"],
    ["olbackend", "olsynth", "backend evidence"],
    ["olautomation", "olreviewer", "evidence"],
    ["olautomation", "olwatchdog", "ops signal"],
    ["olautomation", "olsynth", "runbook"],
    ["olrisk", "olautomation", "risk gate"],
    ["olrisk", "olreviewer", "risk verdict"],
    ["olrisk", "overlord", "escalation"],
    ["olwatchdog", "overlord", "intervention signal"],
    ["olreviewer", "overlord", "verdict"],
    ["olreviewer", "olsynth", "review verdict"],
    ["overlord", "olsynth", "final package"],
    ["olsynth", "vault", "durable note"],
    ["olsynth", "memory", "reusable context"],
    ["olsynth", "user", "final answer"],
]


TASK_STEPS = [
    {"step": 1, "name": "Ingress", "owner": "User / CLI / Telegram", "detail": "A goal enters through overlord-intake.ps1, direct chat, or Telegram."},
    {"step": 2, "name": "Intake card", "owner": "Kanban", "detail": "The wrapper creates an Overlord task on board 'overlord' with triage and a spec-first contract."},
    {"step": 3, "name": "Classification", "owner": "overlord", "detail": "Overlord decides direct mode, council mode, worker graph mode, research swarm, or rescue mode."},
    {"step": 4, "name": "Spec", "owner": "overlord + council", "detail": "Goal, constraints, non-goals, acceptance criteria, risks, task graph, tool plan, and verification plan are made explicit."},
    {"step": 5, "name": "Delegation", "owner": "overlord", "detail": "Specialist child tasks are assigned via Kanban/delegation, each with expected MCPs, skills, outputs, and verification."},
    {"step": 6, "name": "Execution", "owner": "olfrontend / olbackend / olautomation", "detail": "Implementation workers produce changes, evidence, screenshots, tests, scripts, or runbooks."},
    {"step": 7, "name": "Control", "owner": "olwatchdog / olrisk / olreviewer", "detail": "Progress, blockers, risk, regressions, and acceptance evidence are checked before trust is granted."},
    {"step": 8, "name": "Synthesis", "owner": "olsynth + overlord", "detail": "The final answer is produced and durable knowledge can be stored in the vault/memory lanes."},
]


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def has_env_key(path: Path, key: str) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith(f"{key}="):
            value = line.split("=", 1)[1].strip().strip('"')
            return bool(value)
    return False


def count_tasks(db_path: Path) -> int | None:
    if not db_path.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            return int(con.execute("select count(*) from tasks").fetchone()[0])
        finally:
            con.close()
    except Exception:
        return None


def transport_for(server: dict) -> str:
    if server.get("url"):
        return "http"
    if server.get("command"):
        return "stdio"
    return "configured"


def soul_title_and_excerpt(path: Path) -> tuple[str, str]:
    if not path.exists():
        return "", ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0].lstrip("# ") if lines else ""
    prose = []
    for line in lines[1:12]:
        if not line.startswith("#") and len(line) > 18:
            prose.append(line)
    return title, " ".join(prose)[:540]


def build_profiles() -> list[dict]:
    profiles = []
    for profile_dir in sorted(PROFILES_ROOT.iterdir() if PROFILES_ROOT.exists() else []):
        if not profile_dir.is_dir():
            continue
        profile = profile_dir.name
        cfg = load_yaml(profile_dir / "config.yaml")
        model = cfg.get("model") or {}
        delegation = cfg.get("delegation") or {}
        kanban = cfg.get("kanban") or {}
        mcp_servers = cfg.get("mcp_servers") or {}
        soul_title, soul_excerpt = soul_title_and_excerpt(profile_dir / "SOUL.md")
        meta = ROLE_META.get(profile, {})
        servers = []
        for name, raw in sorted(mcp_servers.items()):
            raw = raw or {}
            enabled = not (isinstance(raw, dict) and raw.get("enabled") is False)
            health, note = MCP_HEALTH.get(name, ["unknown", "No latest smoke-test note captured"])
            servers.append(
                {
                    "name": name,
                    "enabled": enabled,
                    "transport": transport_for(raw if isinstance(raw, dict) else {}),
                    "health": health,
                    "note": note,
                    "humanNote": MCP_HUMAN_NOTES.get(name, "MCP-инструмент для этой роли."),
                    "tags": MCP_TAGS.get(name, ["mcp"]),
                }
            )
        profiles.append(
            {
                "id": profile,
                "label": profile,
                "phase": meta.get("phase", "auxiliary"),
                "title": meta.get("title", soul_title or profile),
                "responsibility": meta.get("responsibility", soul_excerpt),
                "ru": RU_ROLE_META.get(profile, {}),
                "tags": PROFILE_TAGS.get(profile, [meta.get("phase", "auxiliary")]),
                "owns": meta.get("owns", []),
                "receivesFrom": meta.get("receivesFrom", []),
                "handsTo": meta.get("handsTo", []),
                "model": model.get("default", ""),
                "provider": model.get("provider", ""),
                "reasoningEffort": (cfg.get("agent") or {}).get("reasoning_effort", ""),
                "maxTurns": (cfg.get("agent") or {}).get("max_turns"),
                "delegation": {
                    "maxIterations": delegation.get("max_iterations"),
                    "maxConcurrentChildren": delegation.get("max_concurrent_children"),
                    "maxSpawnDepth": delegation.get("max_spawn_depth"),
                    "orchestratorEnabled": delegation.get("orchestrator_enabled"),
                },
                "kanban": {
                    "dispatchInGateway": kanban.get("dispatch_in_gateway"),
                    "autoDecompose": kanban.get("auto_decompose"),
                    "failureLimit": kanban.get("failure_limit"),
                },
                "soul": {
                    "title": soul_title,
                    "excerpt": soul_excerpt,
                    "full": (profile_dir / "SOUL.md").read_text(encoding="utf-8", errors="ignore") if (profile_dir / "SOUL.md").exists() else "",
                    "path": str(profile_dir / "SOUL.md"),
                },
                "configPath": str(profile_dir / "config.yaml"),
                "auth": {
                    "env": (profile_dir / ".env").exists(),
                    "authJson": (profile_dir / "auth.json").exists(),
                    "mcpTokens": (profile_dir / "mcp-tokens").exists(),
                    "skills": (profile_dir / "skills").exists(),
                },
                "mcp": servers,
            }
        )
    return profiles


def build_mcp_inventory(profiles: list[dict]) -> list[dict]:
    usage: dict[str, dict] = {}
    for profile in profiles:
        for server in profile["mcp"]:
            record = usage.setdefault(
                server["name"],
                {
                    "name": server["name"],
                    "health": server["health"],
                    "note": server["note"],
                    "humanNote": server.get("humanNote", MCP_HUMAN_NOTES.get(server["name"], "MCP-инструмент для этой роли.")),
                    "profiles": [],
                    "enabledProfiles": [],
                    "disabledProfiles": [],
                    "transports": set(),
                    "tags": set(server.get("tags", MCP_TAGS.get(server["name"], ["mcp"]))),
                },
            )
            record["profiles"].append(profile["id"])
            record["transports"].add(server["transport"])
            record["tags"].update(server.get("tags", []))
            if server["enabled"]:
                record["enabledProfiles"].append(profile["id"])
            else:
                record["disabledProfiles"].append(profile["id"])
    result = []
    for record in usage.values():
        result.append(
            {
                "name": record["name"],
                "health": record["health"],
                "note": record["note"],
                "humanNote": record.get("humanNote", MCP_HUMAN_NOTES.get(record["name"], "MCP-инструмент для этой роли.")),
                "profiles": sorted(record["profiles"]),
                "enabledProfiles": sorted(record["enabledProfiles"]),
                "disabledProfiles": sorted(record["disabledProfiles"]),
                "transports": sorted(record["transports"]),
                "tags": sorted(record["tags"]),
            }
        )
    return sorted(result, key=lambda item: item["name"])


def main() -> None:
    profiles = build_profiles()
    mcp_inventory = build_mcp_inventory(profiles)
    env_path = HERMES_ROOT / "profiles" / "overlord" / ".env"
    startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Hermes_Gateway_overlord.cmd"
    data = {
        "generatedAt": date.today().isoformat(),
        "projectRoot": str(PROJECT_ROOT),
        "hermesRoot": str(HERMES_ROOT),
        "phases": PHASES,
        "profiles": profiles,
        "mcpInventory": mcp_inventory,
        "flow": {"nodes": FLOW_NODES + [{"id": p["id"], "label": p["label"], "phase": p["phase"], "type": "profile", "summary": p["responsibility"]} for p in profiles], "edges": FLOW_EDGES},
        "taskSteps": TASK_STEPS,
        "runtime": {
            "gateway": "stopped after cleanup",
            "windowsStartupItem": startup.exists(),
            "telegramConfigured": has_env_key(env_path, "TELEGRAM_BOT_TOKEN"),
            "telegramAllowlist": has_env_key(env_path, "TELEGRAM_ALLOWED_USERS"),
            "defaultBoardTasks": count_tasks(HERMES_ROOT / "kanban.db"),
            "overlordBoardTasks": count_tasks(HERMES_ROOT / "kanban" / "boards" / "overlord" / "kanban.db"),
            "agentMaxTurns": next((p.get("maxTurns") for p in profiles if p["id"] == "overlord"), None),
            "delegationMaxIterations": next((p.get("delegation", {}).get("maxIterations") for p in profiles if p["id"] == "overlord"), None),
        },
        "wrappers": [
            {"name": "overlord-intake.ps1", "mode": "Full council -> execution -> verification -> synthesis", "path": str(PROJECT_ROOT / "overlord-intake.ps1")},
            {"name": "overlord-swarm.ps1", "mode": "Fast council / research swarm", "path": str(PROJECT_ROOT / "overlord-swarm.ps1")},
            {"name": "overlord.ps1 chat", "mode": "Direct interactive session", "path": str(PROJECT_ROOT / "overlord.ps1")},
            {"name": "telegram-connect.ps1", "mode": "Telegram gateway configuration", "path": str(PROJECT_ROOT / "telegram-connect.ps1")},
            {"name": "storybook-enable.ps1", "mode": "Project-local Storybook MCP toggle", "path": str(PROJECT_ROOT / "storybook-enable.ps1")},
        ],
    }
    output = "window.HERMES_DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    (Path(__file__).resolve().parent / "data.js").write_text(output, encoding="utf-8")
    print(f"Wrote {Path(__file__).resolve().parent / 'data.js'}")


if __name__ == "__main__":
    main()
