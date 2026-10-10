#!/usr/bin/env python3
"""Перепроверка лидов Яндекса через Google Карты: у многих мест сайт указан только в Google.

Берёт из data/maps/yandex.csv карточки без своего сайта (только шард MAPS_SHARD из MAPS_SHARDS),
ищет «название, адрес, Yerevan» в Google Картах и записывает найденный там сайт -> MAPS_OUT.
"""
import asyncio, csv, os, re, sys, urllib.parse
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(__file__))
from maps_google import CARDS_JS

SOCIAL = ("instagram.", "facebook.", "fb.", "t.me", "wa.me", "viber", "taplink", "linktr.ee", "booking.com",
          "airbnb.", "tripadvisor.", "tiktok.", "vk.com", "youtube.", "list.am", "menu.am", "wolt.com")
OUT = os.environ.get("MAPS_OUT", "out/verify.csv")


def no_site(web):
    links = (web or "").split()
    return not [u for u in links if not any(s in u.lower() for s in SOCIAL)]


async def main():
    shard, shards = int(os.environ.get("MAPS_SHARD", "0")), int(os.environ.get("MAPS_SHARDS", "1"))
    rows = [r for r in csv.DictReader(open("data/maps/yandex.csv", encoding="utf-8")) if no_site(r["website"])]
    rows = [r for i, r in enumerate(rows) if i % shards == shard]
    print("проверяю", len(rows), flush=True)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    fh = open(OUT, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(fh, ["yandex_id", "google_name", "google_website", "google_link"])
    w.writeheader()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await (await b.new_context(locale="en-US", viewport={"width": 1280, "height": 900})).new_page()
        for n, r in enumerate(rows, 1):
            q = f"{r['name']}, {r['address']}, Yerevan"
            gname = gweb = glink = ""
            try:
                await pg.goto("https://www.google.com/maps/search/" + urllib.parse.quote(q) + "?hl=en",
                              wait_until="domcontentloaded", timeout=45000)
                await pg.wait_for_timeout(3000)
                if await pg.locator('div[role="feed"]').count():
                    cards = await pg.evaluate(CARDS_JS)
                    if cards:
                        gname, gweb, glink = cards[0]["name"], cards[0]["website"], cards[0]["href"]
                else:
                    h1 = await pg.eval_on_selector_all("h1", "els => els.map(e => e.innerText)")
                    web = await pg.eval_on_selector_all('a[data-item-id="authority"]', "els => els.map(e => e.href)")
                    gname, gweb, glink = (h1[-1] if h1 else ""), (web[0] if web else ""), pg.url
            except Exception as e:
                print("  !", r["name"], type(e).__name__, flush=True)
            w.writerow({"yandex_id": r["yandex_id"], "google_name": gname, "google_website": gweb,
                        "google_link": glink.split("?")[0]})
            if n % 50 == 0:
                fh.flush(); print(n, flush=True)
        await b.close()
    fh.close()


if __name__ == "__main__":
    asyncio.run(main())
