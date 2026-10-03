#!/usr/bin/env bash
# Установка с нуля: LaTeX для объясняющих видео на Manim.
# Проверено на Windows 11 + git-bash, scoop, без прав админа, 2026-10-03.
set -euo pipefail

echo "==> 1/4 Проверка scoop"
command -v scoop >/dev/null || { echo "scoop не найден. Установи его или ставь MiKTeX через winget от админа."; exit 1; }

echo "==> 2/4 Установка MiKTeX (portable, без UAC)"
if command -v pdflatex >/dev/null; then
  echo "    pdflatex уже в PATH, установку пропускаем"
else
  scoop install miktex
fi

echo "==> 3/4 Автоустановка недостающих пакетов"
# Без этого MiKTeX откроет диалоговое окно на каждый пакет и агент зависнет.
# Каноничная форма `miktex --set-default-package-install=1` на этой машине
# зависала дольше 3 минут; initexmf отрабатывает за секунду.
initexmf --set-config-value=[MPM]AutoInstall=1

INI="$HOME/scoop/persist/miktex/texmfs/config/miktex/config/miktex.ini"
echo "    в конфиге: $(grep -i AutoInstall "$INI" 2>/dev/null || echo 'параметр не найден')"

echo "==> 4/4 Проверка через штатный диагност Manim"
PY="<local-path>ppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
if [ ! -x "$PY" ]; then
  echo "    venv hermes не найден по пути $PY - пропускаю проверку manim"
  exit 0
fi
"$PY" -m manim checkhealth <<< "n" || true
echo
echo "Готово. Ожидаемый вывод: latex PASSED и dvisvgm PASSED."
echo "Проверить формулой:"
echo "  MathTex(r'e^{i\\pi} + 1 = 0')"