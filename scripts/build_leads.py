#!/usr/bin/env python3
"""Аудит сайтов из data/businesses.csv и сборка списка лидов в data/leads.csv."""
import csv, datetime, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from site_audit import audit

CACHE = "data/audit_cache.csv"      # сайт -> оценка; перепроверяем раз в 30 дней
MAX_NEW = int(os.environ.get("MAX_NEW_AUDITS", "400"))
TODAY = datetime.date.today()


def load_cache():
    if not os.path.exists(CACHE):
        return {}
    with open(CACHE, encoding="utf-8") as fh:
        return {r["website"]: r for r in csv.DictReader(fh)}


def main():
    with open("data/businesses.csv", encoding="utf-8") as fh:
        biz = list(csv.DictReader(fh))
    cache = load_cache()
    fresh = lambda r: (TODAY - datetime.date.fromisoformat(r["checked"])).days < 30
    todo = sorted({b["website"] for b in biz if b["website"] and not (b["website"] in cache and fresh(cache[b["website"]]))})[:MAX_NEW]
    print(f"Сайтов всего: {len({b['website'] for b in biz if b['website']})}, проверяю сейчас: {len(todo)}")

    def run(url):
        try:
            s, p, f = audit(url)
        except Exception as e:
            s, p, f = 100, [f"ошибка проверки ({type(e).__name__})"], url
        return {"website": url, "score": s, "problems": "; ".join(p), "final_url": f, "checked": TODAY.isoformat()}

    with ThreadPoolExecutor(16) as ex:
        for r in ex.map(run, todo):
            cache[r["website"]] = r
    with open(CACHE, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["website", "score", "problems", "final_url", "checked"])
        w.writeheader()
        w.writerows(sorted(cache.values(), key=lambda r: r["website"]))

    leads = []
    for b in biz:
        contact = b["phone"] or b["instagram"] or b["telegram"] or b["email"] or b["facebook"]
        if not b["website"]:
            if not contact:
                continue
            leads.append({**b, "lead_type": "нет сайта", "score": 100, "problems": "сайта нет"})
        elif b["website"] in cache and int(cache[b["website"]]["score"]) >= 40:
            a = cache[b["website"]]
            leads.append({**b, "lead_type": "устаревший сайт", "score": a["score"], "problems": a["problems"]})
    prio = {"отель": 0, "гостевой дом": 0, "ресторан": 1, "кафе": 1, "супермаркет": 2}
    leads.sort(key=lambda r: (prio.get(r["category"], 3), -int(r["score"]), r["name"]))
    fields = list(biz[0].keys()) + ["lead_type", "score", "problems"]
    with open("data/leads.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fields)
        w.writeheader()
        w.writerows(leads)
    n_old = sum(r["lead_type"] == "устаревший сайт" for r in leads)
    print(f"Лидов: {len(leads)} (устаревший сайт: {n_old}, нет сайта: {len(leads) - n_old})")


if __name__ == "__main__":
    main()
