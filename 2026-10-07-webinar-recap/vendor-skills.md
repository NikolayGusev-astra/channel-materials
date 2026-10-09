# Джентльменский набор вендорских скиллов для Hermes Agent

Собрано 9 октября 2026 по живому Skills Hub (`hermes skills search`). Всё проверено поиском, не по памяти. Установка: `hermes skills install <identifier>`.

## Правило выбора

Два уровня доверия:
- **official**: 154 скилла от Nous Research, идут с Hermes;
- **вендорские**: написаны самим вендором продукта (docker/skills, openai/skills). Это не community-шум, у вендора ответственность за актуальность. В Hub имеют trust `community`/`trusted`, источник при этом официальный репозиторий вендора.

Остальное из skills.sh (тысячи клонов «docker-best-practices» из личных репо) в набор не входит.

## DevOps / инфраструктура

| Скилл | Откуда | Зачем | Установка |
|---|---|---|---|
| docker-management | official (Nous) | контейнеры, образы, volumes, Compose | `hermes skills install official/devops/docker-management` |
| hermes-s6-container-supervision | official (Nous) | s6-сервисы внутри Docker-образа Hermes | `hermes skills install official/devops/hermes-s6-container-supervision` |
| watchers | official (Nous) | поллинг RSS/JSON/страниц для мониторинга изменений | `hermes skills install official/devops/watchers` |
| pinggy-tunnel | official (Nous) | SSH-туннели/проброс портов без белого IP | `hermes skills install official/devops/pinggy-tunnel` |

## Docker (вендорские, от Docker Inc)

Репо: https://github.com/docker/skills, 548 звёзд, лицензия Apache-2.0, среди авторов инженеры Docker glours и dgageot. Ставятся по одному:

| Скилл | Зачем |
|---|---|
| docker-project-foundations | структурирование Dockerized-проекта, Dockerfile/compose.yaml/.dockerignore |
| docker-build-strategies | эффективные и безопасные сборки образов |
| docker-compose-patterns | многоконтейнерные стеки в Compose |
| docker-agent-config / docker-agent-run / docker-agent-deploy | Docker Agent: agent.yaml, запуск, деплой |
| docker-sandboxes-* | изолированные microVM-песочницы (sbx CLI) |

```
hermes skills install skills-sh/docker/skills/docker-compose-patterns
hermes skills install skills-sh/docker/skills/docker-build-strategies
```
Полный список: https://skills.sh/docker/skills

## Cloudflare (вендорский скилл из репозитория openai/skills)

| Скилл | Откуда | Зачем |
|---|---|---|
| cloudflare-deploy | openai/skills (trust: trusted) | единое дерево решений по платформе Cloudflare: Workers, Pages, Durable Objects, привязки, деплой через Wrangler. Источник: https://github.com/openai/skills/blob/main/skills/.curated/cloudflare-deploy/SKILL.md |
| cloudflare-temporary-deploy | official (Nous) | задеплоить Worker без аккаунта, через `wrangler --temporary` |
| publish-site | official (Nous) | версионированные деплои сайта на GitHub/Cloudflare Pages |

```
hermes skills install openai/skills/.curated/cloudflare-deploy
hermes skills install official/web-development/cloudflare-temporary-deploy
```

## Что проверено и чего в official НЕТ

Прогнал поиск по official-источнику: terraform, ansible, kubernetes, prometheus, grafana, nginx, github actions. Ноль официальных скиллов. Это честный ответ на вопрос из чата «а что ещё есть вендорского»: по этим темам только community из skills.sh, качество лотерейное. Для них лучше писать свои скиллы под свою практику.

## Security / смежное из official

| Скилл | Зачем |
|---|---|
| oss-forensics | forensic-разбор GitHub-репо перед тем как брать код |
| web-pentest | веб-пентест под рукой |
| 1password | CLI 1Password: чтение секретов агентом |

## Как проверять перед установкой

```
hermes skills inspect <identifier>   # превью SKILL.md без установки
hermes skills audit                  # перескан установленных
hermes skills list                   # что стоит в профиле
```

Статья про то, как устроена лестница скиллов: https://hermes-agent.ru/news/explain-skills-ladder/
