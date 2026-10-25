"""Уникальный дизайн главной страницы сайта для бизнеса: одна картинка с их логотипом (Azat 10-23).

    python scripts/design.py "Название" "категория" out.jpg [город]

Каждому бизнесу свой вариант: стиль шапки и первого экрана, палитра, шрифты, знак логотипа и порядок блоков
выбираются по названию (md5), так что у двух соседей по очереди дизайны разные, а у одного бизнеса всегда одинаковый.
Логотип: своего логотипа у бизнесов из очереди нет, поэтому рисуем знак-монограмму и надпись с их названием.
"""
import hashlib, html, io, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mockup import N, niche_of, _photos, _b64

FONTS = Path(__file__).resolve().parent.parent / 'data' / 'tg' / 'design' / 'fonts'
W = 1440

# палитры: фон, поверхность, текст, приглушённый текст, акцент, тёмный блок
PAL = {
    'food':    [('#fbf6ef', '#f1e7d8', '#2a1d14', '#7a6656', '#b4532a', '#2a1d14'),
                ('#0f0d0b', '#1b1714', '#f4ece1', '#b9ab98', '#d9a35b', '#1b1714'),
                ('#f6f3ee', '#e9e2d6', '#1f2a24', '#66706a', '#3f6b4f', '#1f2a24'),
                ('#fff8f1', '#ffe9d6', '#2b1a12', '#86695a', '#e0542e', '#3a1f14'),
                ('#f4efe9', '#e6ddd2', '#26201c', '#7c7068', '#8c2f39', '#26201c')],
    'stay':    [('#f7f4ef', '#ebe4d9', '#1e2a2f', '#66737a', '#a7774a', '#1e2a2f'),
                ('#f3f6f5', '#e1ebe8', '#14302b', '#5f7470', '#2f7a68', '#14302b'),
                ('#0e1416', '#172024', '#eef2f1', '#a5b3b4', '#c9a46a', '#172024'),
                ('#faf7f2', '#efe6da', '#2f2620', '#80736a', '#6b8f71', '#2f2620'),
                ('#f2f4f8', '#e2e7f0', '#162033', '#5d6a80', '#c58b4e', '#162033')],
    'booking': [('#fbf7f6', '#f3e6e3', '#2b1f23', '#806d73', '#b8566f', '#2b1f23'),
                ('#f5f5f3', '#e8e6e1', '#161616', '#6b6b6b', '#c49a5a', '#161616'),
                ('#0f0f10', '#1a1a1c', '#f2f0ec', '#a9a6a0', '#c8a96a', '#1a1a1c'),
                ('#f3f7fa', '#e1ecf3', '#13293d', '#5b7184', '#2a7fb8', '#13293d'),
                ('#f7f5fb', '#ebe6f5', '#251f36', '#6f6884', '#7a5bc4', '#251f36')],
    'shop':    [('#f7f7f5', '#ebebe7', '#151515', '#6c6c68', '#e0283f', '#151515'),
                ('#fbf8f3', '#f0e8dc', '#2a2420', '#7d736b', '#c06b3e', '#2a2420'),
                ('#f2f6f2', '#e1ebe1', '#18291c', '#62735f', '#3d8b4a', '#18291c')],
    'travel':  [('#f4f7f8', '#e3ecef', '#13262e', '#5d727a', '#d97a3a', '#13262e'),
                ('#faf6ef', '#efe5d4', '#2a2218', '#7d7160', '#a8572c', '#2a2218')],
}
GROUP = {'restaurant': 'food', 'cafe': 'food', 'fastfood': 'food', 'bar': 'food',
         'hotel': 'stay', 'guesthouse': 'stay', 'hostel': 'stay', 'apartment': 'stay',
         'salon': 'booking', 'barber': 'booking', 'auto': 'booking', 'dental': 'booking', 'clinic': 'booking',
         'market': 'shop', 'shop': 'shop', 'travel': 'travel'}

