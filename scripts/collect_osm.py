#!/usr/bin/env python3
"""Собирает бизнесы Армении из OpenStreetMap (Overpass API) в data/businesses.csv."""
import csv, json, os, sys, time, urllib.parse, urllib.request

# Небольшие прямоугольники вокруг городов: запросы по bbox намного быстрее, чем по всей стране.
# (юг, запад, север, восток)
CITIES = {
    "Ереван": (40.05, 44.36, 40.26, 44.64),
    "Гюмри": (40.76, 43.78, 40.82, 43.88),
    "Ванадзор": (40.79, 44.44, 40.84, 44.53),
    "Дилижан": (40.72, 44.82, 40.77, 44.91),
    "Цахкадзор": (40.52, 44.69, 40.55, 44.74),
    "Севан": (40.52, 44.92, 40.60, 45.05),
    "Джермук": (39.82, 45.65, 39.86, 45.70),
    "Горис": (39.49, 46.32, 39.53, 46.36),
    "Ехегнадзор": (39.75, 45.31, 39.78, 45.36),
}
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# (ключ, значение, категория по-русски)
KINDS = [
    ("tourism", "hotel", "отель"), ("tourism", "guest_house", "гостевой дом"),
    ("tourism", "hostel", "хостел"), ("tourism", "motel", "мотель"),
    ("tourism", "apartment", "апартаменты"),
    ("amenity", "restaurant", "ресторан"), ("amenity", "cafe", "кафе"),
    ("amenity", "bar", "бар"), ("amenity", "pub", "паб"), ("amenity", "fast_food", "фастфуд"),
    ("shop", "supermarket", "супермаркет"),
    ("amenity", "dentist", "стоматология"), ("amenity", "clinic", "клиника"),
    ("shop", "beauty", "салон красоты"), ("shop", "hairdresser", "парикмахерская"),
    ("shop", "car_repair", "автосервис"), ("craft", "car_repair", "автосервис"),
    ("office", "travel_agent", "турагентство"), ("shop", "travel_agency", "турагентство"),
]
FIELDS = ["osm_id", "name", "name_en", "name_ru", "category", "city", "street", "phone",
          "website", "instagram", "facebook", "telegram", "email", "lat", "lon"]


def query(bbox):
    b = ",".join(map(str, bbox))
    parts = "".join(f'nwr["{k}"="{v}"]["name"]({b});' for k, v, _ in KINDS)
    return f'[out:json][timeout:90];({parts});out center tags;'


def fetch(bbox):
    """Один небольшой запрос; пустой ответ с remark считаем ошибкой и пробуем другое зеркало."""
    data = urllib.parse.urlencode({"data": query(bbox)}).encode()
    last = None
    for attempt in range(2):
        for url in ENDPOINTS:
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "evnweb-prospecting/1.0"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    js = json.load(r)
                if js.get("remark") and not js.get("elements"):
                    raise RuntimeError(js["remark"][:200])
                return js["elements"]
            except Exception as e:
                last = e
                print(f"  {url}: {e}", file=sys.stderr)
        time.sleep(10)
    raise SystemExit(f"Overpass недоступен: {last}")


def first(t, *keys):
    for k in keys:
        if t.get(k):
            return t[k].split(";")[0].strip()
    return ""


def main():
    rows = {}
    elements = []
    started = time.time()
    for city, bbox in CITIES.items():
        if time.time() - started > 1200:
            print(f"{city}: пропущен, вышло время", flush=True)
            continue
        try:
            got = fetch(bbox)
        except SystemExit as e:
            print(f"{city}: пропущен ({e})", flush=True)
            continue
        print(f"{city}: {len(got)}", flush=True)
        for el in got:
            el["_city"] = city
        elements += got
        time.sleep(3)
    for el in elements:
        t = el.get("tags", {})
        cat = next((c for k, v, c in KINDS if t.get(k) == v), "")
        c = el.get("center", el)
        rows[f'{el["type"]}/{el["id"]}'] = {
            "osm_id": f'{el["type"]}/{el["id"]}',
            "name": t.get("name", ""), "name_en": t.get("name:en", ""), "name_ru": t.get("name:ru", ""),
            "category": cat,
            "city": el["_city"],
            "street": " ".join(x for x in [t.get("addr:street", ""), t.get("addr:housenumber", "")] if x),
            "phone": first(t, "phone", "contact:phone", "mobile", "contact:mobile"),
            "website": first(t, "website", "contact:website", "url"),
            "instagram": first(t, "contact:instagram", "instagram"),
            "facebook": first(t, "contact:facebook", "facebook"),
            "telegram": first(t, "contact:telegram", "telegram"),
            "email": first(t, "email", "contact:email"),
            "lat": c.get("lat", ""), "lon": c.get("lon", ""),
        }
    if not rows:
        raise SystemExit("Overpass вернул 0 бизнесов, старые данные не трогаю")
    os.makedirs("data", exist_ok=True)
    with open("data/businesses.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: (r["category"], r["name"])))
    print(f"Собрано {len(rows)} бизнесов")


if __name__ == "__main__":
    main()
