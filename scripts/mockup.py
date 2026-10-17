"""Картинка-витрина сайта компании для рассылки: ноутбук + телефон с сайтом компании, фото по нише.

    python scripts/mockup.py "Название" "категория" [hy|ru] [out.png]

В рассылке: from mockup import Mockups; with Mockups() as m: path = m.render(row, lang)
Нужен playwright с chromium (на раннере: pip install playwright && playwright install chromium).
"""
import base64, hashlib, html, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'data' / 'tg'
import os
PHOTOS, ASSETS, OUT = Path(os.environ.get('MOCKUP_PHOTOS') or ROOT / 'photos'), ROOT / 'mockup', ROOT / 'mockup' / 'out'

# ниша: (папка фото, запасная папка, тексты hy, тексты ru)
# тексты: подзаголовок, кнопка, меню (4), карточки (3), плюсы (3)
N = {
    'restaurant': ('restaurant', 'cafe',
        ('Համեղ ուտեստներ և հարմարավետ մթնոլորտ', 'Ամրագրել սեղան', ['Մենյու', 'Ամրագրում', 'Առաքում', 'Կապ'],
         ['Օրվա առաջարկ', 'Խոհանոցի հիթ', 'Նորույթ'], ['Մենյու 3 լեզվով', 'Սեղանի ամրագրում', 'Գները փոխում եք ինքներդ']),
        ('Вкусная кухня и уютная атмосфера', 'Забронировать стол', ['Меню', 'Бронь', 'Доставка', 'Контакты'],
         ['Блюдо дня', 'Хит кухни', 'Новинка'], ['Меню на 3 языках', 'Бронь столов онлайн', 'Цены меняете сами'])),
    'cafe': ('cafe', 'restaurant',
        ('Սուրճ, դեսերտներ և լավ տրամադրություն', 'Պատվիրել', ['Մենյու', 'Նախաճաշ', 'Առաքում', 'Կապ'],
         ['Սուրճ', 'Դեսերտներ', 'Նախաճաշ'], ['Մենյու 3 լեզվով', 'Պատվեր կայքից', 'Հայտերը՝ Telegram-ում']),
        ('Кофе, десерты и хорошее настроение', 'Заказать', ['Меню', 'Завтраки', 'Доставка', 'Контакты'],
         ['Кофе', 'Десерты', 'Завтраки'], ['Меню на 3 языках', 'Заказ с сайта', 'Заявки в Telegram'])),
    'fastfood': ('fastfood', 'cafe',
        ('Արագ, տաք և համեղ', 'Պատվիրել առաքում', ['Մենյու', 'Կոմբո', 'Առաքում', 'Կապ'],
         ['Բուրգերներ', 'Շաուրմա', 'Պիցցա'], ['Առցանց պատվեր', 'Վճարում քարտով', 'Պատվերները՝ Telegram-ում']),
        ('Быстро, горячо и вкусно', 'Заказать доставку', ['Меню', 'Комбо', 'Доставка', 'Контакты'],
         ['Бургеры', 'Шаурма', 'Пицца'], ['Онлайн-заказ', 'Оплата картой', 'Заказы в Telegram'])),
    'bar': ('bar', 'restaurant',
        ('Կոկտեյլներ, երաժշտություն և լավ ընկերություն', 'Ամրագրել սեղան', ['Մենյու', 'Միջոցառումներ', 'Ամրագրում', 'Կապ'],
         ['Կոկտեյլներ', 'Գարեջուր', 'Խորտիկներ'], ['Մենյու 3 լեզվով', 'Սեղանի ամրագրում', 'Միջոցառումների աֆիշա']),
        ('Коктейли, музыка и хорошая компания', 'Забронировать стол', ['Меню', 'События', 'Бронь', 'Контакты'],
         ['Коктейли', 'Пиво', 'Закуски'], ['Меню на 3 языках', 'Бронь столов', 'Афиша событий'])),
    'hotel': ('hotel', 'guesthouse',
        ('Հարմարավետ հանգիստ Հայաստանում', 'Ամրագրել', ['Համարներ', 'Ծառայություններ', 'Գալերեա', 'Կապ'],
         ['Ստանդարտ', 'Լյուքս', 'Ընտանեկան'], ['Ուղիղ ամրագրում առանց միջնորդի', 'Վճարում քարտով', 'Զբաղվածության օրացույց']),
        ('Уютный отдых в Армении', 'Забронировать', ['Номера', 'Услуги', 'Галерея', 'Контакты'],
         ['Стандарт', 'Люкс', 'Семейный'], ['Прямая бронь без комиссии', 'Оплата картой', 'Шахматка занятости'])),
    'guesthouse': ('guesthouse', 'hotel',
        ('Տնային ջերմություն և գեղեցիկ բնություն', 'Ամրագրել', ['Սենյակներ', 'Բակ', 'Գալերեա', 'Կապ'],
         ['Երկտեղանոց', 'Ընտանեկան', 'Տնակ'], ['Ուղիղ ամրագրում առանց Booking-ի', 'Զբաղվածության օրացույց', 'Հայտերը՝ Telegram-ում']),
        ('Домашний уют и красивая природа', 'Забронировать', ['Комнаты', 'Двор', 'Галерея', 'Контакты'],
         ['Двухместный', 'Семейный', 'Домик'], ['Прямая бронь без Booking', 'Календарь занятости', 'Заявки в Telegram'])),
    'hostel': ('hostel', 'guesthouse',
        ('Հարմար և մատչելի կացություն Երևանում', 'Ամրագրել մահճակալ', ['Սենյակներ', 'Ընդհանուր գոտի', 'Ամրագրում', 'Կապ'],
         ['Ընդհանուր սենյակ', 'Մասնավոր սենյակ', 'Խոհանոց'], ['Ուղիղ ամրագրում', 'Կայք 3 լեզվով', 'Վճարում քարտով']),
        ('Удобное и доступное жильё в Ереване', 'Забронировать место', ['Номера', 'Лаунж', 'Бронь', 'Контакты'],
         ['Общий номер', 'Приватный номер', 'Кухня'], ['Прямая бронь', 'Сайт на 3 языках', 'Оплата картой'])),
    'apartment': ('apartment', 'hotel',
        ('Բնակարաններ օրավարձով', 'Ամրագրել', ['Բնակարաններ', 'Պայմաններ', 'Գալերեա', 'Կապ'],
         ['Հյուրասենյակ', 'Խոհանոց', 'Ննջասենյակ'], ['Ուղիղ ամրագրում', 'Զբաղվածության օրացույց', 'Վճարում քարտով']),
        ('Квартиры посуточно', 'Забронировать', ['Квартиры', 'Условия', 'Галерея', 'Контакты'],
         ['Гостиная', 'Кухня', 'Спальня'], ['Прямая бронь', 'Календарь занятости', 'Оплата картой'])),
    'salon': ('salon', 'barber',
        ('Գեղեցկություն և խնամք պրոֆեսիոնալներից', 'Գրանցվել առցանց', ['Ծառայություններ', 'Վարպետներ', 'Աշխատանքներ', 'Կապ'],
         ['Սանրվածք', 'Մատնահարդարում', 'Խնամք'], ['Առցանց գրանցում 24/7', 'Վարպետների գրաֆիկ', 'Հիշեցումներ հաճախորդներին']),
        ('Красота и уход от профессионалов', 'Записаться онлайн', ['Услуги', 'Мастера', 'Работы', 'Контакты'],
         ['Стрижки', 'Маникюр', 'Уход'], ['Онлайн-запись 24/7', 'График мастеров', 'Напоминания клиентам'])),
    'barber': ('barber', 'salon',
        ('Տղամարդկանց սանրվածքներ և մորուքի խնամք', 'Գրանցվել', ['Ծառայություններ', 'Վարպետներ', 'Աշխատանքներ', 'Կապ'],
         ['Սանրվածք', 'Մորուք', 'Ոճավորում'], ['Առցանց գրանցում 24/7', 'Վարպետների գրաֆիկ', 'Հայտերը՝ Telegram-ում']),
        ('Мужские стрижки и уход за бородой', 'Записаться', ['Услуги', 'Мастера', 'Работы', 'Контакты'],
         ['Стрижка', 'Борода', 'Укладка'], ['Онлайн-запись 24/7', 'График мастеров', 'Заявки в Telegram'])),
    'auto': ('auto', 'auto2',
        ('Ավտոմեքենայի վերանորոգում և սպասարկում', 'Գրանցվել վերանորոգման', ['Ծառայություններ', 'Գրանցում', 'Աշխատանքներ', 'Կապ'],
         ['Ախտորոշում', 'Շարժիչ', 'Անվադողեր'], ['Առցանց գրանցում', 'Բոքսերի զբաղվածություն', 'Հայտերը՝ Telegram-ում']),
        ('Ремонт и обслуживание автомобилей', 'Записаться на ремонт', ['Услуги', 'Запись', 'Работы', 'Контакты'],
         ['Диагностика', 'Двигатель', 'Шины'], ['Онлайн-запись', 'Загрузка боксов', 'Заявки в Telegram'])),
    'dental': ('dental', 'clinic',
        ('Առողջ և գեղեցիկ ժպիտ', 'Գրանցվել ընդունելության', ['Ծառայություններ', 'Բժիշկներ', 'Աշխատանքներ', 'Կապ'],
         ['Բուժում', 'Իմպլանտներ', 'Սպիտակեցում'], ['Առցանց գրանցում', 'Բժիշկների գրաֆիկ', 'Հիշեցումներ պացիենտներին']),
        ('Здоровая и красивая улыбка', 'Записаться на приём', ['Услуги', 'Врачи', 'Работы', 'Контакты'],
         ['Лечение', 'Импланты', 'Отбеливание'], ['Онлайн-запись', 'График врачей', 'Напоминания пациентам'])),
    'clinic': ('clinic', 'dental',
        ('Ձեր առողջությունը՝ վստահելի ձեռքերում', 'Գրանցվել ընդունելության', ['Ծառայություններ', 'Բժիշկներ', 'Անալիզներ', 'Կապ'],
         ['Խորհրդատվություն', 'Ախտորոշում', 'Անալիզներ'], ['Առցանց գրանցում', 'Բժիշկների գրաֆիկ', 'Արդյունքները՝ առցանց']),
        ('Ваше здоровье в надёжных руках', 'Записаться на приём', ['Услуги', 'Врачи', 'Анализы', 'Контакты'],
         ['Консультация', 'Диагностика', 'Анализы'], ['Онлайн-запись', 'График врачей', 'Результаты онлайн'])),
    'travel': ('travel', 'yerevan',
        ('Բացահայտեք Հայաստանը մեզ հետ', 'Ընտրել տուր', ['Տուրեր', 'Ուղղություններ', 'Ամրագրում', 'Կապ'],
         ['Տաթև', 'Սևան', 'Գառնի'], ['Տուրերի կատալոգ', 'Առցանց ամրագրում', 'Կայք 3 լեզվով']),
        ('Откройте Армению вместе с нами', 'Выбрать тур', ['Туры', 'Направления', 'Бронь', 'Контакты'],
         ['Татев', 'Севан', 'Гарни'], ['Каталог туров', 'Онлайн-бронь', 'Сайт на 3 языках'])),
    'market': ('market', 'market',
        ('Թարմ մթերքներ ամեն օր', 'Պատվիրել առաքում', ['Կատալոգ', 'Ակցիաներ', 'Առաքում', 'Կապ'],
         ['Մրգեր և բանջարեղեն', 'Կաթնամթերք', 'Հացաբուլկեղեն'], ['Առցանց խանութ', 'Մնացորդների հաշվառում', 'Առաքում տուն']),
        ('Свежие продукты каждый день', 'Заказать доставку', ['Каталог', 'Акции', 'Доставка', 'Контакты'],
         ['Фрукты и овощи', 'Молочное', 'Выпечка'], ['Онлайн-магазин', 'Учёт остатков', 'Доставка на дом'])),
    'shop': ('shop', 'shop',
        ('Նոր հավաքածու արդեն վաճառքում', 'Գնել', ['Կատալոգ', 'Նորույթներ', 'Զեղչեր', 'Կապ'],
         ['Նորույթներ', 'Հիթեր', 'Զեղչեր'], ['Կատալոգ և զամբյուղ', 'Վճարում ArCa և Idram', 'Պատվերները՝ Telegram-ում']),
        ('Новая коллекция уже в продаже', 'Купить', ['Каталог', 'Новинки', 'Скидки', 'Контакты'],
         ['Новинки', 'Хиты', 'Скидки'], ['Каталог и корзина', 'Оплата ArCa и Idram', 'Заказы в Telegram'])),
}
CAT = [  # подстрока категории (рус.) -> ниша
    ('гостев', 'guesthouse'), ('хостел', 'hostel'), ('апартам', 'apartment'), ('мотел', 'hotel'), ('отел', 'hotel'),
    ('гостиниц', 'hotel'), ('кафе', 'cafe'), ('кофе', 'cafe'), ('фастфуд', 'fastfood'), ('бар', 'bar'), ('паб', 'bar'),
    ('ресторан', 'restaurant'), ('парикмах', 'barber'), ('барбер', 'barber'), ('салон', 'salon'), ('стомат', 'dental'),
    ('клиник', 'clinic'), ('автосерв', 'auto'), ('авто', 'auto'), ('тур', 'travel'), ('супермаркет', 'market'),
    ('продукт', 'market'), ('магазин', 'shop'),
]
TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя', ['a','b','v','g','d','e','e','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','kh','ts','ch','sh','sch','','y','','e','yu','ya']))
TR.update(zip('աբգդեզէըթժիլխծկհձղճմյնշոչպջռսվտրցւփքօֆ', ['a','b','g','d','e','z','e','y','t','zh','i','l','kh','ts','k','h','dz','gh','ch','m','y','n','sh','o','ch','p','j','r','s','v','t','r','ts','v','p','k','o','f']))

