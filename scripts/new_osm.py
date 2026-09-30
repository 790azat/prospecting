#!/usr/bin/env python3
"""Новые бизнесы Армении без сайта: объекты, которые появились в OpenStreetMap недавно.

Дата появления: у версии 1 это её timestamp; у изменённых объектов оцениваем по id
(id в OSM растут со временем) по соседним объектам версии 1. Результат: data/new/novye.csv.
"""
import bisect, csv, datetime, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from collect_osm import CITIES as BASE_CITIES, ENDPOINTS, first
import json, urllib.parse, urllib.request

SINCE = os.environ.get("SINCE", "2025-10-01")
CITIES = dict(BASE_CITIES, **{
    "Абовян": (40.26, 44.60, 40.29, 44.65),
    "Эчмиадзин": (40.15, 44.27, 40.19, 44.32),
    "Раздан": (40.48, 44.73, 40.52, 44.79),
    "Армавир": (40.14, 44.02, 40.17, 44.06),
    "Арташат": (39.94, 44.53, 39.97, 44.57),
    "Масис": (40.05, 44.42, 40.08, 44.45),
    "Капан": (39.19, 46.39, 39.22, 46.43),
    "Ашхарак": (40.29, 44.35, 40.31, 44.38),
})
AMENITY = {"restaurant", "cafe", "bar", "pub", "fast_food", "ice_cream", "dentist", "clinic", "doctors",
           "pharmacy", "veterinary", "kindergarten", "language_school", "driving_school", "music_school",
           "car_wash", "car_rental", "events_venue", "nightclub", "childcare", "training", "studio"}
OFFICE_SKIP = {"government", "ngo", "diplomatic", "association", "political_party", "religion", "it",
               "telecommunication", "advertising_agency", "educational_institution", "yes"}
TOURISM = {"hotel", "guest_house", "hostel", "motel", "apartment", "chalet", "camp_site"}
LEISURE = {"fitness_centre", "sports_centre", "dance", "escape_game", "playground_indoor", "sauna"}
SKIP_WORDS = ("web", "digital", "marketing", " ai", "smm", "design", "it ", "software", "tech")
FIELDS = ["poyavilsya", "name", "category", "city", "street", "phone", "instagram", "facebook", "telegram",
          "email", "osm", "map"]


def fetch(bbox):
    b = ",".join(map(str, bbox))
    q = (f'[out:json][timeout:120];(nwr["name"]["shop"](newer:"{SINCE}T00:00:00Z")({b});'
         f'nwr["name"]["office"](newer:"{SINCE}T00:00:00Z")({b});'
         f'nwr["name"]["craft"](newer:"{SINCE}T00:00:00Z")({b});'
         f'nwr["name"]["amenity"](newer:"{SINCE}T00:00:00Z")({b});'
         f'nwr["name"]["tourism"](newer:"{SINCE}T00:00:00Z")({b});'
         f'nwr["name"]["leisure"](newer:"{SINCE}T00:00:00Z")({b});'
         f'nwr["name"]["healthcare"](newer:"{SINCE}T00:00:00Z")({b}););out center meta;')
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for _ in range(2):
        for url in ENDPOINTS:
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "evnweb-prospecting/1.0"})
                with urllib.request.urlopen(req, timeout=150) as r:
                    js = json.load(r)
                if js.get("remark") and not js.get("elements"):
                    raise RuntimeError(js["remark"][:200])
                return js["elements"]
            except Exception as e:
                last = e
                print(f"  {url}: {e}", file=sys.stderr)
        time.sleep(10)
    raise RuntimeError(last)


def category(t):
    if t.get("shop"):
        return "магазин: " + t["shop"]
    if t.get("amenity") in AMENITY:
        return t["amenity"]
    if t.get("office") and t["office"] not in OFFICE_SKIP:
        return "офис: " + t["office"]
    if t.get("craft"):
        return "производство/мастерская: " + t["craft"]
    if t.get("tourism") in TOURISM:
        return t["tourism"]
    if t.get("leisure") in LEISURE:
        return t["leisure"]
    if t.get("healthcare") and not t.get("amenity"):
        return "медицина: " + t["healthcare"]
    return ""


def main():
    els = []
    for city, bbox in CITIES.items():
        try:
            got = fetch(bbox)
        except Exception as e:
            print(f"{city}: пропущен ({e})", flush=True)
            continue
        for el in got:
            el["_city"] = city
        print(f"{city}: {len(got)}", flush=True)
        els += got
        time.sleep(3)
    if not els:
        raise SystemExit("Overpass вернул 0 объектов")
    # опорные точки id -> дата создания (объекты версии 1)
    ref = {}
    for el in els:
        if el.get("version") == 1:
            ref.setdefault(el["type"], []).append((el["id"], el["timestamp"]))
    for k in ref:
        ref[k].sort()

    def created(el):
        if el.get("version") == 1:
            return el["timestamp"][:10]
        pts = ref.get(el["type"], [])
        i = bisect.bisect_left(pts, (el["id"], ""))
        if i == 0:
            return "старый"  # id меньше всех новых: объект давний, просто изменён
        return pts[i - 1][1][:10]

    rows = {}
    for el in els:
        t = el.get("tags", {})
        cat = category(t)
        if not cat or t.get("brand") or t.get("brand:wikidata"):
            continue
        if first(t, "website", "contact:website", "url"):
            continue
        name = t.get("name", "")
        if any(w in f" {name.lower()} " for w in SKIP_WORDS):
            continue
        d = created(el)
        if d == "старый" or d < SINCE:
            continue
        c = el.get("center", el)
        rows[f'{el["type"]}/{el["id"]}'] = {
            "poyavilsya": d, "name": name, "category": cat, "city": el["_city"],
            "street": " ".join(x for x in [t.get("addr:street", ""), t.get("addr:housenumber", "")] if x),
            "phone": first(t, "phone", "contact:phone", "mobile", "contact:mobile"),
            "instagram": first(t, "contact:instagram", "instagram"),
            "facebook": first(t, "contact:facebook", "facebook"),
            "telegram": first(t, "contact:telegram", "telegram"),
            "email": first(t, "email", "contact:email"),
            "osm": f'https://www.openstreetmap.org/{el["type"]}/{el["id"]}',
            "map": f'https://www.google.com/maps/search/?api=1&query={c.get("lat")},{c.get("lon")}',
        }
    os.makedirs("data/new", exist_ok=True)
    with open("data/new/novye.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: r["poyavilsya"], reverse=True))
    print(f"Новых без сайта: {len(rows)}")


if __name__ == "__main__":
    main()
