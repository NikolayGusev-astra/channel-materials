# Отчуждаемая копия скиллов /teachme

Снимок набора скиллов, на которые ссылается зонтичный диспетчер `teachme`.
Дата: 2026-10-03. Объём: 8 МБ, 29 папок со SKILL.md.

Копия нужна для двух вещей: переноса на другую машину и страховки от куратора.
Фоновый процесс архивирует то, чем давно не пользовались, поэтому новые скилы
без пометки попадают в его зону.

## Как развернуть

Скопировать содержимое `skills/` в каталог скиллов профиля Hermes и выполнить
`/reload-skills` в сессии. Реестр команд кэшируется, без перезагрузки новое
имя в автоподсказке не появится, хотя `skill_view` уже видит файл.

Проверить, что всё на месте:

```bash
find skills -name SKILL.md | wc -l      # должно быть 29
hermes skills list | grep -E "teachme|eli5|asd-ste100|3b1b"
```

## Состав

Текст: `asd-ste100`, `humanizer-ru`, `dont-paste-the-ai`, `pstack-teach`, `pstack-unslop`

Схема: `eli5`, `docs-canvas`, `case-map-html`, `claude-design`, `pretext`,
`system-designing`, `ascii-art`, `baoyu-comic`

Видео: `explainer-video-3b1b`, `faceless-explainer`, `hyperframes`,
`hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`,
`hyperframes-registry`, `motion-graphics`, `slideshow`, `product-launch-video`

Озвучка: `t2v`, `media-use`

Курс: `course-program-design`, `teaching-create-learning-path`, `course-authoring`

Зонтичный: `teachme`

## Что требует окружения

Большинство скиллов работают из коробки. Три требуют проверки перед
использованием, потому что упираются в то, чего может не быть на машине:

- `explainer-video-3b1b`: Manim 0.20.1 в venv hermes. LaTeX ставится отдельно,
  см. ниже. Без MiKTeX формулы придётся писать через `Text` с юникодом.
- `t2v`: локальная модель синтеза речи на GPU, референс голоса в проекте
  Raon-OpenTTS. Без него скилл отдаст ошибку загрузки.
- `media-use`: облачные провайдеры (HeyGen) требуют входа, офлайн-ветка
  работает на локальных движках.

## LaTeX для видео: установка с нуля

Manim проверяет два бинаря, а не один: `latex` (движок вёрстки) и `dvisvgm`
(конвертер в SVG для анимации). Без второго формулы не заработают даже при
зелёном первом.

```bash
# portable-режим, без запроса UAC - единственный вариант на машине без прав админа
scoop install miktex

# иначе MiKTeX откроет диалог на каждый недостающий пакет и агент зависнет
initexmf --set-config-value=[MPM]AutoInstall=1
```

Альтернативы при наличии прав админа: `winget install MiKTeX.MiKTeX` (тот же
дистрибутив, но интерактивно), TeX Live через winget (полная схема, порядка
7 ГБ). Пакет `latex` в scoop - устаревшее имя, дубликат `miktex`.

Проверка:

```bash
grep AutoInstall ~/scoop/persist/miktex/texmfs/config/miktex/config/miktex.ini
# ожидается AutoInstall=1

PY="C:/Users/n.gusev/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
"$PY" -m manim checkhealth
# ожидаются четыре PASSED, включая latex и dvisvgm
```

Грабли, на которые ушло время:

- `miktex --set-default-package-install=1` (каноничная форма) на этой машине
  висела дольше трёх минут и была прервана по таймауту. `initexmf` с тем же
  эффектом отработала за секунду.
- `mpm --admin` в портативной установке отказывает: "Option --admin only makes
  sense for a shared MiKTeX setup". Для точечной доустановки хватает
  `mpm --install=<пакет>`.
- Exit code рендера не доказывает, что формулы работают. Проверяется
  `checkhealth` и кадром, а не кодом возврата.

## Лицензии

`asd-ste100` принесён из `github.com/danyuchn/asd-ste100-skill`, MIT, файл
LICENSE сохранён рядом со SKILL.md. Остальные скиллы - локальные, проверяй
лицензию по исходному репозиторию, если собираешься их перепубликовывать.