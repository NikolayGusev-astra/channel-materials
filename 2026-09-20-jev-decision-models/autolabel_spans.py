# -*- coding: utf-8 -*-
"""Автолейбл почтового корпуса спанами через composite-детектор PII Guard.
Вход: mails_10k.json  Выход: labeled/autolabel.jsonl (BIO-спаны с оффсетами).
Каждое письмо: subject + from_domain (как служебные поля) + body = текст для детекции.
Спаны считаются в координатах текста письма (subject\\n\\nbody), оффсеты абсолютные.
"""
import io, json, os, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r'C:/Work/pii-guard')

from pii_guard.detector.regex_detector import RegexDetector
from pii_guard.detector.transformer_detector import TransformerDetector

IN = os.path.join(ROOT, 'mails_10k.json')
OUT = os.path.join(ROOT, 'labeled', 'autolabel.jsonl')
STATS = os.path.join(ROOT, 'labeled', 'autolabel_stats.json')

def merge_spans(regex_spans, ml_spans):
    """Regex имеет приоритет; ML-спаны добавляются если не пересекаются с уже взятыми."""
    taken = []
    for s in sorted(regex_spans, key=lambda x: (x.start, -(x.end - x.start))):
        if not any(s.start < t.end and t.start < s.end for t in taken):
            taken.append(s)
    for s in sorted(ml_spans, key=lambda x: (x.start, -(x.end - x.start))):
        if not any(s.start < t.end and t.start < s.end for t in taken):
            taken.append(s)
    return sorted(taken, key=lambda x: x.start)

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    mails = json.load(io.open(IN, encoding='utf-8'))
    print(f"loaded {len(mails)} mails", flush=True)
    rd = RegexDetector()
    td = TransformerDetector(model_path=r'C:/Work/pii-guard/model_prod_lite')
    print("detectors ready", flush=True)

    stats = {"mails": len(mails), "with_spans": 0, "total_spans": 0, "by_type": {}}
    t0 = time.time()
    fout = io.open(OUT, 'w', encoding='utf-8')
    for i, m in enumerate(mails, 1):
        subject = (m.get('subject') or '').strip()
        body = (m.get('body_snippet') or '').strip()
        # подпись/тема важны для детекции; домен отправителя — контекст, не текст
        text = (subject + "\n\n" + body) if subject else body
        prefix = len(subject) + 2 if subject else 0
        spans_out = []
        if text.strip():
            try:
                r_spans = rd.detect(text)
            except Exception:
                r_spans = []
            try:
                ml_spans = td.detect(text)
            except Exception:
                ml_spans = []
            for s in merge_spans(r_spans, ml_spans):
                spans_out.append({
                    "start": s.start, "end": s.end,
                    "type": s.entity_type.value, "text": s.text,
                })
                stats["by_type"][s.entity_type.value] = stats["by_type"].get(s.entity_type.value, 0) + 1
        if spans_out:
            stats["with_spans"] += 1
            stats["total_spans"] += len(spans_out)
        fout.write(json.dumps({
            "id": i - 1,
            "subject": subject,
            "from_domain": m.get('from_domain') or '',
            "date": m.get('date') or '',
            "text": text,
            "spans": spans_out,
            "autolabel": True,
        }, ensure_ascii=False) + "\n")
        if i % 250 == 0:
            fout.flush()
            rate = i / (time.time() - t0)
            eta = (len(mails) - i) / max(rate, 0.1)
            print(f"{i}/{len(mails)} spans={stats['total_spans']} rate={rate:.1f}/s eta={eta:.0f}s", flush=True)
    fout.close()
    stats["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(stats, io.open(STATS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print("DONE", json.dumps(stats, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
