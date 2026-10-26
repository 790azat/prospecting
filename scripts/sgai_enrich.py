#!/usr/bin/env python3
"""Телефоны для лидов без телефона: проба ScrapeGraphAI против нашего обычного разбора.

Вход: data/enrich/input.csv (лиды общего списка без телефона, выгружает market/master/sborka.py).
Берётся шард ENRICH_SHARD из ENRICH_SHARDS, не больше ENRICH_LIMIT строк.

Этап 1 (Playwright, без модели): карточка места в Google Картах по запросу «название, город, Armenia».
  regex_*: телефон и сайт из кнопок карточки; name_ok: название карточки похоже на наше;
  site_alive: указанный сайт (не соцсеть) отвечает.
Этап 2 (ScrapeGraphAI SearchGraph + локальная модель Ollama, ключи не нужны), только где этап 1 не дал телефона:
  sg_web_*: поиск телефона в интернете (DuckDuckGo, при отказе Bing), первые 3 сайта читает модель.
Телефон от модели засчитывается, только если его цифры есть на этих сайтах (защита от выдумки).
Проба 17.10 на 30 лидах: карточка Google дала телефон 24/30 за ~4 с; SmartScraperGraph на той же
карточке 5/30 за ~50 с (поэтому убран); SearchGraph добавил 2 телефона там, где Google пусто, ~80 с на лид.
Выход: ENRICH_OUT (csv).
"""
import csv, json, os, re, signal, sys, time, urllib.parse

INP = "data/enrich/input.csv"
DONE = "data/enrich/results.csv"  # уже проверенные (название + город) повторно не проверяем
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
          "name_ok", "site_alive",
          "sg_web_phone", "sg_web_raw", "sg_web_sources", "sg_web_sec"]


def key(r):
    return (r["nazvanie"].strip().lower(), r["gorod"].strip().lower())


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


SOCIAL = ("instagram.", "facebook.", "fb.", "t.me", "wa.me", "viber", "taplink", "linktr.ee", "booking.com",
          "airbnb.", "tripadvisor.", "tiktok.", "vk.com", "youtube.", "list.am", "menu.am", "wolt.com", "threads.",
          "myqrcode.", "google.", "linkedin.")
GENERIC = {"hotel", "hotels", "restaurant", "cafe", "café", "bar", "coffee", "yerevan", "inn", "house", "guest",
           "boutique", "gallery", "and", "the", "club", "shop", "salon", "beauty", "studio", "center", "centre",
           "armenia", "dilijan", "gyumri", "resort", "spa", "pub", "bakery", "lounge", "wine", "art", "family",
           "отель", "гостиница", "ресторан", "кафе", "бар", "гостевой", "дом", "салон", "студия", "центр"}


def words(s):
    s = s.lower().replace("&", " ").replace("'s", "")
    return {w for w in re.findall(r"[\w]+", s) if len(w) >= 3 and w not in GENERIC}


def name_ok(ours, google):
    a, b = words(ours), words(google)
    ja, jb = re.sub(r"\W", "", ours.lower()), re.sub(r"\W", "", google.lower())
    return bool(a & b) or (len(ja) >= 4 and (ja in jb or jb in ja))


def real_site(url):
    return bool(url) and not any(x in url.lower() for x in SOCIAL)


def alive(url):
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=20).status < 400
    except Exception:
        return False


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
            d["name_ok"] = int(name_ok(r["nazvanie"], d["google_name"])) if d["google_name"] else 0
            if real_site(d["regex_website"]):
                d["site_alive"] = int(alive(d["regex_website"]))
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


class Timeout(Exception):
    pass


def _alarm(*_):
    raise Timeout()


def stage_sgai(rows, cards, save):
    from scrapegraphai.graphs import SearchGraph
    signal.signal(signal.SIGALRM, _alarm)
    llm = {"model": f"ollama/{MODEL}", "model_tokens": 8192, "format": "json", "temperature": 0,
           "base_url": "http://localhost:11434"}
    out = {}
    todo = [r for r in rows if not (cards.get(r["n"], {}).get("regex_phone") and cards[r["n"]].get("name_ok"))]
    print("ScrapeGraphAI для", len(todo), "лидов без телефона в Google", flush=True)
    for i, r in enumerate(todo, 1):
        d, t = {}, time.time()
        city = CITY.get(r["gorod"], r["gorod"])
        for engine in ("duckduckgo", "bing"):
            try:
                signal.alarm(240)
                g = SearchGraph(prompt=f"What is the phone number of {r['nazvanie']} ({r['nisha']}) in {city}, Armenia? "
                                       "Return JSON with keys: phone, source_url. Empty string if not found.",
                                config={"llm": llm, "headless": True, "verbose": False,
                                        "max_results": 3, "search_engine": engine})
                a = as_dict(g.run())
                urls = g.get_considered_urls() or []
                signal.alarm(60)
                d["sg_web_raw"] = json.dumps(a, ensure_ascii=False)[:400]
                d["sg_web_sources"] = " ".join(urls)[:400]
                d["sg_web_phone"] = " ".join(grounded(a.get("phone", ""), " ".join(page_text(u) for u in urls)))
                signal.alarm(0)
                break
            except Exception as e:
                signal.alarm(0)
                d["sg_web_raw"] = f"ошибка {engine} " + type(e).__name__ + ": " + str(e)[:150]
                if "No results" not in str(e) and "SearchRequestError" not in type(e).__name__:
                    break
        d["sg_web_sec"] = round(time.time() - t, 1)
        out[r["n"]] = d
        save(out)  # пишем после каждого лида: если шард упрётся в лимит времени, готовое не пропадёт
        print(f"sgai {i}/{len(todo)} {r['nazvanie']}: {d.get('sg_web_phone') or '-'} ({d['sg_web_sec']} с)", flush=True)
    return out


def main():
    shard, shards = int(os.environ.get("ENRICH_SHARD", "0")), int(os.environ.get("ENRICH_SHARDS", "1"))
    limit = int(os.environ.get("ENRICH_LIMIT", "0"))
    done = set()
    if os.path.exists(DONE) and os.environ.get("ENRICH_REDO") != "1":
        done = {key(r) for r in csv.DictReader(open(DONE, encoding="utf-8"))}
    rows = [r for r in csv.DictReader(open(INP, encoding="utf-8")) if key(r) not in done]
    rows = [r for i, r in enumerate(rows) if i % shards == shard]
    if limit:
        rows = rows[:limit]
    print("лидов", len(rows), flush=True)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)

    def save(sg):
        with open(OUT + ".tmp", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({**r, **cards.get(r["n"], {}), **sg.get(r["n"], {})})
        os.replace(OUT + ".tmp", OUT)

    cards = stage_cards(rows)
    save({})
    if os.environ.get("ENRICH_SGAI", "1") == "1":
        stage_sgai(rows, cards, save)

if __name__ == "__main__":
    main()