# тексты блоков (hy): о нас, преимущества (3), отзывы (2), контакты
TXT = {
    'food': ('Մեր մասին', 'Մենք պատրաստում ենք թարմ մթերքներից՝ հայկական հյուրընկալությամբ։ Յուրաքանչյուր ուտեստ սիրով է, իսկ մթնոլորտը՝ ջերմ ու հարմարավետ։',
             [('Թարմ մթերքներ', 'Ամեն առավոտ՝ տեղական ֆերմաներից'), ('Արագ սպասարկում', 'Պատվերը սեղանին՝ 15 րոպեում'), ('Առաքում', 'Տաք ուտեստներ ձեր դռան մոտ')],
             'Մենյու', 'Ամրագրեք սեղան այսօր'),
    'stay': ('Մեր մասին', 'Հարմարավետ համարներ, համեղ նախաճաշ և հանգիստ մթնոլորտ։ Մենք սիրով կօգնենք պլանավորել ձեր հանգիստը Հայաստանում։',
             [('Նախաճաշ', 'Տնական նախաճաշ ամեն առավոտ'), ('Wi‑Fi և կայանատեղի', 'Անվճար՝ բոլոր հյուրերի համար'), ('Տրանսֆեր', 'Օդանավակայանից և էքսկուրսիաներ')],
             'Համարներ', 'Ամրագրեք ձեր հանգիստը'),
    'booking': ('Մեր մասին', 'Փորձառու մասնագետներ, ժամանակակից սարքավորումներ և անհատական մոտեցում յուրաքանչյուր հաճախորդի։',
                [('Փորձառու թիմ', 'Տարիների փորձ և վստահություն'), ('Առցանց գրանցում', 'Ընտրեք ազատ ժամը 24/7'), ('Երաշխիք', 'Որակ, որին կարող եք վստահել')],
                'Ծառայություններ', 'Գրանցվեք հարմար ժամին'),
    'shop': ('Մեր մասին', 'Որակյալ ապրանքներ, հարմար գներ և արագ առաքում ամբողջ Երևանում։',
             [('Արագ առաքում', 'Նույն օրը՝ Երևանում'), ('Վճարում քարտով', 'ArCa, Visa, Idram'), ('Վերադարձ', '14 օր՝ առանց հարցերի')],
             'Կատալոգ', 'Պատվիրեք հիմա'),
    'travel': ('Մեր մասին', 'Մենք ցույց կտանք Հայաստանի ամենագեղեցիկ վայրերը՝ փորձառու ուղեկցորդներով և հարմարավետ տրանսպորտով։',
               [('Փորձառու ուղեկցորդներ', '3 լեզվով'), ('Փոքր խմբեր', 'Հարմարավետ և անհատական'), ('Ամեն օր', 'Տուրեր ամբողջ տարին')],
               'Տուրեր', 'Ընտրեք ձեր տուրը'),
}
CITY = {'Ереван': 'Երևան', 'Дилижан': 'Դիլիջան', 'Гюмри': 'Գյումրի', 'Севан': 'Սևան', 'Ванадзор': 'Վանաձոր',
        'Ехегнадзор': 'Եղեգնաձոր', 'Горис': 'Գորիս', 'Цахкадзор': 'Ծաղկաձոր', 'Джермук': 'Ջերմուկ'}

REV = [('Անի Մ.', 'Շատ գոհ ենք, ամեն ինչ հիանալի էր։ Անպայման կգանք նորից։'),
       ('Դավիթ Ք.', 'Ջերմ ընդունելություն և բարձր որակ։ Խորհուրդ եմ տալիս։'),
       ('Լիլիթ Հ.', 'Հիանալի վայր և ուշադիր անձնակազմ։'),
       ('Արամ Գ.', 'Արագ, որակով և սիրով։ Շնորհակալություն։')]


def _font_css():
    def face(fam, f, wght='100 900'):
        return f"@font-face{{font-family:'{fam}';font-weight:{wght};src:url(data:font/ttf;base64,{_b64(FONTS / f)})}}"
    return ''.join([face('Playfair', 'PlayfairDisplay.ttf', '400 900'), face('Inter', 'Inter.ttf'), face('Manrope', 'Manrope.ttf', '200 800'),
                    face('NSerifArm', 'NotoSerifArmenian.ttf'), face('NSansArm', 'NotoSansArmenian.ttf')])


