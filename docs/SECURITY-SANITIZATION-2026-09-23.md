# Санитизация channel-materials - 23.09.2026

## Что нашли (аудит /cursor: security-audit + public-repo-history-sanitization)

GitHub (NikolayGusev-astra) и GitFlic (manve-sulimo2) - ПУБЛИЧНЫЕ (проверено без авторизации).

КРИТИЧНО (в истории, удалены из дерева в 9f70d40):
- 2026-09-20-jev-decision-models/mails.json.partial - 49 МБ, 1441 email, 1809 телефонов,
  подпись владельца (N.gusev@sk-gs.ru, 89221682440) в цитатах писем 2010 г.
- mails_10k.json - 19.8 МБ, 795 email реальных людей
- labeled/autolabel.jsonl - 14.3 МБ, 251 email, та же переписка

СРЕДНЕ (живое дерево): C:\Users\n.gusev в 6 файлах (send_tg.py, quant_duel.py,
quant_final.py, test_granite_dispatch.py, e2e-step37-transcript.md, edit_tg.py).

ЧИСТО: hermes-site (приватный bare на сервере, 22 коммита - 0 секретов),
скиллы writer/draw (секреты только в замаскированных примерах), comfyui-скрипты,
admin.env (600 root, deploy/ не в git), админка 127.0.0.1:3100 (наружу 404).

## Что сделано

1. DRP: git bundle create channel-materials-backup-20260923.bundle --all (127 МБ, verified)
2. git filter-repo --invert-paths (3 файла) + --replace-text:
   n.gusev пути (4 написания) -> redacted; личный email -> redacted@example.org;
   личный телефон -> 70000000000
3. Верификация ДО пуша: все грепы = 0, 72 коммита сохранились, jev в дереве цел (21 файл)
4. force-push: GitHub - сразу; GitFlic - pack>100MB rejected, обошло пушем чанками
   по 20 коммитов (4 chunk'а)
5. Пост-чек: HEAD обоих зеркал = ddd4eac0 = локальный; raw датасета на новом HEAD 404,
   на старом SHA тоже 404; quant_duel.py на GitHub отдаёт redacted-путь

## Остаточные риски

- Хостинги держат старые объекты до gc (прямые SHA-ссылки живут ~2 недели).
  Прямых ссылок на датасеты из постов/README не найдено - индексации не было.
- Бэкап-бандл C:/Work/Assist/channel-materials-backup-20260923.bundle
  СОДЕРЖИТ старую историю с ПДн. Удалить после стабилизации (решение владельца).

## Изменённые SHA

Все SHA переписаны: e3d9611 -> ddd4eac (HEAD), 8542d21 -> иные.
Правило на будущее: сырые датасеты/транскрипты - НЕ в публичный репо
(скилл public-repo-history-sanitization, writer v2.2.0).
