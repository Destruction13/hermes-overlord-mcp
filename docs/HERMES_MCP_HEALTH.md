# Hermes MCP Health

Дата проверки: 2026-05-25. Секреты не раскрывались; OAuth/API значения не приведены.

## Итог

- Healthy: большинство базовых и инженерных MCP реально подключаются и отдают tools.
- Fixed this pass: `docker-gateway`, `serena`; `figma` removed from `olfrontend`.
- OAuth-refreshed: `notion`, `vercel`, `canva`, `browserstack` подключаются на сохранённых токенах.
- Gated by project: `storybook`. `sonarqube` removed by user request because other installed tools cover the same need.

## Unique MCP Status

| MCP | Status | Notes |
|---|---|---|
| filesystem | healthy | 14 tools |
| sequential-thinking | healthy | 1 tool |
| mem0 | healthy | 11 tools |
| github | healthy | 26 tools |
| deepcontext | healthy | 4 tools |
| ref-tools | healthy | 2 tools |
| openaiDeveloperDocs | healthy | 5 tools |
| context7 | healthy | 2 tools |
| exa | healthy | 2 tools |
| tavily | healthy | 5 tools |
| obsidian | healthy | 15 tools; local endpoint reachable |
| notion HTTP | healthy | 14 tools |
| notion stdio | healthy | 22 tools on `olwatchdog` |
| linear | healthy | 35 tools |
| codegraph | healthy | 34 tools |
| codegraphcontext | healthy | 25 tools |
| chrome-devtools | healthy | 29 tools |
| playwright | healthy | 23 tools |
| magic | healthy | 4 tools |
| shadcn | healthy | 7 tools |
| prisma | healthy | 4 tools |
| semgrep | healthy | 7 tools |
| socket | healthy | 1 tool |
| trivy | healthy | 6 tools |
| gitguardian | healthy | 18 tools |
| cloudflare-api | healthy | 2 tools |
| canva | healthy | 30 tools |
| vercel | healthy | 18 tools after OAuth refresh |
| browserstack | healthy | 29 tools after OAuth refresh |
| figma | removed | OAuth registration failed: 403 Forbidden, so it was removed from `olfrontend` |
| canva-dev | failed | Timed out |
| storybook | gated/off | Enable per project only after local endpoint `127.0.0.1:6006/mcp` is reachable |
| sonarqube | removed | Removed from `olreviewer`; Semgrep, Trivy, Socket, GitGuardian, CodeGraph remain available |
| miro | removed | OAuth redirect/callback flow did not complete reliably, so it was removed from `olux` MCP config |
| docker-gateway | healthy | 8 tools after adding `ProgramData` env for Docker MCP on Windows |
| serena | healthy | 22 tools after cache/warm start and enabling profiles |

## Profile Notes

- `overlord`, `olproduct`, `olsynth`: common research/memory/docs MCP set; `docker-gateway` and `serena` are enabled and healthy.
- `olfrontend`, `olux`: largest UI/browser/design MCP sets; Figma and Miro removed, Storybook remains project-local/gated.
- `olbackend`, `olrisk`, `olreviewer`: security/backend MCPs are mostly healthy; SonarQube removed.
- `olwatchdog`: lean operational MCP set works, including stdio Notion.
- `nerood`, `diana`: no MCP servers configured.

## Evidence

- `hermes mcp list`
- `hermes mcp test <server>` run from `overlord` and relevant `ol*` profiles
- `%LOCALAPPDATA%\hermes\profiles\*\config.yaml`
