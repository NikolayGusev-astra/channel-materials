#!/usr/bin/env bash
# Needle-middle на muse-spark-1.3-contributor-free через opencode CLI + прокси
export http_proxy='http://127.0.0.1:12334'
export https_proxy='http://127.0.0.1:12334'
export no_proxy='127.0.0.1,localhost'
cd "C:\Work\llm-wiki\wiki\content\статьи\_dossier-raw"
for SEED in 71 72 73 74; do
  echo "=== muse seed $SEED ==="
  timeout 600 opencode run -m opencode/muse-spark-1.3-contributor-free -f "needle_files/needle_$SEED.txt" -- "Найди в прикреплённом файле строку со словом 'заметка' о коде доступа. Ответь ровно одной строкой: только значение кода." 2>&1 | tail -2
done
echo "MUSE NEEDLES DONE"
