#!/bin/bash
# Быстрая проверка кодбука EXL3-релиза перед закачкой.
# Использование: ./check-codebook.sh <repo> [branch]
# Пример: ./check-codebook.sh ultimatechris/Ornith-1.5-35B-A3B-EXL3-4bpw main
REPO="$1"
BRANCH="${2:-main}"
if [ -z "$REPO" ]; then
  echo "Использование: $0 <repo> [branch]"
  exit 1
fi
CB=$(curl -sL --max-time 20 "https://huggingface.co/$REPO/resolve/$BRANCH/quantization_config.json" -r 0-4000 | grep -o '"codebook": *"[^"]*"' | head -1)
BITS=$(curl -sL --max-time 20 "https://huggingface.co/$REPO/resolve/$BRANCH/quantization_config.json" -r 0-4000 | grep -o '"bits": *[0-9.]*' | head -1)
echo "repo:   $REPO ($BRANCH)"
echo "кодбук: ${CB:-НЕ НАЙДЕН}"
echo "биты:   ${BITS:-?}"
case "$CB" in
  *mul1*) echo "вывод:  mul1 - CPU-offload ExLlamaV3 будет работать" ;;
  *mcg*)  echo "вывод:  mcg - CPU-offload БУДЕТ МОЛЧА ПРОПУЩЕН (эксперты останутся на GPU)" ;;
  *)      echo "вывод:  кодбук не определён - проверьте quantization_config.json вручную" ;;
esac
