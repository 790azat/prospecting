"""Читает bio Instagram-профилей магазинов: телефон, ссылка, подписчики, свежесть постов.

Вход data/magaziny/instagram.csv (колонка username), выход data/magaziny/ig_bio.csv.
Плюс похожие профили (related) в data/magaziny/ig_related.txt для следующего прохода.
Работает только на раннере GitHub Actions (из песочницы Instagram недоступен).
"""
import csv, json, os, random, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'data' / 'magaziny'
URLS = ['https://i.instagram.com/api/v1/users/web_profile_info/?username={}',
        'https://www.instagram.com/api/v1/users/web_profile_info/?username={}']
HEAD = {'x-ig-app-id': '936619743392459', 'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
                      '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'}
PHONE = re.compile(r'(?:\+?374|\b0)[\s\-.()]*(\d{2})[\s\-.()]*(\d{2})[\s\-.()]*(\d{2})[\s\-.()]*(\d{2})\b')
WA = re.compile(r'wa\.me/\+?(374\d{8})')


def phones(*texts):
    out = []
    for t in texts:
        t = t or ''
        for m in WA.finditer(t):
            out.append('+' + m.group(1))
        for m in PHONE.finditer(t):
            out.append('+374' + ''.join(m.groups()))
    return list(dict.fromkeys(out))


SESSION = os.environ.get('IG_SESSIONID', '').strip()   # cookie sessionid запасного аккаунта (секрет)
if SESSION:
    HEAD['Cookie'] = f'sessionid={SESSION}'


def fetch(user):
    for u in URLS:
        req = urllib.request.Request(u.format(user), headers=HEAD)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)['data']['user'], 200
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception:
            code = 0
    return None, code


def main():
    if not SESSION:
        sys.exit('Нет секрета IG_SESSIONID: без входа Instagram отвечает 429, ничего не читаю.')
    rows = list(csv.DictReader(open(ROOT / 'instagram.csv', encoding='utf-8')))
    users = [r['username'].strip().lstrip('@') for r in rows if r.get('username')]
    extra = ROOT / 'ig_more.txt'   # дополнительные username по одному в строке
    if extra.exists():
        users += [l.strip().lstrip('@') for l in extra.read_text().split() if l.strip()]
    users = list(dict.fromkeys(users))
    done = {}
    if (ROOT / 'ig_bio.csv').exists():   # уже прочитанные не трогаем, читаем порциями
        done = {r['username']: r for r in csv.DictReader(open(ROOT / 'ig_bio.csv', encoding='utf-8')) if not r.get('oshibka')}
    limit = int(os.environ.get('IG_LIMIT') or 40)
    todo = [u for u in users if u not in done][:limit]
    old_rel = set((ROOT / 'ig_related.txt').read_text().split()) if (ROOT / 'ig_related.txt').exists() else set()
    print(f'Уже прочитано {len(done)}, сейчас читаю {len(todo)}')
    users = todo
    out, related, fails = [], set(old_rel), 0
    for i, user in enumerate(users):
        u, code = fetch(user)
        if not u:
            print(user, 'ошибка', code, flush=True)
            out.append({'username': user, 'oshibka': code})
            fails += 1
            if code == 429:
                time.sleep(120)
            if fails >= 15 and fails > i * 0.6:
                print('Instagram блокирует, стоп'); break
            continue
        bio = u.get('biography') or ''
        link = u.get('external_url') or ''
        bl = ' '.join(x.get('url', '') for x in (u.get('bio_links') or []))
        ph = phones(u.get('business_phone_number') and ('+' + (u.get('business_country_code') or '') + u['business_phone_number']), bio, link, bl)
        posts = u.get('edge_owner_to_timeline_media', {}).get('edges', [])
        last = max((p['node'].get('taken_at_timestamp', 0) for p in posts), default=0)
        for e in u.get('edge_related_profiles', {}).get('edges', []):
            related.add(e['node']['username'])
        out.append({'username': user, 'imya': u.get('full_name', ''), 'telefon': '; '.join(ph),
                    'email': u.get('business_email') or '', 'ssylka': link or bl,
                    'podpischiki': u.get('edge_followed_by', {}).get('count', ''),
                    'kategoriya_ig': u.get('category_name') or '',
                    'posledniy_post': datetime.fromtimestamp(last, timezone.utc).date().isoformat() if last else '',
                    'bio': bio.replace('\n', ' | '), 'oshibka': ''})
        print(user, '|', ph, '|', link, flush=True)
        time.sleep(random.uniform(20, 40) if SESSION else random.uniform(4, 9))
    f = ['username', 'imya', 'telefon', 'email', 'ssylka', 'podpischiki', 'kategoriya_ig', 'posledniy_post', 'bio', 'oshibka']
    with open(ROOT / 'ig_bio.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=f); w.writeheader(); w.writerows(list(done.values()) + out)
    (ROOT / 'ig_related.txt').write_text('\n'.join(sorted(related - set(users) - set(done))))
    ok = sum(1 for r in out if not r['oshibka'])
    print(f'Прочитано {ok} из {len(users)}, с телефоном {sum(1 for r in out if r.get("telefon"))}, похожих {len(related)}')


if __name__ == '__main__':
    main()
