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


def audit(url):
    if not re.match(r"https?://", url):
        url = "https://" + url
    problems, score = [], 0
    try:
        final, status, html, secs, size = fetch(url)
    except ssl.SSLError:
        return 90, ["сертификат HTTPS сломан (браузер пугает посетителей)"], url
    except Exception as e:
        try:
            final, status, html, secs, size = fetch(url.replace("https://", "http://", 1))
        except Exception:
            return 100, [f"сайт не открывается ({type(e).__name__})"], url
    low = html.lower()

    def add(points, text):
        nonlocal score
        score += points
        problems.append(text)

    if urlparse(final).scheme != "https":
        add(20, "нет HTTPS (Chrome пишет «Не защищено»)")
    if 'name="viewport"' not in low and "name=viewport" not in low:
        add(25, "не адаптирован под телефон (нет viewport)")
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", low)]
    if years and max(years) <= YEAR - 3:
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
        print(f"{f}\nscore {s}\n- " + "\n- ".join(p or ["проблем не найдено"])); return
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
        print(f"[{i}/{len(rows)}] {s:3d}  {row[0]}")
        out.append(row + [s, "; ".join(p), f])
    out.sort(key=lambda r: -r[len(header)])
    with open("audit_result.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header + ["score", "problems", "final_url"])
        w.writerows(out)
    print("\nГотово: audit_result.csv (отсортировано, самые устаревшие сверху)")


if __name__ == "__main__":
    main()
