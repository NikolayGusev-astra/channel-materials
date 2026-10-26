---
title: "Топ-10 скиллов Hermes Agent на каждый день"
slug: hermes-top10-skills
date: 2026-10-21
tags: [hermes, skills, agents, ai]
author: Гусев Николай
site:
  slug: hermes-top10-skills
  tags: [hermes, skills, agents]
  cover: cover.png
---
# Топ-10 скиллов Hermes Agent на каждый день

![Как агент выбирает скилл: задача, скан каталога, загрузка в контекст](/hermes-top10-skills/cover.png)

Я веду статистику запусков [скиллов](https://hermes-agent.ru/glossary/skill/) в своём Hermes Agent: SQLite-база сессий хранит каждый тул-колл, и по ней видно не то, что «должно пригодиться», а то, что реально используется. На момент октября 2026 в базе 191 910 сообщений с тул-коллами и 4 268 вызовов `skill_view` по 609 разным скиллам. Из этих вызовов и родился этот топ.

![GIF: агент получает задачу, сканирует каталог скиллов, совпавший cursor грузится в контекст](/hermes-top10-skills/skill-router.gif)

[Скилл](https://hermes-agent.ru/glossary/skill/) - это каталог с `SKILL.md`: описание триггеров, процедура, гейты, питфоллы из реальной работы. Агент загружает скилл в контекст, когда задача подходит под триггер, и дальше работает по его процедуре, а не по общим соображениям. Нижеприведённые десять - публичные копии моих рабочих скиллов, забирайте и адаптируйте.

## Зачем вообще скиллы, если есть промпт

Промпт живёт один запрос. Скилл накапливает: каждый раз, когда я наступаю на грабли, правило отправляется в SKILL.md соответствующего скилла, и в следующей сессии агент их уже знает. Через полгода такой файл превращается в плотную выжимку шрамов - и это работает лучше любой памяти.

Как скиллы уложены в [профили](https://hermes-agent.ru/glossary/profil/) и проекты, я разбирал в [статье про профили, скиллы и A2A](https://hermes-agent.ru/news/skills-profiles-a2a/): у каждого домена свой профиль со своим набором скиллов, и дисциплина их версионирования - отдельная работа.

Показательно, что в топе не «умные» скиллы, а диспетчеры и гейты: роутер портированных инженерных скиллов (188 запусков), планировщик (81), вики-база знаний (80). Агенту чаще нужна дисциплина и процедура, чем дополнительный интеллект.

## Десять скиллов

### 1. cursor - роутер инженерных скиллов (188 запусков)

Диспетчер над 78 портированными скиллами из плагинов Cursor и 25 портами из `addyosmani/agent-skills`. Пишешь `/cursor почини падающий CI` - роутер сам выбирает нужные скиллы (`fix-ci`, `loop-on-ci`, `run-smoke-tests`), грузит их и применяет.

```text
/cursor почини падающий CI и сделай ревью перед мержем
```

Что охраняет: не править код, пока крутятся read-only [субагенты](/glossary/subagent/); push только по явному «ок» пользователя; RED до GREEN в TDD; модель для делегата задавать явно.

- [cursor.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/cursor.md)

### 2. writing-plans - план до кода (81)

План в Markdown: декомпозиция на задачи с файлами, код-скетчами, тестами и критериями приёмки. Каждый пункт плана самодостаточен - его можно отдать другому агенту или человеку.

```text
/writing-plans добавь в сервис rate-limiting по API-ключам
```

- [writing-plans.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/writing-plans.md)

### 3. llm-wiki - база знаний (80)

Личная вики в стиле Karpathy LLM Wiki: сущности, концепции, источники, связанные перекрёстными ссылками. Все долговременные знания агента живут там, а не в угасающем контексте сессий.

```text
что я знаю про настройку chrony на стендах?
```

- [llm-wiki.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/llm-wiki.md)

### 4. writer - диспетчер контента (75)

Маршрутизатор текстов по площадкам: Telegram-канал, Telegra.ph, Хабр, сайт. Внутри - гейты публикации, которые проверяет скрипт, а не агент: длина подписи, живость ссылок, реестр постов.

```text
/writer статья про наш пайплайн бенчмарков, черновик на утверждение
```

- [writer.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/writer.md)

### 5. codex - делегирование (68)

Передача кодовых задач в Codex CLI: генерация ветки, узкий [промпт](/glossary/prompt/), проверка диффа, коммит только после ревью. Агент-компаньон готовит задачу и принимает результат, CLI делает тяжёлую правку.

```text
/codex сделай фикс из задачи 5 плана, прогони тесты, покажи дифф
```

- [codex.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/codex.md)

### 6. humanizer-ru - линтер русского текста (39)

Механический гейт на AI-штампы: длинные тире, «ёлочки», шаблонные связки, парцеляции. ERROR не переживает публикацию - правило из скилла writer, и оно сэкономило мне не один переделанный текст.

```bash
python content/humanizer-ru/scripts/lint.py article.md
```

- [humanizer-ru.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/humanizer-ru.md)

### 7. be-ambitious - углубление промпта (36)

Превращает задачу в более глубокую версию самой себя, не в большую. Четыре вопроса до рерайта: что сделал бы топовый профессионал; из какого сырья начал; какими методами; что, кроме автора и модели, подтвердит результат.

```text
/be-ambitious напиши статью про выбор локальной LLM под задачу
```

- [be-ambitious.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/be-ambitious.md)

### 8. ramsay - прожарка перед отправкой (33)

Роль жёсткого шефа в духе Гордона Рамзи из Kitchen Nightmares: отчёт - это блюдо, и если он сырой, он уходит обратно на кухню, а не к гостю. Ищет места, за которые зацепится строгий проверяющий: невалидные сравнения, незавершённое как завершённое, двойные числа между разделами, «сопоставимо» без доказательства. Двадцать атак чек-листом, PRISM-проход по шести осям и премортем «отчёт опубликован - откуда негатив через неделю?». «It's raw» - вердикт для сырых цифр.

```text
/ramsay прогони черновик отчёта по migrating-тестам
```

- [ramsay.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/ramsay.md)

### 9. research-before-build - не изобретать велосипед (12)

Перед любым новым инструментом: найти два существующих решения и разобрать, как они устроены. Нет двух аналогов - задача идёт на уточнение, а не на изобретение. Сэкономила мне уже десятки часов написания лишнего кода.

```text
/research-before-build нужен скрипт синкронизации wiki с git
```

- [research-before-build.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/research-before-build.md)

### 10. session-audit - рентген своих сессий (8)

Аудит собственной базы сессий Hermes: атрибуция по проектам, счётчики трения (nudge-сообщения, error rate по тулам), здоровье крона. Отвечает на вопрос «что чинить дальше» числами, а не ощущениями. Этим же скиллом собрана статистика для этой статьи.

```text
/session-audit какие инструменты чаще всего падают за месяц?
```

- [session-audit.md](https://github.com/NikolayGusev-astra/channel-materials/blob/master/2026-10-21-hermes-top10-skills/skills/session-audit.md)

## Что дальше


Про то, как научить агента объяснять, а не только делать, - в [статье про 29 скиллов объяснения](https://hermes-agent.ru/news/explain-skills-ladder/). Про [профили](https://hermes-agent.ru/glossary/profil/) и мульти-подписочные конфигурации - в [разборе multi-subscription профилей](https://hermes-agent.ru/news/multi-subscription-profiles/).

Файлы скиллов лежат в этом каталоге, лицензия MIT. Счётчики запусков - из живой базы сессий, не из ощущений.
