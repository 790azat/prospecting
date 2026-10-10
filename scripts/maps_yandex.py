#!/usr/bin/env python3
"""Бизнесы Еревана из Яндекс Карт (публичная страница поиска, без ключа) -> data/maps/yandex.csv.

Страница https://yandex.ru/maps/<город>/search/<запрос>/ отдаёт до 25 организаций в JSON (state-view)
вместе с телефонами, сайтами и соцсетями. Чтобы обойти лимит выдачи, город режется на сетку
небольших квадратов (параметры ll и z) и по каждой нише листаются страницы.
Запуск: python3 scripts/maps_yandex.py  (переменные MAPS_CITY, MAPS_NICHES, MAPS_PAGES, MAPS_STEP)
"""
import csv, gzip, json, os, random, re, sys, time, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
OUT = os.environ.get("MAPS_OUT", "data/maps/yandex.csv")

# город: (id региона в Яндексе, slug, (юг, запад, север, восток))
CITIES = {
    "Ереван": (10262, "yerevan", (40.12, 44.42, 40.24, 44.60)),
    "Гюмри": (10261, "gyumri", (40.76, 43.80, 40.82, 43.87)),
    "Дилижан": (10264, "dilijan", (40.72, 44.83, 40.76, 44.90)),
}

# запрос в Яндексе -> ниша по-русски (как в мастер-списке)
NICHES = {
    "ресторан": "ресторан", "кафе": "кафе", "кофейня": "кофейня", "бар": "бар",
    "гостиница": "отель", "гостевой дом": "гостевой дом", "хостел": "хостел",
    "стоматология": "стоматология", "медицинский центр": "клиника",
    "салон красоты": "салон красоты", "парикмахерская": "парикмахерская", "ногтевая студия": "салон красоты",
    "автосервис": "автосервис", "фитнес-клуб": "фитнес", "пекарня": "пекарня", "кондитерская": "кондитерская",
    "цветы": "цветы", "ветеринарная клиника": "ветклиника", "учебный центр": "учебный центр",
    "мебель на заказ": "мебель", "магазин одежды": "магазин одежды", "фотостудия": "фотостудия",
}

FIELDS = ["yandex_id", "name", "category", "niche", "city", "address", "phone", "website", "instagram",
          "facebook", "telegram", "whatsapp", "viber", "other_social", "rating", "reviews", "status",
          "hours", "lat", "lon", "link", "query"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ru,en;q=0.7",
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=40) as r:
        b = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            b = gzip.decompress(b)
    return b.decode("utf-8", "replace")


def search(region, slug, q, ll=None, z=None, page=1):
    params = {}
    if ll:
        params["ll"], params["z"] = ll, z
    if page > 1:
        params["page"] = page
    url = f"https://yandex.ru/maps/{region}/{slug}/search/{urllib.parse.quote(q)}/"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    t = get(url)
    m = re.search(r'<script type="application/json" class="state-view">(.*?)</script>', t, re.S)
    if not m:
        raise RuntimeError("captcha" if "captcha" in t.lower() else "нет данных")
    res = json.loads(m.group(1))["stack"][0].get("results") or {}
    return [i for i in res.get("items", []) if i.get("type") == "business"], res.get("totalResultCount", 0)


def clean_url(u):
    u = re.sub(r"[?&](yclid|utm_[a-z]+)=[^&]*", "", u)
    return u.rstrip("?&")


def row(it, niche, city, q):
    soc = {}
    other = []
    for s in it.get("socialLinks") or []:
        t, h = s.get("type", ""), s.get("href", "")
        if t in ("instagram", "facebook", "telegram", "whatsapp", "viber") and t not in soc:
            soc[t] = h
        else:
            other.append(h)
    lon, lat = (it.get("coordinates") or [None, None])[:2]
    rd = it.get("ratingData") or {}
    return {
        "yandex_id": it.get("id", ""), "name": it.get("title", ""),
        "category": ", ".join(c.get("name", "") for c in it.get("categories") or []),
        "niche": niche, "city": city, "address": it.get("address", ""),
        "phone": "; ".join(p.get("number", "") for p in it.get("phones") or []),
        "website": " ".join(clean_url(u) for u in it.get("urls") or []),
        "instagram": soc.get("instagram", ""), "facebook": soc.get("facebook", ""),
        "telegram": soc.get("telegram", ""), "whatsapp": soc.get("whatsapp", ""), "viber": soc.get("viber", ""),
        "other_social": " ".join(other), "rating": rd.get("ratingValue", ""), "reviews": rd.get("reviewCount", ""),
        "status": it.get("status", ""), "hours": it.get("workingTimeText", ""), "lat": lat, "lon": lon,
        "link": f"https://yandex.ru/maps/org/{it.get('seoname', 'org')}/{it.get('id', '')}/", "query": q,
    }


def grid(bbox, step):
    s, w, n, e = bbox
    y = s + step / 2
    while y < n:
        x = w + step / 2
        while x < e:
            yield f"{x:.4f},{y:.4f}"
            x += step
        y += step


def main():
    cities = os.environ.get("MAPS_CITY", "Ереван").split(",")
    niches = [n for n in os.environ.get("MAPS_NICHES", ",".join(NICHES)).split(",") if n]
    pages = int(os.environ.get("MAPS_PAGES", "2"))          # страниц на квадрат сетки
    top_pages = int(os.environ.get("MAPS_TOP_PAGES", "20"))  # страниц общего поиска по городу
    step = float(os.environ.get("MAPS_STEP", "0.03"))
    zoom = os.environ.get("MAPS_Z", "15")
    found = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            found = {r["yandex_id"]: r for r in csv.DictReader(fh)}
    print(f"Уже в базе: {len(found)}")
    errors = 0
    for city in cities:
        region, slug, bbox = CITIES[city]
        cells = list(grid(bbox, step))
        for q in niches:
            before = len(found)
            for ll in [None] + cells:
                for page in range(1, (top_pages if ll is None else pages) + 1):
                    try:
                        items, total = search(region, slug, q, ll, zoom, page)
                        errors = 0
                    except Exception as e:
                        errors += 1
                        print(f"  ! {q} {ll} p{page}: {e}")
                        if errors >= 8:
                            print("Слишком много ошибок подряд (капча?), сохраняю что есть")
                            return save(found)
                        time.sleep(20)
                        break
                    for it in items:
                        if it.get("id") and it["id"] not in found:
                            found[it["id"]] = row(it, NICHES.get(q, q), city, q)
                    time.sleep(random.uniform(1.5, 3.0))
                    if len(items) < 25:
                        break
            print(f"{city} / {q}: +{len(found) - before} (всего {len(found)})", flush=True)
            save(found)
    save(found)


def save(found):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(found.values(), key=lambda r: (r["niche"], r["name"])):
            w.writerow({k: r.get(k, "") for k in FIELDS})


if __name__ == "__main__":
    main()
