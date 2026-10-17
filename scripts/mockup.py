"""Картинка «так может выглядеть ваш сайт» для рассылки: ноутбук + телефон с сайтом компании, фото по нише.

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
    'auto': ('auto', 'auto',
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
TITLE = {'hy': 'Այսպես կարող է տեսք ունենալ<br><b>{name}</b>-ի կայքը', 'ru': 'Так может выглядеть сайт<br><b>{name}</b>'}
NOTE = {'hy': 'Կայքը՝ համակարգչում և հեռախոսում', 'ru': 'Сайт на компьютере и в телефоне'}


def niche_of(category):
    c = (category or '').lower()
    return next((n for k, n in CAT if k in c), 'restaurant')


def _b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode()


def _photos(niche, seed):
    folder, alt = N[niche][0], N[niche][1]
    fs = sorted((PHOTOS / folder).glob('*.jpg')) or sorted((PHOTOS / alt).glob('*.jpg'))
    if not fs:
        raise FileNotFoundError(f'нет фото для ниши {niche}')
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    start = h % len(fs)
    return [fs[(start + i * 3) % len(fs)] for i in range(4)]   # 4 разных (если фото хватает)


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
    niche = niche_of(category)
    sub, cta, menu, cards, plus = N[niche][2] if lang == 'hy' else N[niche][3]
    ph = [f'data:image/jpeg;base64,{_b64(p)}' for p in _photos(niche, name)]
    e = html.escape(name)
    h1 = 66 if len(name) <= 18 else 54 if len(name) <= 28 else 44
    tf = 50 if len(name) <= 26 else 42
    nav = ''.join(f'<span>{html.escape(m)}</span>' for m in menu)
    card = lambda i, t: f'<div class="card"><div class="ci" style="background-image:url({ph[(i + 1) % 4]})"></div><div class="ct">{html.escape(t)}</div></div>'
    cards_html = ''.join(card(i, t) for i, t in enumerate(cards))
    plus_html = ''.join(f'<div class="pl"><i>✓</i>{html.escape(p)}</div>' for p in plus)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{_font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1350px;overflow:hidden;font-family:'Noto Sans Armenian','Noto Sans',sans-serif;color:#fff;
 background:radial-gradient(900px 700px at 85% 10%,#5a0f17 0%,rgba(90,15,23,0) 70%),radial-gradient(800px 600px at 0% 100%,#3b0a10 0%,rgba(59,10,16,0) 70%),#16161a}}
.title{{position:absolute;left:70px;right:70px;top:64px;font-size:{tf}px;line-height:1.22;font-weight:700;letter-spacing:-.5px}}
.title b{{color:#ff4d5e}}
.laptop{{position:absolute;left:50px;top:270px;width:900px}}
.lid{{background:#0c0c0e;border-radius:22px 22px 0 0;padding:16px 16px 18px;border:2px solid #2c2c33}}
.screen{{width:864px;height:540px;overflow:hidden;border-radius:6px;background:#fff;position:relative}}
.base{{height:22px;background:linear-gradient(#cfd0d4,#9b9ca2);border-radius:0 0 26px 26px;margin:0 -40px}}
.site{{width:1280px;height:800px;transform:scale(.675);transform-origin:0 0;color:#1a1a1a;font-family:inherit}}
.nav{{height:84px;display:flex;align-items:center;justify-content:space-between;padding:0 56px;position:absolute;top:0;left:0;right:0;z-index:2;color:#fff}}
.logo{{font-family:'Montserrat';font-weight:800;font-size:30px;letter-spacing:.5px;max-width:520px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.nav .m span{{margin-left:34px;font-size:19px;opacity:.95}}
.hero{{height:560px;background-size:cover;background-position:center;position:relative}}
.hero:after{{content:'';position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.72),rgba(0,0,0,.15))}}
.hc{{position:absolute;left:56px;top:190px;z-index:1;color:#fff;max-width:720px}}
.hc h1{{font-family:'Montserrat','Noto Sans Armenian';font-size:{h1}px;line-height:1.05;font-weight:800;margin-bottom:18px;overflow-wrap:break-word}}
.hc p{{font-size:26px;opacity:.95;margin-bottom:30px}}
.btn{{display:inline-block;background:#e0283a;color:#fff;font-weight:700;font-size:22px;padding:18px 34px;border-radius:12px}}
.cards{{display:flex;gap:24px;padding:28px 56px;background:#fff}}
.card{{flex:1;border-radius:14px;overflow:hidden;box-shadow:0 6px 20px rgba(0,0,0,.12)}}
.ci{{height:120px;background-size:cover;background-position:center}}
.ct{{padding:12px 16px;font-weight:700;font-size:20px}}
.phone{{position:absolute;right:46px;top:600px;width:300px;height:620px;background:#0c0c0e;border-radius:46px;padding:12px;border:2px solid #34343b;box-shadow:0 30px 60px rgba(0,0,0,.55)}}
.ps{{width:100%;height:100%;border-radius:36px;overflow:hidden;background:#fff;position:relative}}
.mob{{width:390px;height:780px;transform:scale(.7077);transform-origin:0 0;color:#1a1a1a}}
.mh{{height:430px;background-size:cover;background-position:center;position:relative}}
.mh:after{{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.55),rgba(0,0,0,.2) 40%,rgba(0,0,0,.75))}}
.mt{{position:absolute;z-index:1;left:22px;right:22px;top:26px;display:flex;justify-content:space-between;color:#fff;font-family:'Montserrat';font-weight:800;font-size:22px}}
.mt span{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:280px}}
.mc{{position:absolute;z-index:1;left:22px;right:22px;bottom:26px;color:#fff}}
.mc h2{{font-family:'Noto Sans Armenian','Noto Sans';font-size:27px;line-height:1.15;font-weight:700;margin-bottom:16px}}
.mc .btn{{font-size:19px;padding:14px 22px;display:block;text-align:center}}
.ml{{padding:18px 22px}}
.mi{{display:flex;align-items:center;gap:16px;margin-bottom:16px;font-weight:700;font-size:21px}}
.mbar{{margin:6px 22px 0;background:#f3f3f5;border-radius:14px;padding:16px;font-size:17px;color:#555;display:flex;justify-content:space-between}}
.mbar b{{color:#e0283a}}
.mi div{{width:110px;height:84px;border-radius:12px;background-size:cover;background-position:center;flex:none}}
.plus{{position:absolute;left:70px;top:975px;width:580px}}
.pl{{font-size:30px;font-weight:700;margin-bottom:26px;display:flex;gap:16px;align-items:flex-start;line-height:1.25}}
.pl i{{font-style:normal;color:#fff;background:#e0283a;border-radius:50%;width:40px;height:40px;flex:none;display:flex;align-items:center;justify-content:center;font-size:22px;margin-top:-2px}}
.note{{position:absolute;left:70px;top:915px;font-size:24px;color:#b9b9c2}}
.foot{{position:absolute;left:70px;bottom:56px;display:flex;align-items:center;gap:22px}}
.foot img{{height:58px;mix-blend-mode:lighten}}
.foot span{{font-size:28px;font-weight:700;color:#d8d8de}}
</style></head><body>
<div class="title">{TITLE[lang].format(name=e)}</div>
<div class="laptop"><div class="lid"><div class="screen"><div class="site">
 <div class="nav"><div class="logo">{e}</div><div class="m">{nav}</div></div>
 <div class="hero" style="background-image:url({ph[0]})"><div class="hc"><h1>{e}</h1><p>{html.escape(sub)}</p><span class="btn">{html.escape(cta)}</span></div></div>
 <div class="cards">{cards_html}</div>
</div></div></div><div class="base"></div></div>
<div class="phone"><div class="ps"><div class="mob">
 <div class="mh" style="background-image:url({ph[1]})"><div class="mt"><span>{e}</span><span>☰</span></div>
 <div class="mc"><h2>{html.escape(sub)}</h2><span class="btn">{html.escape(cta)}</span></div></div>
 <div class="ml">{''.join(f'<div class="mi"><div style="background-image:url({ph[(i + 2) % 4]})"></div>{html.escape(t)}</div>' for i, t in enumerate(cards))}</div>
 <div class="mbar"><span>{html.escape(menu[3])}</span><b>{html.escape(cta)} →</b></div>
</div></div></div>
<div class="note">{NOTE[lang]}</div>
<div class="plus">{plus_html}</div>
<div class="foot"><img src="data:image/png;base64,{_b64(ASSETS / 'logo.png')}"><span>evnweb.am</span></div>
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
