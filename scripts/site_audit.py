#!/usr/bin/env python3
"""
Оценка «устарелости» сайтов для поиска клиентов EVNWEB.

Запуск (нужен только Python 3, без установки библиотек):
    python3 site_audit.py sites.csv            -> пишет audit_result.csv
    python3 site_audit.py https://example.am   -> проверить один сайт

sites.csv: первая колонка name, вторая url (остальные колонки сохраняются).
Чем выше score (0-100), тем сильнее сайт устарел и тем горячее клиент.
"""
import csv, re, ssl, sys, time, datetime, urllib.request, urllib.error
from urllib.parse import urlparse

UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36"
YEAR = datetime.date.today().year


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        body = r.read(3_000_000)
        return r.geturl(), r.status, body.decode(r.headers.get_content_charset() or "utf-8", "replace"), time.time() - t, len(body)


SOCIAL = ("facebook.com", "fb.com", "fb.me", "instagram.com", "booking.com", "airbnb.", "tripadvisor.", "t.me/", "linktr.ee", "wa.me/")


def dns_status(host):
    """NXDOMAIN по Google DNS-over-HTTPS: 'dead', 'alive' или 'unknown'."""
    import json
    try:
        q = urllib.request.Request(f"https://dns.google/resolve?name={host}&type=A", headers={"User-Agent": UA})
        with urllib.request.urlopen(q, timeout=10) as r:
            js = json.load(r)
        if js.get("Status") == 3:
            return "dead"
        return "alive" if js.get("Answer") else "dead"
    except Exception:
        return "unknown"


def why(e, url=""):
    """Причина, по которой сайт не открылся; score None = непонятно (защита от ботов), не считаем лидом."""
    import socket
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 403, 429, 503):
            return None, f"сайт не пускает бота (HTTP {e.code}), проверить вручную"
        return 85, f"сайт выдаёт ошибку HTTP {e.code}"
    r = getattr(e, "reason", e)
    if isinstance(r, socket.gaierror):
        if dns_status(urlparse(url).hostname or "") == "dead":
            return 100, "домен не работает (не продлён или не настроен)"
        return None, "сервер проверки не смог открыть сайт, проверить вручную"
    if isinstance(r, ssl.SSLError):
        return 90, "сертификат HTTPS сломан (браузер пугает посетителей)"
    # таймауты и обрывы могут быть проблемой сервера проверки, а не сайта
    return None, f"сайт не ответил серверу проверки ({type(r).__name__}), проверить вручную"


def audit(url):
    """Возвращает (score 0-100 или None, [проблемы], итоговый url)."""
    if ".business.site" in url.lower():
        return 100, ["сайт на Google business.site, Google отключил такие сайты в 2024: ссылка ведёт в пустоту"], url
    if any(x in url.lower() for x in SOCIAL):
        return 100, ["своего сайта нет, вместо него ссылка на соцсеть/агрегатор"], url
    if not re.match(r"https?://", url, re.I):
        url = "https://" + url
    problems, score = [], 0
    try:
        final, status, html, secs, size = fetch(url)
    except Exception as e:
        first_score, first_why = why(e, url)
        try:
            final, status, html, secs, size = fetch(re.sub(r"^https://", "http://", url, flags=re.I))
            if first_score and "сертификат" in first_why:
                score, problems = 30, [first_why]
        except Exception as e2:
            s2, w2 = why(e2, url)
            if first_score is None and s2 is None:
                return None, [first_why], url
            if first_score is None or s2 is None:
                return None, [first_why if first_score is None else w2], url
            return (first_score, [first_why], url) if "сертификат" in first_why or "домен" in first_why else (s2, [w2], url)
    low = html.lower()
    if "suspendedpage" in final.lower() or "account suspended" in low[:5000]:
        return 95, ["хостинг отключил сайт (не оплачен), вместо сайта заглушка"], final

    def add(points, text):
        nonlocal score
        score += points
        problems.append(text)

    if urlparse(final).scheme != "https":
        add(20, "нет HTTPS (Chrome пишет «Не защищено»)")
    if 'name="viewport"' not in low and "name=viewport" not in low:
        add(25, "не адаптирован под телефон (нет viewport)")
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", low)]
    if years and max(years) <= YEAR - 4:
        add(15, f"в подвале © {max(years)}: сайт давно не обновляли")
    m = re.search(r"jquery[.-]?(\d)\.(\d+)", low)
    if m and (int(m.group(1)), int(m.group(2))) < (1, 12):
        add(10, f"старый jQuery {m.group(1)}.{m.group(2)}")
    if "<table" in low and low.count("<table") > 3 and "<div" not in low[:5000]:
        add(10, "вёрстка таблицами (2000-е годы)")
    if re.search(r"\.swf|<marquee|<font\b|<frameset", low):
        add(15, "устаревшие теги (Flash/marquee/font/frames)")
    if "wix.com" in low or "tilda" in low or "ucoz" in low or "narod" in low:
        add(5, "сделан на конструкторе (ограничения, нет своей админки)")
    langs = set(re.findall(r'hreflang="([a-z]{2})', low)) | set(re.findall(r'/(hy|am|ru|en)/', low))
    if len(langs) < 2:
        add(10, "похоже, только один язык (туристы не поймут)")
    if not re.search(r"tel:|t\.me/|wa\.me/|whatsapp|viber:", low):
        add(10, "нет кликабельного телефона/мессенджера")
    if not re.search(r"book|reserv|бронир|ամրագր|order|заказ", low):
        add(5, "нет онлайн-брони/заказа")
    if secs > 4:
        add(10, f"грузится медленно ({secs:.1f} c)")
    if size > 2_500_000:
        add(5, f"тяжёлая страница ({size // 1024} КБ HTML)")
    return min(score, 100), problems, final


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    arg = sys.argv[1]
    if arg.startswith("http") or ("." in arg and not arg.endswith(".csv")):
        s, p, f = audit(arg)
        print(f"{f}\nscore {s if s is not None else '?'}\n- " + "\n- ".join(p or ["проблем не найдено"])); return
    with open(arg, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    header, rows = rows[0], rows[1:]
    out = []
    for i, row in enumerate(rows, 1):
        url = row[1].strip() if len(row) > 1 else ""
        if not url:
            s, p, f = 100, ["сайта нет"], ""
        else:
            s, p, f = audit(url)
        print(f"[{i}/{len(rows)}] {s if s is not None else '?':>3}  {row[0]}")
        out.append(row + ["" if s is None else s, "; ".join(p), f])
    out.sort(key=lambda r: -(r[len(header)] or 0))
    with open("audit_result.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header + ["score", "problems", "final_url"])
        w.writerows(out)
    print("\nГотово: audit_result.csv (отсортировано, самые устаревшие сверху)")


if __name__ == "__main__":
    main()
