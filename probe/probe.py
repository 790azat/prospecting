import urllib.request, urllib.parse, os, gzip
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
urls = {
 "ya_ru": "https://yandex.ru/maps/10262/yerevan/search/" + urllib.parse.quote("стоматология") + "/",
 "ya_com": "https://yandex.com/maps/10262/yerevan/search/" + urllib.parse.quote("dentist") + "/",
 "ya_api": "https://search-maps.yandex.ru/v1/?text=" + urllib.parse.quote("стоматология Ереван") + "&lang=ru_RU&type=biz&results=50",
 "g_tbm": "https://www.google.com/search?tbm=map&hl=en&gl=am&q=" + urllib.parse.quote("dentist in Yerevan") + "&pb=!4m12!1m3!1d10000!2d44.51!3d40.18!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!7i20!10b1!12m8!1m1!18b1!2m3!5m1!6e2!20e3!10b1!16b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m42!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e9!2b1!3e2!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!2b1!4b1!9b0!22m6!1sa!2z!3sa!7e81!15i16!24m1!2b1!26m1!1b1",
 "g_maps": "https://www.google.com/maps/search/" + urllib.parse.quote("dentist in Yerevan") + "?hl=en",
}
os.makedirs("probe/out", exist_ok=True)
for k, u in urls.items():
    try:
        req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "ru,en;q=0.8", "Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=30) as r:
            b = r.read()
            if r.headers.get("Content-Encoding") == "gzip": b = gzip.decompress(b)
            t = b.decode("utf-8", "replace"); print(k, r.status, r.url[:120], len(t), "captcha" in t.lower())
    except Exception as e:
        t = repr(e); print(k, "ERR", t[:200])
    open(f"probe/out/{k}.txt", "w").write(t)
