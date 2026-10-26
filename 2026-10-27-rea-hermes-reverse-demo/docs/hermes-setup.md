# REA в Hermes - мануал по установке

> Публикационная копия мануала по установке REA в Hermes Agent (Windows).
> Пути обобщены до переменных окружения; живая версия с конкретными путями - у автора.


REA (Reverse Engineer Anything) 6.8.0, MIT: MCP-сервер + CLI + скилл для
реверс-инжиниринга приложений без исходников — бинарники, Electron/JS, .NET,
APK, прошивки, сайты. Репозиторий: https://github.com/morluto/rea (~390k
звёзд). Установлено 26.10.2026, всё из этого файла проверено живым прогоном,
кроме раздела «Не проверено».

## Что где лежит

- CLI: `rea` — глобальный npm-пакет `rea-agents@6.8.0`
  (`%APPDATA%\npm\rea`).
- Node под REA: `%LOCALAPPDATA%\hermes\tools\node-v24.22.1-win-x64\`
  (portable, LTS Krypton). Системный Node 22.18.0 остался нетронутым.
- MCP-сервер: запись `rea` в `%LOCALAPPDATA%\hermes\config.yaml`,
  блок `mcp_servers` (строки ~747–755).
- Скилл: `%LOCALAPPDATA%\hermes\skills\reverse-engineer-anything\`
  (версия 49, 229 инструментов, 7 референсов). Ставится и обновляется самим
  `rea setup` — руками не править, doctor сверяет identity и версию.
- Клон репо для доков/исходников: `<project-dir>\`.

## Почему отдельный Node

`rea setup` и `rea doctor` жёстко требуют Node ≥22.23.4, ≥24.22.1 или
≥26.12.1 — на 22.18.0 setup отвечает `needs_human` и ничего не пишет. При этом
сам MCP-сервер на 22.18.0 стартует и отдаёт список тулов. Решение: portable
Node 24.22.1 в `hermes\tools\`, setup запускался с ним первым в PATH. Регистрация
привязывает `process.execPath` (исходники `SetupHost.ts`:
`setupRegistrationCommand` биндит runtime, которым запущен setup), поэтому в
config.yaml прописан абсолютный путь к node.exe 24.22.1 — системные обновления
Node её не сломают.

## Что записано в config.yaml

```yaml
  rea:
    command: %LOCALAPPDATA%\hermes\tools\node-v24.22.1-win-x64\node.exe
    args:
      - %APPDATA%\npm\node_modules\rea-agents\scripts\rea.mjs
      - mcp
    enabled: true
    lazy: true
    timeout: 600
    connect_timeout: 60
```

- `lazy: true` — Hermes подключает сервер при первом вызове инструмента, а при
  старте регистрирует 229 тулов из персистентного кэша схем. Без кэша (первый
  запуск) Hermes сам делает обычный коннект и заполняет кэш — fallback
  подтверждён в исходниках (`mcp_tool_discovery.py`).
- `timeout: 600` — деинжиниринг бинарника живёт дольше дефолтных 120 с на вызов.
- Бэкап конфига до установки: `config.yaml.rea.backup` рядом с config.yaml
  (создал `rea setup`) плюс `%TEMP%\config.yaml.bak-rea`.

## Как пользоваться

После рестарта Hermes тула видны как `mcp_rea_*` (229 штук, в отложенном
каталоге — контекст не раздувают). Скилл подхватывается автоматически: любая
задача, где вывод зависит от скомпилированного артефакта или нужен рантайм-
эвиденс, возвращает REA.

Типовые формулировки:

- «Разбери этот Electron-приложение: `C:\...\app.asar` — как устроен модуль X»
  — статический JS-анализ, провайдеры не нужны.
- «Собери evidence по функции Y из этого exe и предложи реализацию» — нужен
  нативный провайдер (см. ниже).
- «Сравни поведение версии 1.2 и 1.3 по захвату трафика» — runtime-наблюдение.

CLI доступен и без агента (175 команд): `rea analyze <путь> --json`,
`rea --help`, полный список `rea --llms`. Каждый вызов CLI — отдельный процесс,
результаты сохраняй в файл: полный evidence по реальному приложению — сотни
мегабайт; проекция в summary ~10 КБ (`rea inspect-analysis-view`).

## Провайдеры нативного анализа

Пока не настроены — нативные бинарники (exe, ELF, Mach-O) без них не
разбираются. Статический JS/Electron работает уже сейчас.

- Ghidra: распаковать релиз 12.1.x, выставить `GHIDRA_INSTALL_DIR`.
- Hopper: `rea setup --install-hopper` (спросит одобрение).
- IDA: `REA_IDA_MCP_CONFIG` — JSON регистрации upstream IDA MCP
  (док: `docs/ida-provider.md` в клоне).
- JADX (Android): `REA_JADX_MCP_JAR` — путь к jadx-headless-mcp 0.7.1, REA сам
  его не скачивает.
- Переменные добавлять в `env:` записи `rea` в config.yaml.

## Обновление

```bash
npm install -g rea-agents
export PATH="$LOCALAPPDATA/hermes/tools/node-v24.22.1-win-x64:$PATH"
rea setup --client hermes --skill --yes
```

Потом рестарт Hermes. `rea setup` делает бэкап конфига и не трогает чужие
записи (проверено: diff до/после — только блок rea).

## Диагностика

- `rea doctor --json` — запускать с Node 24 в PATH (export выше), иначе
  ложный `missing_dependency` по node.
- `rea doctor --client hermes --json` — только регистрация hermes.
- Если тулов нет в сессии при живой регистрации — рестарт агента; doctor не
  доказывает, что текущая сессия подключилась.
- Дальше по лестнице восстановления: `references/connection-and-recovery.md`
  внутри скилла.

## Откат

1. Убрать блок `rea` из `mcp_servers` в config.yaml (или вернуть
   `config.yaml.rea.backup`).
2. Удалить `%LOCALAPPDATA%\hermes\skills\reverse-engineer-anything\`.
3. `npm rm -g rea-agents`.
4. Node 24.22.1 можно оставить — изолированная папка, ничем не управляется.

## Проверено и не проверено

Проверено живым прогоном 26.10.2026:

- `rea --version` → 6.8.0; `rea doctor --json` (полный отчёт, 12 клиентов).
- `rea setup --client hermes --skill --yes` → `status: ready`, применено
  `configured_hermes` + `installed_skill`; diff конфига — только блок rea.
- Raw stdio-проба зарегистрированной командой: initialize → serverInfo rea
  6.8.0; tools/list → 229 тулов; tools/call `inspect_analysis_settings` →
  живой ответ с настройками.

Не проверено (границы):

- Появление тулов в сессии Hermes — после рестарта агента.
- Реальный разбор цели (Electron-приложения, бинарника) — первый запуск ещё
  не делали.
- Нативные провайдеры — не настроены, их сценарии не гонялись.