# общие подписи блоков сайта
UI = {
    'hy': {'gal': 'Պատկերասրահ', 'rev': 'Կարծիքներ', 'city': 'Երևան', 'call': 'Զանգահարել', 'more': 'Մանրամասն',
           'r1': 'Հիանալի սպասարկում, անպայման կգանք նորից։', 'r2': 'Ամեն ինչ արագ և որակով։ Խորհուրդ եմ տալիս։',
           'about': 'Մեր մասին', 'hours': 'Ամեն օր 10:00–22:00'},
    'ru': {'gal': 'Галерея', 'rev': 'Отзывы', 'city': 'Ереван', 'call': 'Позвонить', 'more': 'Подробнее',
           'r1': 'Отличный сервис, обязательно придём ещё.', 'r2': 'Всё быстро и качественно. Рекомендую!',
           'about': 'О нас', 'hours': 'Ежедневно 10:00–22:00'},
}


def niche_of(category):
    c = (category or '').lower()
    return next((n for k, n in CAT if k in c), 'restaurant')


def _b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode()


def _photos(niche, seed, k=7):
    folder, alt = N[niche][0], N[niche][1]
    fs = sorted((PHOTOS / folder).glob('*.jpg'))
    if len(fs) < 8 and alt != folder:   # мало своих фото: добавляем из соседней ниши
        fs += sorted((PHOTOS / alt).glob('*.jpg'))
    if not fs:
        raise FileNotFoundError(f'нет фото для ниши {niche}')
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    start = h % len(fs)
    order = [fs[(start + i) % len(fs)] for i in range(len(fs))]
    return [order[(i * 3) % len(order)] if len(order) >= 3 * k else order[i % len(order)] for i in range(k)]