def _initials(name):
    words = [w for w in ''.join(ch if ch.isalnum() else ' ' for ch in name).split() if w.lower() not in ('the', 'hotel', 'cafe', 'restaurant', 'and', 'by')]
    words = words or name.split() or ['E']
    return (words[0][0] + (words[1][0] if len(words) > 1 else '')).upper()


def logo_svg(name, shape, acc, fg, serif):
    """Знак: форма + монограмма (свой у каждого бизнеса)."""
    ini = html.escape(_initials(name))
    font = "Playfair,NSerifArm,serif" if serif else "Manrope,NSansArm,sans-serif"
    fs = 30 if len(ini) == 1 else 24
    shapes = {
        'circle': f'<circle cx="32" cy="32" r="29" fill="none" stroke="{acc}" stroke-width="2.5"/><circle cx="32" cy="32" r="24" fill="{acc}"/>',
        'arch': f'<path d="M6 60V30a26 26 0 0 1 52 0v30z" fill="{acc}"/>',
        'diamond': f'<rect x="12" y="12" width="40" height="40" rx="6" transform="rotate(45 32 32)" fill="{acc}"/>',
        'leaf': f'<path d="M32 4C50 14 60 30 60 60H4C4 30 14 14 32 4z" fill="{acc}"/>',
        'square': f'<rect x="4" y="4" width="56" height="56" rx="16" fill="{acc}"/>',
        'ring': f'<circle cx="32" cy="32" r="27" fill="none" stroke="{acc}" stroke-width="5"/>',
    }
    tc = acc if shape == 'ring' else '#fff'
    return (f'<svg width="64" height="64" viewBox="0 0 64 64">{shapes[shape]}'
            f'<text x="32" y="{39 if shape != "arch" else 44}" text-anchor="middle" font-family="{font}" font-weight="700" font-size="{fs}" fill="{tc}">{ini}</text></svg>')


def brand(name):
    """Короткое имя для логотипа и заголовка: без хвостов вида « - Pediatric dentist ...» и «(...)»."""
    import re, unicodedata
    n = unicodedata.normalize('NFKC', name)
    n = re.split(r'\s[-–—|/]\s|\(|,', n)[0].strip()
    generic = {'hotel', 'hostel', 'cafe', 'restaurant', 'guest house', 'guesthouse', 'bar', 'salon'}
    return n if len(n) >= 2 and n.lower() not in generic else name.strip()


