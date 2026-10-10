import urllib.request, urllib.parse, json, re, gzip, time, os
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
def ya(q, extra=""):
    u = "https://yandex.ru/maps/10262/yerevan/search/" + urllib.parse.quote(q) + "/" + extra
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "ru", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read(); b = gzip.decompress(b) if r.headers.get("Content-Encoding") == "gzip" else b
    t = b.decode("utf-8", "replace")
    m = re.search(r'<script type="application/json" class="state-view">(.*?)</script>', t, re.S)
    if not m: return None, "captcha" in t.lower()
    res = json.loads(m.group(1))["stack"][0].get("results", {})
    return res, False
tests = [("ресторан",""),("ресторан","?page=2"),("ресторан","?page=3"),("ресторан","?ll=44.48%2C40.15&z=16"),("ресторан","?ll=44.55%2C40.20&z=16"),("кафе","?ll=44.51%2C40.18&z=17"),("салон красоты",""),("гостиница","")]
for q, e in tests:
    try:
        r, cap = ya(q, e)
        if r is None: print(q, e, "NO STATE captcha=", cap)
        else: print(q, e, r.get("totalResultCount"), len(r.get("items", [])), [i.get("title") for i in r.get("items", [])][:6])
    except Exception as ex: print(q, e, "ERR", ex)
    time.sleep(3)
