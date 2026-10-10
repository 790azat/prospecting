#!/usr/bin/env python3
"""Бизнесы Еревана из Google Карт (браузер Playwright, без ключа API) -> data/maps/google*.csv.

Для каждой ниши и района открывается поиск «<ниша> in <район>, Yerevan», лента результатов
прокручивается до конца (до ~120 мест). У карточек с кнопкой «Website» сайт есть, их пропускаем;
карточки без сайта открываем и забираем адрес, телефон и категорию.
Запуск: pip install playwright && python3 -m playwright install --with-deps chromium && python3 scripts/maps_google.py
Переменные: MAPS_NICHES (через запятую, английские запросы), MAPS_OUT, MAPS_AREAS.
"""
import asyncio, csv, os, re, sys, urllib.parse
from playwright.async_api import async_playwright

OUT = os.environ.get("MAPS_OUT", "data/maps/google.csv")
NICHES = {
    "restaurant": "ресторан", "cafe": "кафе", "coffee shop": "кофейня", "bar": "бар",
    "hotel": "отель", "guest house": "гостевой дом", "hostel": "хостел",
    "dentist": "стоматология", "medical clinic": "клиника",
    "beauty salon": "салон красоты", "barber shop": "парикмахерская", "nail salon": "салон красоты",
    "car repair": "автосервис", "gym": "фитнес", "bakery": "пекарня", "pastry shop": "кондитерская",
    "florist": "цветы", "veterinarian": "ветклиника", "language school": "учебный центр",
    "furniture maker": "мебель", "clothing store": "магазин одежды", "photo studio": "фотостудия",
}
AREAS = ["Kentron", "Arabkir", "Ajapnyak", "Avan", "Davtashen", "Erebuni", "Kanaker-Zeytun",
         "Malatia-Sebastia", "Nor Nork", "Nork-Marash", "Shengavit", "Nubarashen"]
FIELDS = ["google_id", "name", "category", "niche", "city", "address", "phone", "website", "instagram",
          "facebook", "telegram", "whatsapp", "viber", "other_social", "rating", "reviews", "status",
          "hours", "lat", "lon", "link", "query"]

CARDS_JS = """() => [...document.querySelectorAll('div[role="feed"] a.hfpxzc')].map(a => {
  const card = a.closest('div.Nv2PK') || a.parentElement;
  const web = card && card.querySelector('a[data-value="Website"], a[aria-label^="Visit"][href^="http"]');
  return {name: a.getAttribute('aria-label') || '', href: a.href,
          website: web ? web.href : '', text: card ? card.innerText : ''};
})"""


def place_id(href):
    m = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", href)
    return m.group(1) if m else href.split("?")[0]


def coords(href):
    m = re.search(r"!3d(-?[\d.]+)!4d(-?[\d.]+)", href)
    return (m.group(1), m.group(2)) if m else ("", "")


async def scroll_feed(pg):
    feed = pg.locator('div[role="feed"]')
    if not await feed.count():
        return
    last = -1
    for _ in range(25):
        await feed.evaluate("e => e.scrollBy(0, 8000)")
        await pg.wait_for_timeout(1300)
        n = await pg.locator('div[role="feed"] a.hfpxzc').count()
        end = await pg.locator("text=You've reached the end of the list").count()
        if end or n == last:
            break
        last = n


async def details(pg, href):
    await pg.goto(href, wait_until="domcontentloaded", timeout=45000)
    try:
        await pg.wait_for_selector("h1", timeout=10000)
    except Exception:
        pass
    await pg.wait_for_timeout(1200)
    one = lambda sel, attr=None: pg.eval_on_selector_all(
        sel, f"els => els.map(e => {('e.getAttribute(%r)' % attr) if attr else 'e.innerText'})")
    web = await one('a[data-item-id="authority"]', "href")
    phone = await one('button[data-item-id^="phone"]', "data-item-id")
    addr = await one('button[data-item-id="address"]', "aria-label")
    cat = await one("button.DkEaL")
    closed = await pg.locator("text=/Permanently closed|Temporarily closed/").count()
    rating = await one('div.F7nice span[aria-hidden="true"]')
    reviews = await one('div.F7nice span[aria-label$="reviews"]', "aria-label")
    return {
        "website": " ".join(web),
        "phone": "; ".join(p.replace("phone:tel:", "") for p in phone),
        "address": (addr[0] if addr else "").replace("Address: ", "").strip(),
        "category": cat[0] if cat else "",
        "status": "closed" if closed else "open",
        "rating": rating[0] if rating else "",
        "reviews": re.sub(r"\D", "", reviews[0]) if reviews else "",
    }


def save(found):
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(found.values(), key=lambda r: (r["niche"], r["name"])):
            w.writerow({k: r.get(k, "") for k in FIELDS})


async def main():
    niches = [n for n in os.environ.get("MAPS_NICHES", ",".join(NICHES)).split(",") if n]
    areas = [a for a in os.environ.get("MAPS_AREAS", ",".join(AREAS)).split(",") if a]
    found, with_site = {}, set()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
        pg = await ctx.new_page()
        for q in niches:
            before = len(found)
            for area in areas:
                query = f"{q} in {area}, Yerevan"
                url = "https://www.google.com/maps/search/" + urllib.parse.quote(query) + "?hl=en"
                try:
                    await pg.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await pg.wait_for_timeout(3500)
                    await scroll_feed(pg)
                    cards = await pg.evaluate(CARDS_JS)
                except Exception as e:
                    print(f"  ! {query}: {type(e).__name__}", flush=True)
                    continue
                todo = []
                for c in cards:
                    pid = place_id(c["href"])
                    if pid in found or pid in with_site:
                        continue
                    if c["website"]:
                        with_site.add(pid)
                        continue
                    todo.append((pid, c))
                for pid, c in todo:
                    try:
                        d = await details(pg, c["href"])
                    except Exception as e:
                        print(f"  ! {c['name']}: {type(e).__name__}", flush=True)
                        continue
                    if d["website"]:
                        with_site.add(pid)
                        continue
                    lat, lon = coords(c["href"])
                    found[pid] = {"google_id": pid, "name": c["name"], "niche": NICHES.get(q, q), "city": "Ереван",
                                  "lat": lat, "lon": lon, "link": c["href"].split("?")[0], "query": query, **d}
                print(f"{query}: карточек {len(cards)}, без сайта новых {len(todo)}", flush=True)
            print(f"== {q}: +{len(found) - before} без сайта (всего {len(found)}, с сайтом {len(with_site)})", flush=True)
            save(found)
        await b.close()
    save(found)


if __name__ == "__main__":
    asyncio.run(main())
