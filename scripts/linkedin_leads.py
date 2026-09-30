#!/usr/bin/env python3
"""Лиды из LinkedIn: компании Армении со страницей на LinkedIn, у которых нет сайта или он устарел.

data/linkedin/companies.csv пополняет Claude: ищет страницы компаний LinkedIn через поисковик
(сам LinkedIn не открывает и не парсит), для каждой ищет её собственный сайт.
Этот скрипт проверяет найденные сайты тем же site_audit.py (кэш общий с data/audit_cache.csv),
подтягивает телефон/почту из data/businesses.csv (OSM) по названию и пишет data/linkedin/leads.csv.
"""
import csv, datetime, os, re, sys
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from site_audit import audit, fetch, dns_status

SRC = "data/linkedin/companies.csv"
OUT = "data/linkedin/leads.csv"
CACHE = "data/audit_cache.csv"
TODAY = datetime.date.today()
CACHE_FIELDS = ["website", "score", "problems", "final_url", "checked"]


def norm(s):
    s = s.lower()
    s = re.sub(r"\b(llc|ltd|cjsc|ojsc|ooo|сс|ооо|restaurant|hotel|cafe|clinic|salon|group|armenia|yerevan)\b", " ", s)
    return re.sub(r"[^0-9a-zа-яա-ֆ]+", "", s)


STOP = {"llc", "ltd", "cjsc", "ojsc", "the", "and", "armenia", "yerevan", "hotel", "restaurant", "cafe", "clinic", "center", "centre", "group", "company", "medical", "dental", "salon", "studio"}


SKIP_CATEGORIES = {"маркетинг", "IT", "дизайн"}
SKIP_WORDS = re.compile(r"\b(ai|a\.i\.|artificial intelligence|machine learning|ml|software|web|website|digital\w*|it|tech|code|coding|developers?|software development|web development|programming|smm|marketing|media|saas|hosting)\b", re.I)


def guesses(c):
    """Возможные домены компании по slug LinkedIn и названию."""
    slug = c["linkedin"].rstrip("/").rsplit("/", 1)[-1].lower()
    words = [w for w in re.findall(r"[a-z0-9]+", c["name"].lower()) if w not in STOP]
    bases = {slug, slug.replace("-", ""), "".join(words), "-".join(words)}
    bases = {b for b in bases if len(b) >= 4 and not b.isdigit()}
    return [f"{b}.am" for b in sorted(bases)]  # .com по названию слишком часто чужой


def find_site(c):
    """Ищем сайт перебором доменов: страница должна упоминать название компании."""
    words = [w for w in re.findall(r"[a-z0-9]+", c["name"].lower()) if w not in STOP and len(w) >= 4]
    for host in guesses(c):
        for scheme in ("https://", "http://"):
            try:
                final, status, html, secs, size = fetch(scheme + host, timeout=10)
            except Exception:
                if scheme == "http://" and host.endswith(".am") and dns_status(host) == "alive":
                    return host  # домен живой, но сервер проверки не открыл: пусть аудит решает, не считаем «сайта нет»
                continue
            low = html.lower()
            if host not in (urlparse(final).hostname or ""):
                break  # увело на другой домен (парковка, продажа домена)
            if words and all(w in low for w in words) and not re.search(r"domain (is )?for sale|parked|buy this domain", low):
                return final
            break
    return ""


def main():
    with open(SRC, encoding="utf-8") as fh:
        comp = list(csv.DictReader(fh))
    look = [c for c in comp if not c["website"] and c["status"] in ("unknown", "") and not c.get("guessed")]
    if look:
        print(f"Ищу сайты перебором доменов: {len(look)}")
        with ThreadPoolExecutor(16) as ex:
            for c, site in zip(look, ex.map(find_site, look)):
                c["website"], c["guessed"] = site, TODAY.isoformat()
                if site:
                    c["status"], c["evidence"] = "own_site", "нашёлся по домену"
        with open(SRC, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, list(comp[0].keys()))
            w.writeheader()
            w.writerows(comp)
    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as fh:
            cache = {r["website"]: r for r in csv.DictReader(fh)}
    fresh = lambda r: (TODAY - datetime.date.fromisoformat(r["checked"])).days < 30
    todo = sorted({c["website"] for c in comp if c["website"] and not (c["website"] in cache and fresh(cache[c["website"]]))})
    print(f"Компаний с LinkedIn: {len(comp)}, проверяю сайтов: {len(todo)}")

    def run(url):
        try:
            s, p, f = audit(url)
        except Exception as e:
            s, p, f = None, [f"ошибка проверки ({type(e).__name__})"], url
        return {"website": url, "score": "" if s is None else s, "problems": "; ".join(p), "final_url": f, "checked": TODAY.isoformat()}

    with ThreadPoolExecutor(16) as ex:
        for r in ex.map(run, todo):
            cache[r["website"]] = r
    with open(CACHE, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, CACHE_FIELDS)
        w.writeheader()
        w.writerows(sorted(cache.values(), key=lambda r: r["website"]))

    osm = {}
    if os.path.exists("data/businesses.csv"):
        with open("data/businesses.csv", encoding="utf-8") as fh:
            for b in csv.DictReader(fh):
                for n in (b["name"], b["name_en"], b["name_ru"]):
                    if n and len(norm(n)) >= 4:
                        osm.setdefault(norm(n), b)

    leads = []
    for c in comp:
        if c["category"] in SKIP_CATEGORIES or SKIP_WORDS.search(c["name"]):
            continue  # сами сделают себе сайт (AI, IT, веб, маркетинг) — не клиенты
        b = osm.get(norm(c["name"]), {})
        row = {k: c[k] for k in ("name", "category", "city", "linkedin", "website", "socials")}
        row.update(phone=b.get("phone", ""), email=b.get("email", ""), instagram=b.get("instagram", ""))
        if not c["website"]:
            if c["status"] == "no_site":
                row.update(lead_type="нет сайта", score=100, problems="в поиске только LinkedIn, соцсети и каталоги")
            else:
                row.update(lead_type="сайт не найден", score=90, problems="сайт не нашёлся ни поиском, ни по домену: проверить поле Website на LinkedIn")
        else:
            a = cache.get(c["website"])
            if not a or a["score"] == "" or int(a["score"]) < 40:
                continue
            kind = "нет сайта" if "соцсеть" in a["problems"] else "устаревший сайт"
            row.update(lead_type=kind, score=a["score"], problems=a["problems"])
        leads.append(row)
    order = {"устаревший сайт": 0, "нет сайта": 1, "сайт не найден": 2}
    leads.sort(key=lambda r: (order[r["lead_type"]], -int(r["score"]), r["category"], r["name"]))
    fields = ["name", "category", "city", "linkedin", "website", "socials", "phone", "email", "instagram", "lead_type", "score", "problems"]
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fields)
        w.writeheader()
        w.writerows(leads)
    from collections import Counter
    print(f"LinkedIn-лидов: {len(leads)}", dict(Counter(r["lead_type"] for r in leads)))


if __name__ == "__main__":
    main()
