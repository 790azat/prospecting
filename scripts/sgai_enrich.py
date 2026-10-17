#!/usr/bin/env python3
"""Телефоны для лидов без телефона: проба ScrapeGraphAI против нашего обычного разбора.

Вход: data/enrich/input.csv (лиды общего списка без телефона, выгружает market/master/sborka.py).
Берётся шард ENRICH_SHARD из ENRICH_SHARDS, не больше ENRICH_LIMIT строк.

Этап 1 (Playwright): карточка места в Google Картах по запросу «название, город, Armenia».
  regex_*: телефон и сайт из кнопок карточки, как это делают maps_google.py / maps_verify.py.
Этап 2 (ScrapeGraphAI + локальная модель Ollama, ключи не нужны):
  sg_card_*: SmartScraperGraph читает ту же карточку и достаёт телефон, WhatsApp, Telegram, сайт;
  sg_web_*: SearchGraph ищет телефон в интернете (DuckDuckGo, несколько первых сайтов).
Телефон от модели засчитывается, только если его цифры есть в исходном тексте (защита от выдумки).
Выход: ENRICH_OUT (csv), время каждого этапа в колонках *_sec.
"""
import csv, json, os, re, sys, time, urllib.parse

INP = "data/enrich/input.csv"
OUT = os.environ.get("ENRICH_OUT", "out/enrich.csv")
MODEL = os.environ.get("ENRICH_MODEL", "qwen2.5:3b")
CITY = {"Ереван": "Yerevan", "Гюмри": "Gyumri", "Ванадзор": "Vanadzor", "Дилижан": "Dilijan",
        "Севан": "Sevan", "Джермук": "Jermuk", "Цахкадзор": "Tsaghkadzor", "Горис": "Goris",
        "Ехегнадзор": "Yeghegnadzor", "Эчмиадзин": "Vagharshapat", "Абовян": "Abovyan",
        "Капан": "Kapan", "Иджеван": "Ijevan", "Аштарак": "Ashtarak", "Гарни": "Garni",
        "Армавир": "Armavir", "Арташат": "Artashat", "Раздан": "Hrazdan", "Сисиан": "Sisian"}
# мобильные операторы, Ереван (10/11/12) и областные коды 2x/3x
CODES = r"(33|4[1-9]|55|77|9[1-9]|1[0-2]|2[2-8]|3[1-8])"
FIELDS = ["n", "nazvanie", "nisha", "gorod",
          "regex_phone", "regex_website", "google_name", "google_link", "card_sec",
          "sg_card_phone", "sg_card_whatsapp", "sg_card_telegram", "sg_card_website", "sg_card_raw", "sg_card_sec",
          "sg_web_phone", "sg_web_raw", "sg_web_sources", "sg_web_sec"]


def phones(text):
    """Армянские номера из текста -> список 8-значных хвостов (как norm_phone в sborka.py)."""
    out = []
    for m in re.finditer(r"\+?\(?\d[\d\s\-().]{6,18}\d", text or ""):
        d = re.sub(r"\D", "", m.group(0))
        if d.startswith("374") and len(d) == 11:
            d = d[3:]
        elif d.startswith("0") and len(d) == 9:
            d = d[1:]
        if len(d) == 8 and re.match(CODES, d) and d not in out:
            out.append(d)
    return out


def fmt(d8):
    return f"+374 {d8[:2]} {d8[2:4]} {d8[4:6]} {d8[6:]}"


def grounded(llm_value, source_text):
    """Номера из ответа модели, цифры которых реально есть в источнике."""
    src = re.sub(r"\D", "", source_text or "")
    return [fmt(d) for d in phones(str(llm_value)) if d in src]


def page_text(url):
    """Текст страницы, откуда SearchGraph взял ответ, для проверки номера."""
    import requests
    try:
        return requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
    except Exception:
        return ""