def _font_css():
    f = ASSETS / 'fonts'
    faces = [('Noto Sans Armenian', 'NotoSansArmenian-400-armenian', 400), ('Noto Sans Armenian', 'NotoSansArmenian-600-armenian', 700),
             ('Noto Sans', 'NotoSans-400-latin', 400), ('Noto Sans', 'NotoSans-600-latin', 700),
             ('Noto Sans', 'NotoSans-400-cyrillic', 400), ('Noto Sans', 'NotoSans-600-cyrillic', 700)]
    css = ''.join(f"@font-face{{font-family:'{n}';font-weight:{w};src:url(data:font/woff2;base64,{_b64(f / (s + '.woff2'))}) format('woff2')}}"
                  for n, s, w in faces)
    css += f"@font-face{{font-family:'Montserrat';font-weight:100 900;src:url(data:font/ttf;base64,{_b64(f / 'Montserrat.ttf')})}}"
    return css


def page(name, category, lang='hy'):
    """Витрина: ноутбук (главная), окно браузера (галерея и отзывы) и телефон. Без рекламных надписей."""
    niche = niche_of(category)
    sub, cta, menu, cards, _ = N[niche][2] if lang == 'hy' else N[niche][3]
    u = UI[lang]
    ph = [f'data:image/jpeg;base64,{_b64(p)}' for p in _photos(niche, name)]
    e, s, c = html.escape(name), html.escape(sub), html.escape(cta)
    h1 = 64 if len(name) <= 16 else 52 if len(name) <= 26 else 42
    slug = ''.join(TR.get(ch, ch) for ch in name.lower())
    slug = ''.join(ch for ch in slug if ch.isascii() and ch.isalnum())[:18] or 'site'
    nav = ''.join(f'<span>{html.escape(m)}</span>' for m in menu[:3])
    bar = lambda: f'<div class="bb"><i></i><i></i><i></i><div class="url">{slug}.am</div></div>'
    card = lambda i, t: (f'<div class="card"><div class="ci" style="background-image:url({ph[2 + i]})"></div>'
                         f'<div class="ct"><b>{html.escape(t)}</b><span>{u["more"]} →</span></div></div>')
    cards_html = ''.join(card(i, t) for i, t in enumerate(cards))
    gal = ''.join(f'<div class="g g{i}" style="background-image:url({ph[(i + 1) % 7]})"></div>' for i in range(5))
    rev = lambda who, t: f'<div class="rv"><div class="st">★★★★★</div><p>{t}</p><b>{who}</b></div>'
    mob_items = ''.join(f'<div class="mi"><div style="background-image:url({ph[2 + i]})"></div><span>{html.escape(t)}<small>{u["more"]} →</small></span></div>'
                        for i, t in enumerate(cards))
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{_font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1350px;overflow:hidden;font-family:'Noto Sans Armenian','Noto Sans',sans-serif;color:#1d1d22;position:relative;
 background:radial-gradient(700px 520px at 92% 8%,rgba(224,40,58,.16),transparent 70%),radial-gradient(760px 620px at 0% 92%,rgba(70,90,160,.14),transparent 70%),linear-gradient(160deg,#f6f2ee,#e9e7ee)}}
.sh{{box-shadow:0 40px 80px rgba(30,25,40,.28),0 10px 24px rgba(30,25,40,.14)}}
.laptop{{position:absolute;left:58px;top:64px;width:964px}}
.lid{{background:#111114;border-radius:24px 24px 0 0;padding:14px 14px 16px;border:2px solid #2a2a30}}
.screen{{width:932px;height:583px;overflow:hidden;border-radius:6px;background:#fff;position:relative}}
.base{{height:24px;background:linear-gradient(#e2e3e7,#a9aab0);border-radius:0 0 28px 28px;margin:0 -46px;position:relative}}
.base:after{{content:'';position:absolute;left:50%;top:0;width:150px;height:9px;margin-left:-75px;background:#c4c5ca;border-radius:0 0 10px 10px}}
.site{{width:1280px;height:800px;transform:scale(.728);transform-origin:0 0;font-family:inherit;background:#fff}}
.bb{{height:44px;background:#f1f1f4;display:flex;align-items:center;padding:0 18px;gap:9px;border-bottom:1px solid #e3e3e8}}
.bb i{{width:13px;height:13px;border-radius:50%;background:#ff5f57}}.bb i:nth-child(2){{background:#febc2e}}.bb i:nth-child(3){{background:#28c840}}
.url{{margin-left:22px;background:#fff;border-radius:9px;padding:6px 18px;font-size:16px;color:#666;width:420px;font-family:'Noto Sans'}}
.nav{{height:80px;display:flex;align-items:center;justify-content:space-between;padding:0 60px}}
.logo{{font-family:'Montserrat';font-weight:800;font-size:28px;max-width:520px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.logo:before{{content:'';display:inline-block;width:14px;height:14px;border-radius:50%;background:#e0283a;margin-right:12px;vertical-align:2px}}
.nav .m{{display:flex;align-items:center;gap:34px;font-size:18px;color:#444}}
.nb{{background:#1d1d22;color:#fff;padding:12px 24px;border-radius:30px;font-weight:700;font-size:17px}}
.hero{{display:flex;gap:40px;padding:30px 60px 0;height:440px}}
.hl{{flex:1;padding-top:30px}}
.tag{{display:inline-block;background:#fdeaec;color:#c81e2f;font-weight:700;font-size:16px;padding:8px 16px;border-radius:20px;margin-bottom:20px}}
.hl h1{{font-family:'Montserrat','Noto Sans Armenian';font-size:{h1}px;line-height:1.04;font-weight:800;margin-bottom:18px;overflow-wrap:break-word;letter-spacing:-1px}}
.hl p{{font-size:23px;color:#555;margin-bottom:30px;line-height:1.35}}
.btn{{display:inline-block;background:#e0283a;color:#fff;font-weight:700;font-size:20px;padding:17px 32px;border-radius:14px}}
.btn2{{display:inline-block;margin-left:14px;border:2px solid #1d1d22;font-weight:700;font-size:20px;padding:15px 28px;border-radius:14px}}
.rate{{margin-top:28px;font-size:18px;color:#555}}
.hr{{width:560px;position:relative}}
.hp{{position:absolute;inset:0 0 0 0;border-radius:26px;background-size:cover;background-position:center}}
.hs{{position:absolute;left:-46px;bottom:-30px;width:210px;height:150px;border-radius:18px;background-size:cover;background-position:center;border:6px solid #fff;box-shadow:0 14px 30px rgba(0,0,0,.18)}}
.cards{{display:flex;gap:26px;padding:64px 60px 0}}
.card{{flex:1;border-radius:18px;overflow:hidden;background:#fff;box-shadow:0 8px 26px rgba(0,0,0,.10);display:flex;align-items:center}}
.ci{{width:130px;height:104px;background-size:cover;background-position:center;flex:none}}
.ct{{padding:0 18px;display:flex;flex-direction:column;gap:6px}}.ct b{{font-size:20px}}.ct span{{font-size:15px;color:#e0283a;font-weight:700}}
.win{{position:absolute;left:44px;top:752px;width:650px;height:520px;border-radius:18px;overflow:hidden;background:#fff}}
.wsite{{width:1300px;height:1040px;transform:scale(.5);transform-origin:0 0;background:#fff}}
.wsite .bb{{height:56px}}.wsite .url{{font-size:20px;width:520px}}
.sec{{padding:44px 60px 0}}
.sec h3{{font-family:'Montserrat','Noto Sans Armenian';font-size:44px;font-weight:800;margin-bottom:26px}}
.grid{{display:grid;grid-template-columns:1.4fr 1fr 1fr;grid-template-rows:230px 230px;gap:18px}}
.g{{border-radius:20px;background-size:cover;background-position:center}}.g0{{grid-row:span 2}}
.revs{{display:flex;gap:22px}}
.rv{{flex:1;background:#f6f5f8;border-radius:20px;padding:26px 28px}}
.st{{color:#f5a623;font-size:26px;letter-spacing:3px;margin-bottom:10px}}.rv p{{font-size:23px;line-height:1.35;margin-bottom:12px}}.rv b{{font-size:20px;color:#777}}
.phone{{position:absolute;right:52px;top:640px;width:318px;height:648px;background:#111114;border-radius:50px;padding:12px;border:2px solid #34343b}}
.ps{{width:100%;height:100%;border-radius:39px;overflow:hidden;background:#fff;position:relative}}
.notch{{position:absolute;top:10px;left:50%;width:96px;height:26px;margin-left:-48px;background:#111114;border-radius:16px;z-index:5}}
.mob{{width:390px;height:772px;transform:scale(.7538);transform-origin:0 0}}
.mtop{{height:96px;display:flex;align-items:flex-end;justify-content:space-between;padding:0 22px 14px;font-family:'Montserrat';font-weight:800;font-size:21px}}
.mtop span{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:290px}}
.mh{{margin:0 16px;height:300px;border-radius:24px;background-size:cover;background-position:center;position:relative;overflow:hidden}}
.mh:after{{content:'';position:absolute;inset:0;background:linear-gradient(180deg,transparent 35%,rgba(0,0,0,.78))}}
.mc{{position:absolute;z-index:1;left:20px;right:20px;bottom:20px;color:#fff}}
.mc h2{{font-size:25px;line-height:1.18;font-weight:700;margin-bottom:14px}}
.mc .btn{{font-size:18px;padding:13px 20px;display:block;text-align:center}}
.ml{{padding:18px 16px 0}}
.mi{{display:flex;align-items:center;gap:14px;margin-bottom:14px;background:#f6f5f8;border-radius:18px;padding:8px}}
.mi div{{width:96px;height:72px;border-radius:13px;background-size:cover;background-position:center;flex:none}}
.mi span{{font-weight:700;font-size:20px;display:flex;flex-direction:column;gap:4px}}.mi small{{font-size:14px;color:#e0283a}}
.mbar{{margin:4px 16px 0;background:#1d1d22;color:#fff;border-radius:18px;padding:18px 20px;font-size:18px;display:flex;justify-content:space-between}}.mbar b{{color:#ff6b78}}
.foot{{position:absolute;left:0;right:0;bottom:22px;text-align:center;font-size:0}}
.foot img{{height:34px;mix-blend-mode:multiply;opacity:.9}}
</style></head><body>
<div class="laptop"><div class="lid sh"><div class="screen"><div class="site">
 {bar()}
 <div class="nav"><div class="logo">{e}</div><div class="m">{nav}<span class="nb">{c}</span></div></div>
 <div class="hero"><div class="hl"><h1>{e}</h1><p>{s}</p><span class="btn">{c}</span><span class="btn2">{u["call"]}</span>
  <div class="rate">🕘 {u["hours"]}</div></div>
  <div class="hr"><div class="hp" style="background-image:url({ph[0]})"></div><div class="hs" style="background-image:url({ph[1]})"></div></div></div>
 <div class="cards">{cards_html}</div>
</div></div></div><div class="base"></div></div>
<div class="win sh"><div class="wsite">{bar()}
 <div class="sec"><h3>{u["gal"]}</h3><div class="grid">{gal}</div></div>
 <div class="sec"><h3>{u["rev"]}</h3><div class="revs">{rev("Anna M.", u["r1"])}{rev("Davit K.", u["r2"])}</div></div>
</div></div>
<div class="phone sh"><div class="ps"><div class="notch"></div><div class="mob">
 <div class="mtop"><span>{e}</span><span>☰</span></div>
 <div class="mh" style="background-image:url({ph[1]})"><div class="mc"><h2>{s}</h2><span class="btn">{c}</span></div></div>
 <div class="ml">{mob_items}</div>
 <div class="mbar"><span>{html.escape(menu[0])}</span><b>📞 {u["call"]}</b></div>
</div></div></div>
<div class="foot"><img src="data:image/png;base64,{_b64(ASSETS / 'logo-light.png')}"></div>
</body></html>'''


class Mockups:
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch()
        self.pg = self.browser.new_page(viewport={'width': 1080, 'height': 1350})
        OUT.mkdir(parents=True, exist_ok=True)
        return self

    def render(self, name, category, lang='hy', out=None):
        out = Path(out or OUT / f'{hashlib.md5((name + lang).encode()).hexdigest()[:12]}.jpg')
        self.pg.set_content(page(name, category, lang), wait_until='load')
        self.pg.evaluate('document.fonts.ready')
        self.pg.screenshot(path=str(out), type='jpeg', quality=88)
        return out

    def __exit__(self, *a):
        self.browser.close(); self.pw.stop()


if __name__ == '__main__':
    a = sys.argv[1:]
    with Mockups() as m:
        print(m.render(a[0], a[1], a[2] if len(a) > 2 else 'hy', a[3] if len(a) > 3 else None))
