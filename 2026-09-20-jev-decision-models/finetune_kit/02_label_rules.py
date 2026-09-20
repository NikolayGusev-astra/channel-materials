"""Шаг 2: слабая разметка правилами по доменам.
Запуск: python 02_label_rules.py --mails mails.json --out mails_rules.json
Свой список доменов отредактируйте под свой ящик (NOISE = шум, ACTION = важное).
"""
import json, argparse

NOISE = {
    "github.com", "news.ozon.ru", "sender.ozon.ru", "deals.biglion.ru",
    "zerocoder.ru", "discover.pinterest.com", "mail.timepad.ru",
    "substack.com", "updates.typesafe.ai", "sub.stoloto.ru",
    "smartlab.ru", "smart-lab.ru",
}
ACTION = {"gosuslugi.ru", "hostkey.ru"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mails", default="mails.json")
    ap.add_argument("--out", default="mails_rules.json")
    args = ap.parse_args()
    mails = json.load(open(args.mails, encoding="utf-8"))
    labeled, rules = [], 0
    for m in mails:
        lab = None
        if m["from_domain"] in NOISE: lab, rules = 0, rules + 1
        elif m["from_domain"] in ACTION: lab, rules = 1, rules + 1
        labeled.append({**m, "label": lab, "source": "rule" if lab is not None else None})
    json.dump(labeled, open(args.out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(labeled)} писем, правилами закрыто {rules} ({rules*100//len(labeled)}%)")

if __name__ == "__main__":
    main()