def page(name, category, city=''):
    name = brand(name)
    niche = niche_of(category)
    grp = GROUP.get(niche, 'food')
    sub, cta, menu, cards, plus = N[niche][2]
    about_h, about, feats, sec_h, cta_h = TXT[grp]
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    pick = lambda seq, k: seq[(h >> k) % len(seq)]
    bg, surf, fg, mut, acc, dark = pick(PAL[grp], 3)
    serif = pick([True, False, True] if grp in ('food', 'stay') else [False, True, False], 7)
    hero = pick(['full', 'split', 'arch', 'collage'], 11)
    shape = pick(['circle', 'arch', 'diamond', 'leaf', 'square', 'ring'], 17)
    radius = pick([0, 6, 18, 28], 23)
    ph = [f'data:image/jpeg;base64,{_b64(p)}' for p in _photos(niche, name, 8)]
    e, s, c = html.escape(name), html.escape(sub), html.escape(cta)
    place = CITY.get(city, 'Երևան')
    disp = "'Playfair','NSerifArm',serif" if serif else "'Manrope','NSansArm',sans-serif"
    body = "'Inter','NSansArm',sans-serif"
    n = len(name)
    h1 = 96 if n <= 12 else 80 if n <= 20 else 64 if n <= 30 else 52
    logo = f'<div class="logo">{logo_svg(name, shape, acc, fg, serif)}<span>{e}</span></div>'
    nav = ''.join(f'<a>{html.escape(m)}</a>' for m in menu)
    header = f'<header>{logo}<nav>{nav}</nav><a class="btn sm">{c}</a></header>'

    if hero == 'full':
        hero_html = f'''<section class="hero full" style="background-image:linear-gradient(180deg,rgba(0,0,0,.35),rgba(0,0,0,.55)),url({ph[0]})">
 {header.replace('<header>', '<header class="over">')}
 <div class="hc"><div class="kick">{place} · Հայաստան</div><h1>{e}</h1><p>{s}</p><a class="btn">{c}</a><a class="btn ghost">Զանգահարել</a></div></section>'''
    elif hero == 'split':
        hero_html = f'''{header}<section class="hero split"><div class="hl"><div class="kick">{place} · Հայաստան</div><h1>{e}</h1><p>{s}</p>
 <div><a class="btn">{c}</a><a class="btn line">Զանգահարել</a></div><div class="stats">{''.join(f'<div><b>{i + 1:02d}</b>{html.escape(p)}</div>' for i, p in enumerate(plus))}</div></div>
 <div class="hr"><div class="img" style="background-image:url({ph[0]})"></div><div class="img2" style="background-image:url({ph[1]})"></div></div></section>'''
    elif hero == 'arch':
        hero_html = f'''{header}<section class="hero arch"><div class="hl"><div class="kick">{place} · Հայաստան</div><h1>{e}</h1><p>{s}</p><a class="btn">{c}</a></div>
 <div class="archimg" style="background-image:url({ph[0]})"></div><div class="badge">{html.escape(plus[0])}</div></section>'''
    else:
        hero_html = f'''{header}<section class="hero collage"><div class="kick c">{place} · Հայաստան</div><h1 class="c">{e}</h1><p class="c">{s}</p><div class="c"><a class="btn">{c}</a></div>
 <div class="row">{''.join(f'<div class="img" style="background-image:url({ph[i]})"></div>' for i in range(4))}</div></section>'''

    feats_html = ''.join(f'<div class="ft"><i>{i + 1:02d}</i><b>{html.escape(a)}</b><span>{html.escape(b)}</span></div>' for i, (a, b) in enumerate(feats))
    cards_html = ''.join(f'<div class="card"><div class="img" style="background-image:url({ph[2 + i]})"></div><div class="ct"><b>{html.escape(t)}</b>'
                         f'<span>Մանրամասն →</span></div></div>' for i, t in enumerate(cards))
    gal = ''.join(f'<div class="g g{i}" style="background-image:url({ph[(i + 4) % 8]})"></div>' for i in range(4))
    revs = ''.join(f'<div class="rv"><div class="st">★★★★★</div><p>«{html.escape(t)}»</p><b>{html.escape(w)}</b></div>'
                   for w, t in [REV[(h >> 29) % 4], REV[((h >> 29) + 1) % 4], REV[((h >> 29) + 2) % 4]])
    plus_html = ''.join(f'<li>{html.escape(p)}</li>' for p in plus)
    order = pick([['about', 'cards', 'gallery', 'reviews'], ['cards', 'about', 'reviews', 'gallery'], ['about', 'gallery', 'cards', 'reviews']], 31)
    blocks = {
        'about': f'''<section class="about"><div class="aimg" style="background-image:url({ph[6]})"></div><div><div class="kick">{about_h}</div>
          <h2>{e}</h2><p class="lead">{html.escape(about)}</p><div class="feats">{feats_html}</div></div></section>''',
        'cards': f'''<section class="cards"><div class="sh"><div><div class="kick">{e}</div><h2>{sec_h}</h2></div><a class="btn line">Տեսնել բոլորը</a></div>
          <div class="grid3">{cards_html}</div></section>''',
        'gallery': f'''<section class="gallery"><div class="gal">{gal}</div></section>''',
        'reviews': f'''<section class="reviews"><div class="kick c">Կարծիքներ</div><h2 class="c">Ինչ են ասում մեր հյուրերը</h2><div class="grid3">{revs}</div></section>''',
    }
    main = ''.join(blocks[b] for b in order)
    r = radius
    dark_txt = '#f4f1ec'
    return f'''<!doctype html><html lang="hy"><head><meta charset="utf-8"><style>{_font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;background:{bg};color:{fg};font-family:{body};font-size:18px;line-height:1.55}}
a{{text-decoration:none;color:inherit}}
header{{display:flex;align-items:center;justify-content:space-between;padding:28px 80px;gap:40px}}
header.over{{color:#fff}} header.over nav a{{color:#fff}}
.logo{{display:flex;align-items:center;gap:14px;font-family:{disp};font-weight:700;font-size:28px;letter-spacing:.3px;white-space:nowrap;max-width:560px;overflow:hidden}}
.logo svg{{flex:none}}
nav{{display:flex;gap:36px;font-size:17px;color:{mut};font-weight:500}}
.btn{{display:inline-block;background:{acc};color:#fff;padding:18px 34px;border-radius:{max(r, 4)}px;font-weight:600;font-size:18px;margin-right:12px}}
.btn.sm{{padding:13px 24px;font-size:16px;margin:0}}
.btn.line{{background:transparent;color:{fg};border:1.5px solid {fg}}}
.btn.ghost{{background:rgba(255,255,255,.12);border:1.5px solid rgba(255,255,255,.6)}}
.kick{{text-transform:uppercase;letter-spacing:.22em;font-size:14px;font-weight:600;color:{acc};margin-bottom:18px}}
h1{{font-family:{disp};font-size:{h1}px;line-height:1.02;font-weight:700;letter-spacing:-1px;margin-bottom:24px;overflow-wrap:break-word}}
h2{{font-family:{disp};font-size:52px;line-height:1.1;font-weight:700;margin-bottom:22px}}
.c{{text-align:center;margin-left:auto;margin-right:auto}}
.hero.full{{padding:0;height:900px;background-size:cover;background-position:center;color:#fff;position:relative}}
.hero.full .hc{{position:absolute;left:80px;bottom:110px;max-width:860px}} .hero.full .kick{{color:#fff;opacity:.85}}
.hero.full p{{font-size:24px;margin-bottom:36px;opacity:.92;max-width:640px}}
.hero.split{{display:grid;grid-template-columns:1fr 1fr;gap:60px;padding:50px 80px 90px;align-items:center}}
.hero.split p,.hero.arch p{{font-size:22px;color:{mut};margin-bottom:34px;max-width:560px}}
.hr{{position:relative;height:640px}}
.hr .img{{position:absolute;inset:0 0 60px 60px;background-size:cover;background-position:center;border-radius:{r}px}}
.hr .img2{{position:absolute;left:0;bottom:0;width:260px;height:200px;background-size:cover;background-position:center;border-radius:{r}px;border:8px solid {bg}}}
.stats{{display:flex;gap:40px;margin-top:46px}} .stats div{{max-width:180px}} .stats b{{display:block;font-family:{disp};font-size:40px;color:{fg}}} .stats div{{color:{mut};font-size:16px}}
.hero.arch{{display:grid;grid-template-columns:1.05fr .95fr;gap:40px;padding:40px 80px 90px;align-items:center;position:relative}}
.archimg{{height:680px;border-radius:340px 340px {r}px {r}px;background-size:cover;background-position:center}}
.badge{{position:absolute;right:120px;bottom:60px;background:{acc};color:#fff;padding:22px 30px;border-radius:{max(r, 8)}px;font-weight:600;max-width:300px;box-shadow:0 20px 40px rgba(0,0,0,.2)}}
.hero.collage{{padding:50px 80px 90px}} .hero.collage p{{font-size:22px;color:{mut};max-width:680px;margin-bottom:34px}}
.hero.collage h1{{font-size:{h1 + 16}px;max-width:1100px}}
.hero.collage .row{{display:grid;grid-template-columns:1fr 1.4fr 1.4fr 1fr;gap:20px;margin-top:60px;height:420px;align-items:end}}
.row .img{{height:100%;background-size:cover;background-position:center;border-radius:{r}px}} .row .img:nth-child(odd){{height:78%}}
section{{padding:110px 80px}}
.about{{display:grid;grid-template-columns:.9fr 1.1fr;gap:80px;align-items:center;background:{surf}}}
.aimg{{height:620px;background-size:cover;background-position:center;border-radius:{r}px}}
.lead{{font-size:21px;color:{mut};margin-bottom:40px}}
.feats{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:28px}}
.ft i{{display:block;font-style:normal;font-family:{disp};font-size:30px;color:{acc};margin-bottom:8px}} .ft b{{display:block;font-size:19px;margin-bottom:4px}} .ft span{{color:{mut};font-size:16px}}
.sh{{display:flex;justify-content:space-between;align-items:end;margin-bottom:46px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:30px}}
.card .img{{height:380px;background-size:cover;background-position:center;border-radius:{r}px}}
.ct{{display:flex;justify-content:space-between;align-items:center;padding:20px 4px 0}} .ct b{{font-family:{disp};font-size:26px}} .ct span{{color:{acc};font-weight:600;font-size:16px}}
.gallery{{padding:0 80px 110px}}
.gal{{display:grid;grid-template-columns:2fr 1fr 1fr;grid-template-rows:280px 280px;gap:20px}}
.g{{background-size:cover;background-position:center;border-radius:{r}px}} .g0{{grid-row:span 2}} .g3{{grid-column:span 2}}
.reviews{{background:{surf}}} .reviews h2{{margin-bottom:56px}}
.rv{{background:{bg};padding:38px;border-radius:{max(r, 6)}px}} .st{{color:{acc};letter-spacing:4px;margin-bottom:16px}}
.rv p{{font-family:{disp};font-size:22px;line-height:1.45;margin-bottom:22px}} .rv b{{color:{mut};font-weight:600;font-size:16px}}
.cta{{background:{dark};color:{dark_txt};display:grid;grid-template-columns:1.2fr .8fr;gap:60px;align-items:center}}
.cta h2{{font-size:58px}} .cta p{{color:#bdb6ad;font-size:20px;margin-bottom:34px}}
.cta ul{{list-style:none}} .cta li{{padding:18px 0;border-bottom:1px solid rgba(255,255,255,.15);font-size:19px}} .cta li:before{{content:'✓';color:{acc};margin-right:14px;font-weight:700}}
footer{{background:{dark};color:#a8a29a;padding:40px 80px 50px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid rgba(255,255,255,.1);font-size:16px}}
footer .logo{{color:{dark_txt};font-size:24px}}
</style></head><body>
{hero_html}
{main}
<section class="cta"><div><div class="kick">{e}</div><h2>{cta_h}</h2><p>{s}</p><a class="btn">{c}</a></div><ul>{plus_html}</ul></section>
<footer>{logo}<span>{html.escape(menu[0])} · {html.escape(menu[1])} · {html.escape(menu[2])} · {html.escape(menu[3])}</span><span>{place}, Հայաստան</span></footer>
</body></html>'''


class Designs:
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch()
        self.pg = self.browser.new_page(viewport={'width': W, 'height': 900})
        return self

    def render(self, name, category, out, width=1080, city=''):
        from PIL import Image
        out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
        self.pg.set_content(page(name, category, city), wait_until='load')
        self.pg.evaluate('document.fonts.ready')
        png = self.pg.screenshot(full_page=False, type='png')   # только первый экран (Azat 10-25)
        im = Image.open(io.BytesIO(png)).convert('RGB')
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(out, quality=86, optimize=True, progressive=True)
        return out

    def __exit__(self, *a):
        self.browser.close(); self.pw.stop()


if __name__ == '__main__':
    with Designs() as d:
        print(d.render(sys.argv[1], sys.argv[2], sys.argv[3], city=sys.argv[4] if len(sys.argv) > 4 else ''))
