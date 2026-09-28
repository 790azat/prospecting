#!/usr/bin/env python3
"""Собирает бизнесы Армении из OpenStreetMap (Overpass API) в data/businesses.csv."""
import csv, json, os, sys, time, urllib.parse, urllib.request

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

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


def query():
    parts = "".join(f'nwr["{k}"="{v}"]["name"](area.am);' for k, v, _ in KINDS)
    return f'[out:json][timeout:180];area["ISO3166-1"="AM"][admin_level=2]->.am;({parts});out center tags;'


def fetch():
    data = urllib.parse.urlencode({"data": query()}).encode()
    last = None
    for attempt in range(3):
        for url in ENDPOINTS:
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "evnweb-prospecting/1.0"})
                with urllib.request.urlopen(req, timeout=240) as r:
                    return json.load(r)["elements"]
            except Exception as e:
                last = e
                print(f"{url}: {e}", file=sys.stderr)
        time.sleep(30)
    raise SystemExit(f"Overpass недоступен: {last}")


def first(t, *keys):
    for k in keys:
        if t.get(k):
            return t[k].split(";")[0].strip()
    return ""


def main():
    rows = {}
    for el in fetch():
        t = el.get("tags", {})
        cat = next((c for k, v, c in KINDS if t.get(k) == v), "")
        c = el.get("center", el)
        rows[f'{el["type"]}/{el["id"]}'] = {
            "osm_id": f'{el["type"]}/{el["id"]}',
            "name": t.get("name", ""), "name_en": t.get("name:en", ""), "name_ru": t.get("name:ru", ""),
            "category": cat,
            "city": first(t, "addr:city", "addr:place"),
            "street": " ".join(x for x in [t.get("addr:street", ""), t.get("addr:housenumber", "")] if x),
            "phone": first(t, "phone", "contact:phone", "mobile", "contact:mobile"),
            "website": first(t, "website", "contact:website", "url"),
            "instagram": first(t, "contact:instagram", "instagram"),
            "facebook": first(t, "contact:facebook", "facebook"),
            "telegram": first(t, "contact:telegram", "telegram"),
            "email": first(t, "email", "contact:email"),
            "lat": c.get("lat", ""), "lon": c.get("lon", ""),
        }
    os.makedirs("data", exist_ok=True)
    with open("data/businesses.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: (r["category"], r["name"])))
    print(f"Собрано {len(rows)} бизнесов")


if __name__ == "__main__":
    main()
