# paramiko для администрирования стендов (Windows-агент)

## Почему paramiko, а не ssh из терминала

Windows-агент работает через git-bash/MSYS. `cmd.exe` не имеет одинарных кавычек и
режет строку своими операторами (`; | && > <`) РАНЬШЕ, чем её увидит ssh, поэтому
составная удалённая команда разваливается, а кавычки доезжают до удалённой машины
как обычные символы (классика: `bash: /tmp/x.sh: Нет такого файла или каталога`).

paramiko снимает обе проблемы разом: cmd.exe вообще не участвует, команда уходит
одним аргументом, кириллица и кавычки сохраняются.

## Установка

```bash
uv venv C:/tmp/diagvenv
uv pip install --python C:/tmp/diagvenv paramiko
```

Запускать venv-python по НАТИВНОМУ windows-пути (`/c/tmp/...` MSYS не разрешает).

## Минимальный шаблон

```python
import paramiko

def run(host, port, user, cmd, key=None, password=None, timeout=15):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, port=port, username=user, key_filename=key,
              password=password, timeout=timeout,
              allow_agent=False, look_for_keys=False)
    try:
        _, out, err = c.exec_command(cmd, timeout=timeout)
        return (out.read().decode("utf-8", "replace").strip(),
                err.read().decode("utf-8", "replace").strip())
    finally:
        c.close()
```

- `allow_agent=False` + `look_for_keys=False` обязательны при наличии ssh-agent с
  ключами от других хостов: иначе paramiko подставит не тот ключ и даст отказ по
  логу, где пароль верный.
- Таймаут на `connect` И на каждую `exec_command`. Без них скрипт висит до вечера
  на одном мёртвом хосте.
- Пароль в теле скрипта допустим только для одноразовой диагностики стенда.
  Постоянные скрипты — ключ + секрет в переменной окружения, иначе код уедет в репозиторий.

## За стендом через бастион: direct-tcpip

`paramiko.ProxyCommand` с системным `ssh -W` на Windows падает `not a socket`.
Работает чистый канал Python:

```python
bastion = paramiko.SSHClient()
bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
bastion.connect("bastion-host", username="astra",
                key_filename="C:/Users/<u>/.ssh/id_ed25519")
chan = bastion.get_transport().open_channel("direct-tcpip",
                                             ("<target-ip>", 22), ("127.0.0.1", 0))
target = paramiko.SSHClient()
target.set_missing_host_key_policy(paramiko.AutoAddPolicy())
target.connect("<target-ip>", username="admin", password="[REDACTED]", sock=chan)
```

- Путь к ключу — нативный windows-стилем, прямым слэшем. Форму `/c/Users/...`
  paramiko не разрешает: ошибка выглядит как «файл не найден», хотя файл есть.
- Объект `paramiko.Transport()` требует аргумент (socket). Проверять наличие
  `open_channel` надо на реальном инстансе, а не на классе: `hasattr(paramiko.Transport(), ...)`
  падает `TypeError: Transport.__init__() missing 1 required`.

## Версии

- **paramiko 5.x удалил `py3compat`.** Скрипты с `paramiko.py3compat.u()` /
  `encodecmd()` падают `AttributeError` там, где раньше проходили. Экранирование —
  f-строки и `shlex.quote()`, декодирование байтов — `decode("utf-8", "replace")`.
- На 5.0.0 у `SSHClient` есть `get_transport()`; отдельного `invoke_transport`
  нет — не полагаться на него.

## Две формы, путать нельзя

1. **Скрипт на своей машине.** Берёт порт локального туннеля и ходит в
   `127.0.0.1:<port>`. Туннель поднимается один раз отдельно (cmd.exe + системный
   OpenSSH `ssh -f -N -L`), скрипт только забирает состояние.
2. **Скрипт на бастионе.** Кладётся на сам бастион и ходит на стенды по внутренним
   адресам. Там пароль в коде менее опасен (хост под контролем) и уместен state-файл
   с предыдущим замером: «залипло» должно означать «не двигается N замеров подряд»,
   а не «один раз показало то же значение».

## Проверка перед боевым прогоном

- Только чтение: `systemctl is-active`, `tail`, `SELECT`. `restart`/запись в базу —
  отдельная операция с отдельным подтверждением.
- Сухой прогон: вывести список команд, не исполняя.
- Пароль не в строке команды: `echo "PASS" | sudo -S` светит пароль в истории
  процессов и ловится защитой агента как подбор пароля. Права — через `sudo -n`.
