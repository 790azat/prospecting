"""Фото по нишам для картинок «ваш будущий сайт» (Openverse, лицензии для коммерческого использования).
Запуск на раннере GitHub (из песочницы стоки недоступны): python scripts/fetch_photos.py"""
import io, json, sys, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / 'data' / 'tg' / 'photos'
Q = {
    'guesthouse': ['guest house bedroom interior', 'cozy cottage room', 'guesthouse garden terrace'],
    'restaurant': ['restaurant interior dinner', 'restaurant table setting', 'grilled kebab plate'],
    'cafe': ['cafe interior', 'cappuccino latte art', 'croissant coffee breakfast'],
    'fastfood': ['burger fries', 'shawarma wrap', 'pizza slice'],
    'hotel': ['hotel room bed', 'hotel lobby', 'hotel pool'],
    'hostel': ['hostel dormitory bunk beds', 'hostel common room', 'backpackers lounge'],
    'salon': ['beauty salon interior', 'manicure nails', 'hair stylist salon'],
    'barber': ['barbershop', 'barber haircut beard', 'barber chair'],
    'auto': ['car repair garage mechanic', 'auto service car lift', 'mechanic engine repair'],
    'dental': ['dental clinic chair', 'dentist patient', 'dental office'],
    'clinic': ['medical clinic reception', 'doctor consultation', 'hospital corridor modern'],
    'bar': ['cocktail bar', 'pub interior beer', 'wine glasses bar'],
    'travel': ['armenia mountains', 'tatev monastery', 'lake sevan', 'garni temple'],
    'market': ['grocery store shelves', 'supermarket fruit vegetables', 'grocery shopping basket'],
    'apartment': ['apartment living room interior', 'modern apartment kitchen', 'apartment bedroom'],
    'shop': ['clothing store rack', 'fashion boutique', 'jeans denim folded'],
    'auto2': ['car service center workshop', 'tire change wheel', 'car diagnostics mechanic', 'auto repair shop interior'],
    'yerevan': ['yerevan city', 'yerevan cascade', 'mount ararat'],
}
UA = {'User-Agent': 'evnweb-mockups/1.0 (vip.azatazat@gmail.com)'}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()


def main():
    only = set(sys.argv[1:])
    for niche, queries in Q.items():
        if only and niche not in only: continue
        d = OUT / niche; d.mkdir(parents=True, exist_ok=True)
        credits, n = [], 0
        for q in queries:
            api = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode(
                {'q': q, 'license_type': 'commercial', 'size': 'large', 'page_size': 8, 'mature': 'false'})
            try:
                res = json.loads(get(api))['results']
            except Exception as e:
                print('search fail', q, e); continue
            for r in res:
                if 'rawpixel' in (r.get('foreign_landing_url') or ''): continue   # у rawpixel водяные знаки
                try:
                    im = Image.open(io.BytesIO(get(r['url']))).convert('RGB')
                except Exception as e:
                    print('img fail', r['url'][:80], e); continue
                if im.width < 800 or im.height < 500: continue
                im.thumbnail((1400, 1400))
                n += 1
                name = f'{n:02d}.jpg'
                im.save(d / name, quality=82)
                credits.append({'file': name, 'q': q, 'title': r.get('title'), 'creator': r.get('creator'),
                                'license': r.get('license'), 'url': r.get('foreign_landing_url')})
            time.sleep(1)
        (d / 'credits.json').write_text(json.dumps(credits, ensure_ascii=False, indent=1))
        print(niche, n)


if __name__ == '__main__':
    main()
