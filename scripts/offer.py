"""PDF-предложение (КП) для бизнеса, который ответил на рассылку с интересом. Только армянский (Azat 10-17).

    python scripts/offer.py "Название" "категория" out.pdf

Стр. 1: имя бизнеса, картинка сайта (mockup.py), что будет на сайте. Стр. 2: цена по нише, поддержка, этапы, контакты.
Цены: прайс evnweb.am (2026-09-28 и 2026-10-12).
"""
import base64, html, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mockup import Mockups, niche_of, _font_css, ASSETS, OUT

# группа ниш: (что делаем, вступление, функции [(заголовок, пояснение)], основная цена, доп. вариант (название, цена, пункты))
G = {
    'food': ('Կայք {name}-ի համար',
             'Հյուրերը տեսնում են մենյուն լուսանկարներով, ամրագրում են սեղան կամ պատվիրում առաքում, իսկ հայտը անմիջապես գալիս է ձեր Telegram-ին։',
             [('Դիզայն ձեր ոճով', 'Ձեր լոգոն, գույները և սրահի լուսանկարները'),
              ('Մենյու լուսանկարներով', 'Բաժիններ, ուտեստներ, գներ և նկարագրություն'),
              ('Սեղանի ամրագրում', 'Հյուրը ընտրում է օրը, ժամը և մարդկանց քանակը'),
              ('Պատվեր և առաքում', 'Զամբյուղ, առաքում Երևանում կամ վերցնել տեղից'),
              ('Առցանց վճարում', 'ArCa, Visa, Mastercard, Idram կամ կանխիկ'),
              ('Հայտերը Telegram-ում', 'Յուրաքանչյուր ամրագրում և պատվեր անմիջապես գալիս է ձեզ'),
              ('3 լեզու', 'Հայերեն, ռուսերեն և անգլերեն'),
              ('Բջջային տարբերակ', 'Հարմար է հեռախոսից'),
              ('Ադմին վահանակ', 'Մենյուն և գները փոխում եք ինքներդ'),
              ('Կենդանի չատ կայքում', 'Հաճախորդը գրում է կայքից, դուք պատասխանում եք ադմինից'),
              ('Google Maps և SEO', 'Ձեզ հեշտ է գտնել Google-ում և քարտեզում'),
              ('Վիճակագրություն', 'Պատվերներ, ամրագրումներ և ամենաշատ պատվիրվող ուտեստներ')],
             ('Ռեստորանի կայք', '280 000 ֏'),
             ('Ռեստորանի համակարգ', '350 000 ֏', ['Սեղանների և պատվերների կառավարում', 'Խոհանոցի էկրան', 'Վաճառքի հաշվետվություններ'])),
    'stay': ('Կայք {name}-ի համար',
             'Հյուրերը տեսնում են համարները լուսանկարներով, ստուգում են ազատ օրերը և ամրագրում են ուղիղ, առանց Booking-ի կոմիսիայի։',
             [('Դիզայն ձեր ոճով', 'Ձեր լոգոն, գույները և լուսանկարները'),
              ('Համարներ լուսանկարներով', 'Յուրաքանչյուր համարի էջ՝ գին, հարմարություններ, լուսանկարներ'),
              ('Ուղիղ ամրագրում', 'Հյուրը ընտրում է ամսաթվերը և ամրագրում կայքում'),
              ('Զբաղվածության օրացույց', 'Զբաղված օրերը ինքնաշխատ փակվում են'),
              ('Առցանց վճարում', 'ArCa, Visa, Mastercard կամ կանխիկ՝ տեղում'),
              ('Հայտերը Telegram-ում', 'Յուրաքանչյուր նոր ամրագրում անմիջապես գալիս է ձեզ'),
              ('3 լեզու', 'Հայերեն, ռուսերեն և անգլերեն'),
              ('Բջջային տարբերակ', 'Հարմար է ամրագրել հեռախոսից'),
              ('Ադմին վահանակ', 'Գները, համարները և լուսանկարները փոխում եք ինքներդ'),
              ('Կենդանի չատ կայքում', 'Հյուրը գրում է կայքից, դուք պատասխանում եք ադմինից'),
              ('Google Maps և SEO', 'Ձեզ հեշտ է գտնել Google-ում և քարտեզում'),
              ('Վիճակագրություն', 'Ամրագրումներ և զբաղվածություն ըստ ամիսների')],
             ('Հյուրանոցի կայք', '450 000 ֏'),
             ('Կայք + հյուրանոցի կառավարում', '900 000 ֏', ['Շախմատ՝ բոլոր համարները մեկ էկրանում', 'Առցանց վճարում և կանխավճար', 'Հաշվետվություններ'])),
    'booking': ('Կայք {name}-ի համար',
                'Հաճախորդները ընտրում են ծառայությունը, մասնագետին և ազատ ժամը, գրանցվում են առցանց 24/7, իսկ հայտը գալիս է ձեր Telegram-ին։',
                [('Դիզայն ձեր ոճով', 'Ձեր լոգոն, գույները և լուսանկարները'),
                 ('Ծառայություններ և գներ', 'Ծառայությունների ցանկ՝ գներով և տևողությամբ'),
                 ('Առցանց գրանցում 24/7', 'Հաճախորդը ընտրում է օրը և ազատ ժամը'),
                 ('Մասնագետների գրաֆիկ', 'Յուրաքանչյուր մասնագետի ազատ և զբաղված ժամերը'),
                 ('Հիշեցումներ', 'Հաճախորդը ստանում է հիշեցում այցից առաջ'),
                 ('Հայտերը Telegram-ում', 'Յուրաքանչյուր նոր գրանցում անմիջապես գալիս է ձեզ'),
                 ('Աշխատանքների պատկերասրահ', 'Ձեր լավագույն աշխատանքների լուսանկարները'),
                 ('3 լեզու', 'Հայերեն, ռուսերեն և անգլերեն'),
                 ('Բջջային տարբերակ', 'Հարմար է գրանցվել հեռախոսից'),
                 ('Ադմին վահանակ', 'Ծառայությունները, գները և գրաֆիկը փոխում եք ինքներդ'),
                 ('Google Maps և SEO', 'Ձեզ հեշտ է գտնել Google-ում և քարտեզում'),
                 ('Վիճակագրություն', 'Գրանցումներ և ամենապահանջված ծառայություններ')],
                ('Կայք առցանց գրանցումով', '200 000 ֏'),
                ('Կայք + CRM', '400 000 ֏', ['Հաճախորդների բազա և այցերի պատմություն', 'Վճարումներ և հաշվետվություններ', 'SMS և Telegram հիշեցումներ'])),
    'shop': ('Առցանց խանութ {name}-ի համար',
             'Հաճախորդները ընտրում են ապրանքները կայքում, վճարում են քարտով կամ Idram-ով, իսկ պատվերը անմիջապես գալիս է ձեր Telegram-ին։',
             [('Դիզայն ձեր ոճով', 'Ձեր լոգոն, գույները և լուսանկարները'),
              ('Ապրանքների կատալոգ', 'Բաժիններ, ֆիլտր և որոնում'),
              ('Ապրանքի էջ', 'Լուսանկարներ, գին և նկարագրություն'),
              ('Զամբյուղ և պատվեր', 'Պատվերը մեկ րոպեում'),
              ('Առցանց վճարում', 'ArCa, Visa, Mastercard, Idram կամ կանխիկ'),
              ('Պատվերները Telegram-ում', 'Յուրաքանչյուր նոր պատվեր անմիջապես գալիս է ձեզ'),
              ('Առաքում և վերցնել խանութից', 'Առաքում Երևանում կամ վերցնել խանութից'),
              ('3 լեզու', 'Հայերեն, ռուսերեն և անգլերեն'),
              ('Բջջային տարբերակ', 'Հարմար է գնումներ անել հեռախոսով'),
              ('Ադմին վահանակ', 'Ապրանքներ, գներ և լուսանկարներ ավելացնում եք ինքներդ'),
              ('Զեղչեր և պրոմոկոդեր', 'Ակցիաներ, հին և նոր գին'),
              ('Վիճակագրություն', 'Վաճառքներ և ամենաշատ վաճառվող ապրանքներ')],
             ('Առցանց խանութ', '400 000 ֏'),
             ('Խանութ + պահեստի հաշվառում', '650 000 ֏', ['Ապրանքի ընդունում և շտրիխկոդեր', 'Մնացորդները խանութում և կայքում՝ միասին', 'Շահույթի և վաճառքի հաշվետվություններ'])),
    'travel': ('Կայք {name}-ի համար',
               'Զբոսաշրջիկները տեսնում են տուրերը լուսանկարներով և գներով, ընտրում են ամսաթիվը և ամրագրում են ուղիղ կայքում։',
               [('Դիզայն ձեր ոճով', 'Ձեր լոգոն, գույները և լուսանկարները'),
                ('Տուրերի կատալոգ', 'Ուղղություններ, ծրագիր, տևողություն և գին'),
                ('Առցանց ամրագրում', 'Ամսաթիվ, մարդկանց քանակ և հայտ'),
                ('Առցանց վճարում', 'ArCa, Visa, Mastercard կամ կանխավճար'),
                ('Հայտերը Telegram-ում', 'Յուրաքանչյուր հայտ անմիջապես գալիս է ձեզ'),
                ('3 լեզու', 'Հայերեն, ռուսերեն և անգլերեն'),
                ('Բջջային տարբերակ', 'Հարմար է հեռախոսից'),
                ('Ադմին վահանակ', 'Տուրերն ու գները փոխում եք ինքներդ'),
                ('Կենդանի չատ կայքում', 'Հաճախորդը գրում է կայքից, դուք պատասխանում եք ադմինից'),
                ('Կարծիքներ', 'Հաճախորդների կարծիքներ և լուսանկարներ'),
                ('SEO', 'Կայքը պատրաստ է Google-ում գտնվելու համար'),
                ('Վիճակագրություն', 'Հայտեր և ամենապահանջված տուրեր')],
               ('Կայք տուրերի ամրագրումով', '280 000 ֏'),
               ('Կայք + CRM', '400 000 ֏', ['Հաճախորդների բազա', 'Խմբերի և ուղեկցորդների կառավարում', 'Հաշվետվություններ'])),
}
GROUP = {'restaurant': 'food', 'cafe': 'food', 'fastfood': 'food', 'bar': 'food',
         'hotel': 'stay', 'guesthouse': 'stay', 'hostel': 'stay', 'apartment': 'stay',
         'salon': 'booking', 'barber': 'booking', 'auto': 'booking', 'dental': 'booking', 'clinic': 'booking',
         'market': 'shop', 'shop': 'shop', 'travel': 'travel'}

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; margin:0; padding:0; }
:root { --r:#e0283f; --dk:#16131a; --mut:#5d5862; }
body { font:10pt/1.45 "Noto Sans Armenian","Noto Sans",sans-serif; color:#1d1a20; }
.pg { width:210mm; height:297mm; position:relative; overflow:hidden; page-break-after:always; }
.pg:last-child { page-break-after:auto; }
.hero { background:linear-gradient(135deg,#1a1519 0%,#3a1018 100%); color:#fff; padding:13mm 15mm 0; height:132mm; position:relative; }
.top { display:flex; justify-content:space-between; align-items:center; }
.top img { height:9mm; }
.top span { font-size:8.5pt; color:#d9cfd4; }
.eb { margin-top:10mm; font-size:8pt; letter-spacing:.12em; text-transform:uppercase; font-weight:700; color:#ff6b7c; }
h1 { font:700 23pt/1.15 "Noto Sans Armenian","Noto Sans"; margin:2mm 0 4mm; max-width:88mm; overflow-wrap:break-word; }
h1 em { font-style:normal; color:#ff4a5e; }
.lead { font-size:10.5pt; color:#e6dde2; max-width:84mm; }
.mk { position:absolute; right:10mm; top:28mm; width:88mm; border-radius:3mm; box-shadow:0 3mm 10mm rgba(0,0,0,.45); }
.body { padding:9mm 15mm 0; }
h2 { font:700 15pt "Noto Sans Armenian","Noto Sans"; margin:0 0 5mm; }
.feat { display:grid; grid-template-columns:1fr 1fr; gap:3.4mm 8mm; }
.feat div { padding-left:8mm; position:relative; font-size:9pt; color:var(--mut); }
.feat div:before { content:"✓"; position:absolute; left:0; top:.3mm; width:5mm; height:5mm; border-radius:50%; background:var(--r); color:#fff; font:700 8pt/5mm sans-serif; text-align:center; }
.feat b { display:block; font-size:10pt; color:#1d1a20; }
.foot { position:absolute; bottom:7mm; left:15mm; right:15mm; font-size:7.5pt; color:#9a949e; display:flex; justify-content:space-between; }
.price { display:grid; grid-template-columns:1.2fr 1fr; gap:5mm; margin-bottom:7mm; }
.box { border:1px solid #e1dde3; border-radius:3mm; padding:6mm; }
.box.main { border:2px solid var(--r); background:#fff6f7; }
.tag { display:inline-block; background:var(--r); color:#fff; font-size:7.5pt; font-weight:700; padding:.8mm 2.5mm; border-radius:1mm; }
.box h3 { font-size:12pt; margin:3mm 0 0; }
.amt { font:700 25pt/1.1 "Noto Sans","Noto Sans Armenian"; color:var(--r); margin:2mm 0 1mm; }
.box.opt .amt { font-size:19pt; color:#1d1a20; }
.note { font-size:8.5pt; color:var(--mut); margin-bottom:3mm; }
.box ul { padding-left:4.5mm; font-size:9pt; } .box li { margin-bottom:1.2mm; }
.inc { display:grid; grid-template-columns:repeat(3,1fr); gap:4mm; margin-bottom:8mm; }
.inc div { background:#f5f3f6; border-radius:2.5mm; padding:4mm; font-size:8.8pt; color:var(--mut); }
.inc b { display:block; color:#1d1a20; font-size:10pt; margin-bottom:.5mm; }
.inc .big { color:var(--r); font-size:13pt; }
.steps { display:grid; grid-template-columns:repeat(4,1fr); gap:3mm; margin-bottom:6mm; }
.steps div { border-top:1mm solid var(--r); padding-top:2.5mm; font-size:8.6pt; color:var(--mut); }
.steps b { display:block; color:#1d1a20; font-size:9.6pt; }
.own { font-size:9pt; color:var(--mut); }
.contact { position:absolute; left:15mm; right:15mm; bottom:16mm; background:var(--dk); color:#fff; border-radius:3mm; padding:6mm 7mm; display:flex; justify-content:space-between; align-items:center; }
.contact img { height:8mm; display:block; margin-bottom:2mm; }
.contact .l span { font-size:9pt; color:#cfc6cc; }
.contact .r { text-align:right; font-size:10pt; line-height:1.75; }
.contact .r b { font-size:12.5pt; }
"""


def _img(p, mime):
    return f'data:{mime};base64,{base64.b64encode(Path(p).read_bytes()).decode()}'


def page(name, category, mockup_jpg):
    g = G[GROUP.get(niche_of(category), 'food')]
    what, lead, feats, (pname, pamt), (oname, oamt, oli) = g
    e = html.escape(name)
    logo = _img(ASSETS / 'logo.png', 'image/png')
    feats_html = ''.join(f'<div><b>{a}</b>{b}</div>' for a, b in feats)
    mainli = ''.join(f'<li>{x}</li>' for x in ['Ամեն ինչ նախորդ էջի ցուցակից', 'Կայքի տեղադրում ձեր դոմենի վրա',
                                                 'Ադմին վահանակի ուսուցում', 'Կայքը և բոլոր տվյալները պատկանում են ձեզ'])
    optli = ''.join(f'<li>{x}</li>' for x in oli)
    inc = ''.join(f'<div><b>{a}</b><b class="big">{b}</b>{c}</div>' for a, b, c in [
        ('Աջակցում', '25 000 ֏/ամիս', 'Թարմացումներ, փոփոխություններ, հոստինգի հսկողություն'),
        ('Առաջին 3 ամիսը', 'Անվճար', 'Աջակցումը գործարկումից հետո 3 ամիս՝ անվճար'),
        ('Կոմիսիա', '0%', 'Ձեր վաճառքից տոկոս չենք վերցնում')])
    steps = ''.join(f'<div><b>{a}</b>{b}</div>' for a, b in [
        ('1. Զանգ կամ հանդիպում', 'Քննարկում ենք ձեր ցանկությունները'), ('2. Դիզայն', 'Կայքի տեսքը ձեր ոճով'),
        ('3. Լցնում ենք', 'Տեքստեր, լուսանկարներ, գներ'), ('4. Գործարկում', 'Կայքը աշխատում է, հայտերը՝ Telegram-ում')])
    h1 = html.escape(what).replace('{name}', f'<em>{e}</em>')
    return f"""<!doctype html><html lang="hy"><head><meta charset="utf-8"><style>{_font_css()}{CSS}</style></head><body>
<section class="pg">
 <div class="hero">
  <div class="top"><img src="{logo}"><span>Անհատական առաջարկ · 2026</span></div>
  <div class="eb">Առաջարկ {e}-ի համար</div>
  <h1>{h1}</h1>
  <p class="lead">{lead}</p>
  <img class="mk" src="{_img(mockup_jpg, 'image/jpeg')}">
 </div>
 <div class="body"><h2>Ինչ կներառի կայքը</h2><div class="feat">{feats_html}</div></div>
 <div class="foot"><span>EvnWeb · evnweb.am</span><span>{e} · 1</span></div>
</section>
<section class="pg"><div class="body" style="padding-top:14mm">
 <h2>Արժեք</h2>
 <div class="price">
  <div class="box main"><span class="tag">Ամբողջ փաթեթ</span><h3>{pname}</h3><div class="amt">{pamt}</div><div class="note">մեկանգամյա վճար · պատրաստ է 2–4 շաբաթում</div><ul>{mainli}</ul></div>
  <div class="box opt"><span class="tag" style="background:#6d6772">Ըստ ցանկության</span><h3>{oname}</h3><div class="amt">{oamt}</div><div class="note">եթե ուզում եք ավելին</div><ul>{optli}</ul></div>
 </div>
 <div class="inc">{inc}</div>
 <h2>Ինչպես ենք աշխատում</h2>
 <div class="steps">{steps}</div>
 <p class="own">Կայքը պատրաստվում է Laravel-ով՝ արագ, հուսալի և հեշտ ընդլայնվող։</p>
</div>
 <div class="contact"><div class="l"><img src="{logo}"><span>Ազատ · կայքերի և ծրագրերի մշակում<br>Կցուցադրեմ դեմոն առցանց, անվճար</span></div>
 <div class="r"><b>+374 93 40-11-79</b><br>Telegram · WhatsApp · Viber<br>vip.azatazat@gmail.com · evnweb.am</div></div>
 <div class="foot"><span>EvnWeb · evnweb.am</span><span>{e} · 2</span></div>
</section></body></html>"""


def render(name, category, out):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    with Mockups() as m:
        jpg = m.render(name, category, 'hy', OUT / (out.stem + '-kp.jpg'))
        m.pg.set_content(page(name, category, jpg), wait_until='load')
        m.pg.evaluate('document.fonts.ready')
        m.pg.pdf(path=str(out), format='A4', print_background=True)
    return out


if __name__ == '__main__':
    print(render(sys.argv[1], sys.argv[2], sys.argv[3]))