def stage_cards(rows):
    from playwright.sync_api import sync_playwright
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context(locale="en-US", viewport={"width": 1280, "height": 900}).new_page()
        for i, r in enumerate(rows, 1):
            t = time.time()
            q = f"{r['nazvanie']}, {CITY.get(r['gorod'], r['gorod'])}, Armenia"
            d = {"regex_phone": "", "regex_website": "", "google_name": "", "google_link": "", "text": "", "html": ""}
            try:
                pg.goto("https://www.google.com/maps/search/" + urllib.parse.quote(q) + "?hl=en",
                        wait_until="domcontentloaded", timeout=45000)
                if "consent." in pg.url:
                    pg.locator('button:has-text("Accept all")').first.click(timeout=8000)
                pg.wait_for_timeout(3000)
                first = pg.locator('div[role="feed"] a.hfpxzc')
                if first.count():
                    first.first.click()
                    pg.wait_for_timeout(3000)
                main = pg.locator('div[role="main"]').last
                if main.count():
                    d["text"] = main.inner_text(timeout=5000)
                    d["html"] = main.inner_html(timeout=5000)
                    h1 = main.locator("h1")
                    d["google_name"] = h1.first.inner_text() if h1.count() else ""
                tel = pg.eval_on_selector_all('button[data-item-id^="phone:tel:"]',
                                              "els => els.map(e => e.getAttribute('data-item-id'))")
                d["regex_phone"] = " ".join(fmt(x) for t_ in tel for x in phones(t_.split(":")[-1]))
                web = pg.eval_on_selector_all('a[data-item-id="authority"]', "els => els.map(e => e.href)")
                d["regex_website"] = web[0] if web else ""
                d["google_link"] = pg.url.split("?")[0]
            except Exception as e:
                print("  ! карты", r["nazvanie"], type(e).__name__, flush=True)
            d["card_sec"] = round(time.time() - t, 1)
            res[r["n"]] = d
            print(f"карты {i}/{len(rows)} {r['nazvanie']}: {d['regex_phone'] or '-'}", flush=True)
        b.close()
    return res


def as_dict(x):
    if isinstance(x, dict):
        return x.get("content", x) if isinstance(x.get("content"), dict) else x
    try:
        return json.loads(x)
    except Exception:
        return {"raw": str(x)}


def stage_sgai(rows, cards):
    from scrapegraphai.graphs import SmartScraperGraph, SearchGraph
    llm = {"model": f"ollama/{MODEL}", "model_tokens": 8192, "format": "json", "temperature": 0,
           "base_url": "http://localhost:11434"}
    cfg = {"llm": llm, "headless": True, "verbose": False}
    ask = ("Extract the business contact details. Return JSON with keys: phone, whatsapp, telegram, website. "
           "Use only what is written on the page, empty string if absent.")
    out = {}
    for i, r in enumerate(rows, 1):
        c, d = cards.get(r["n"], {}), {}
        t = time.time()
        if c.get("html"):
            try:
                a = as_dict(SmartScraperGraph(prompt=ask, source=c["html"], config=cfg).run())
                d["sg_card_raw"] = json.dumps(a, ensure_ascii=False)[:400]
                d["sg_card_phone"] = " ".join(grounded(a.get("phone", ""), c["text"] + c["html"]))
                d["sg_card_whatsapp"] = " ".join(grounded(a.get("whatsapp", ""), c["html"]))
                d["sg_card_telegram"] = str(a.get("telegram", "") or "")[:80]
                d["sg_card_website"] = str(a.get("website", "") or "")[:120]
            except Exception as e:
                d["sg_card_raw"] = "ошибка " + type(e).__name__ + ": " + str(e)[:150]
        d["sg_card_sec"] = round(time.time() - t, 1)

        t = time.time()
        city = CITY.get(r["gorod"], r["gorod"])
        try:
            g = SearchGraph(prompt=f"What is the phone number of {r['nazvanie']} ({r['nisha']}) in {city}, Armenia? "
                                   "Return JSON with keys: phone, source_url. Empty string if not found.",
                            config={**cfg, "max_results": 3, "search_engine": "duckduckgo"})
            a = as_dict(g.run())
            urls = g.get_considered_urls() or []
            d["sg_web_raw"] = json.dumps(a, ensure_ascii=False)[:400]
            d["sg_web_sources"] = " ".join(urls)[:400]
            d["sg_web_phone"] = " ".join(grounded(a.get("phone", ""), " ".join(page_text(u) for u in urls)))
        except Exception as e:
            d["sg_web_raw"] = "ошибка " + type(e).__name__ + ": " + str(e)[:150]
        d["sg_web_sec"] = round(time.time() - t, 1)
        out[r["n"]] = d
        print(f"sgai {i}/{len(rows)} {r['nazvanie']}: карточка {d.get('sg_card_phone') or '-'}, "
              f"интернет {d.get('sg_web_phone') or '-'} ({d['sg_card_sec']}+{d['sg_web_sec']} с)", flush=True)
    return out


def main():
    shard, shards = int(os.environ.get("ENRICH_SHARD", "0")), int(os.environ.get("ENRICH_SHARDS", "1"))
    limit = int(os.environ.get("ENRICH_LIMIT", "0"))
    rows = [r for i, r in enumerate(csv.DictReader(open(INP, encoding="utf-8"))) if i % shards == shard]
    if limit:
        rows = rows[:limit]
    print("лидов", len(rows), flush=True)
    cards = stage_cards(rows)
    sg = stage_sgai(rows, cards) if os.environ.get("ENRICH_SGAI", "1") == "1" else {}
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, **cards.get(r["n"], {}), **sg.get(r["n"], {})})


if __name__ == "__main__":
    main()
