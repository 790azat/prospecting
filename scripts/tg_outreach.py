"""Рассылка первых сообщений в Telegram с аккаунта Азата (Telethon, пользовательская сессия).

Режимы (первый аргумент):
  send_code        - запросить код входа, сохранить зашифрованную пред-сессию
  sign_in CODE     - войти по коду (и облачному паролю из TG_2FA, если есть)
  run              - дневная порция: проверить ответы, отправить N сообщений с паузами, отчёт в «Избранное»
  status           - проверить сессию и вывести счётчики без отправки

Безопасность аккаунта: лимит по дням (10/15/20, не больше 25), только пн-сб 10:30-18:30 по Еревану,
паузы 4-10 минут, текст и следом основное видео (data/tg/video), без повторов. При PeerFlood/FloodWait рассылка встаёт на 3 дня.
Сессия хранится в репозитории только в зашифрованном виде (ключ из секрета TG_API_HASH).
"""
import asyncio, base64, csv, datetime as dt, hashlib, json, os, random, re, sys
from pathlib import Path

from cryptography.fernet import Fernet
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession

ROOT = Path(__file__).resolve().parent.parent / 'data' / 'tg'
QUEUE, STATE, SESSION = ROOT / 'queue.csv', ROOT / 'state.json', ROOT / 'session.enc'
VIDEO_DIR = ROOT / 'video'   # после текста отправляем основное видео EVNWEB на языке сообщения
PHONE = os.environ.get('TG_PHONE') or '+37493401179'
LANG = os.environ.get('TG_LANG') or 'hy'          # язык первого сообщения: hy или ru
YEREVAN = dt.timezone(dt.timedelta(hours=4))
MAX_PER_DAY = 25
PAUSE_MIN, PAUSE_MAX = 4 * 60, 10 * 60


def limit_for(day_no):
    if day_no <= 3: return 10
    if day_no <= 7: return 15
    return 20


def fernet():
    key = hashlib.sha256((os.environ['TG_API_HASH'] + ':evnweb-session').encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def load_session():
    return fernet().decrypt(SESSION.read_bytes()).decode() if SESSION.exists() else ''


def save_session(s):
    SESSION.write_bytes(fernet().encrypt(s.encode()))


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1) + '\n')


def load_queue():
    with QUEUE.open(newline='') as f:
        return list(csv.DictReader(f))


def save_queue(rows):
    with QUEUE.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def client(session=''):
    return TelegramClient(StringSession(session), int(os.environ['TG_API_ID']), os.environ['TG_API_HASH'],
                          device_model='EVNWEB', system_version='Linux', app_version='1.0',
                          lang_code='ru', system_lang_code='ru')


class Video:
    """Первая отправка загружает файл, дальше пересылаем уже загруженный документ."""
    def __init__(self, lang):
        self.path, self.thumb = VIDEO_DIR / f'evnweb-{lang}.mp4', VIDEO_DIR / f'oblozhka-{lang}.jpg'
        self.media = None

    def ok(self):
        return self.path.exists()

    async def send(self, c, user):
        if self.media is None:
            msg = await c.send_file(user, str(self.path), supports_streaming=True,
                                    thumb=str(self.thumb) if self.thumb.exists() else None)
            self.media = msg.media
        else:
            await c.send_file(user, self.media)


def now():
    return dt.datetime.now(YEREVAN)


async def send_code():
    c = client(); await c.connect()
    sent = await c.send_code_request(PHONE)
    save_session(c.session.save())
    st = load_state(); st['phone_code_hash'] = sent.phone_code_hash; save_state(st)
    print('Код отправлен. Тип доставки:', type(sent.type).__name__)
    await c.disconnect()


async def sign_in(code):
    st = load_state()
    c = client(load_session()); await c.connect()
    try:
        await c.sign_in(PHONE, code.strip(), phone_code_hash=st.get('phone_code_hash'))
    except errors.SessionPasswordNeededError:
        pw = os.environ.get('TG_2FA')
        if not pw:
            sys.exit('Нужен облачный пароль: добавьте секрет TG_2FA и запустите вход ещё раз (с новым кодом).')
        await c.sign_in(password=pw)
    me = await c.get_me()
    save_session(c.session.save())
    st.pop('phone_code_hash', None); st['login'] = now().isoformat(); save_state(st)
    print('Вход выполнен:', me.first_name, '(id скрыт)')
    await c.disconnect()


async def check_replies(c, rows):
    """Кто из тех, кому писали, ответил. Отмечаем в очереди и возвращаем список новых ответов."""
    waiting = {r['tg_id']: r for r in rows if r['status'] == 'otpravleno' and r.get('tg_id')}
    new = []
    if not waiting:
        return new
    async for d in c.iter_dialogs(limit=300):
        r = waiting.get(str(d.id))
        if r and d.message and not d.message.out:
            r['status'] = 'otvetil'
            r['otvet'] = (d.message.message or '[медиа]')[:300].replace('\n', ' ')
            new.append(r)
    return new


async def report(c, text):
    try:
        await c.send_message('me', text)
    except Exception as e:
        print('Не удалось отправить отчёт:', e)


def last_run(msg):
    (ROOT / 'last_run.txt').write_text(f'{now().isoformat()}\n{msg}\n')


async def spam_check(c):
    """Спрашиваем @SpamBot, нет ли ограничения на сообщения незнакомым. Возвращает (ok, ответ)."""
    try:
        async with c.conversation('SpamBot', timeout=40) as conv:
            await conv.send_message('/start')
            ans = (await conv.get_response()).raw_text or ''
    except Exception as e:
        return False, f'SpamBot не ответил: {type(e).__name__}'
    low = ans.lower()
    free = any(w in low for w in ('no limits', 'free as a bird', 'свободен', 'нет ограничений', 'никаких ограничений'))
    return free, ans[:1500].replace('\n', ' ')


async def run():
    st = load_state()
    t = now()
    if (t.weekday() == 6 or not (dt.time(10, 30) <= t.time() <= dt.time(18, 30))):
        print('Не рабочее время по Еревану, пропускаю:', t.isoformat()); return
    if st.get('pause_until') and t.date().isoformat() < st['pause_until']:
        print('Рассылка на паузе до', st['pause_until']); return
    if st.get('stopped'):
        print('Рассылка остановлена вручную (state.stopped).'); return

    rows = load_queue()
    today = t.date().isoformat()
    days = st.setdefault('days', {})
    day_no = len([d for d in days if d != today]) + 1
    limit = min(limit_for(day_no), MAX_PER_DAY) - days.get(today, 0)
    if days.get(today) and limit <= 0:
        print('Сегодняшний лимит уже отправлен'); return

    c = client(load_session()); await c.connect()
    if not await c.is_user_authorized():
        sys.exit('Сессия не авторизована: нужен вход (send_code, затем sign_in).')

    replies = await check_replies(c, rows)
    save_queue(rows)
    free, spam_ans = await spam_check(c)
    print('SpamBot:', spam_ans)
    if not free:
        msg = f'EVNWEB рассылка {today}: не начата, у аккаунта ограничение Telegram. SpamBot: {spam_ans}'
        st['pause_until'] = (t.date() + dt.timedelta(days=1)).isoformat(); save_state(st)  # завтра проверим снова
        print(msg); last_run(msg); await report(c, msg); await c.disconnect(); return
    sent, no_tg, had_chat, stop_reason = [], 0, 0, ''
    video, video_sent = Video(LANG), 0
    if not video.ok():   # текст ссылается на видео ниже, без него не отправляем
        sys.exit(f'Нет видео {video.path}, рассылка не запущена.')
    tries_day = st.setdefault('tries', {})
    tries = tries_day.get(today, 0)   # проверки номеров за день, с учётом запасных запусков
    day_cap = min(limit_for(day_no), MAX_PER_DAY) * 3
    todo = [r for r in rows if r['status'] == '']
    todo.sort(key=lambda r: (int(r['den'] or 999), int(r['prioritet'] or 9)))
    print(f'День рассылки №{day_no}, лимит на сегодня {limit}, в очереди {len(todo)}, новых ответов {len(replies)}')

    for r in todo:
        if len(sent) >= limit or tries >= day_cap:
            break
        if now().time() > dt.time(18, 30):
            stop_reason = 'закончилось рабочее время'; break
        tries += 1; tries_day[today] = tries
        try:
            res = await c(functions.contacts.ImportContactsRequest([types.InputPhoneContact(
                client_id=random.randrange(1 << 62), phone=r['nomer'], first_name=r['nazvanie'][:60], last_name='')]))
            if not res.users:
                r['status'], r['data'] = 'net_tg', today; no_tg += 1; save_queue(rows)
                await asyncio.sleep(random.uniform(20, 60)); continue
            user = res.users[0]
            if user.bot or user.deleted:
                r['status'], r['data'] = 'net_tg', today; no_tg += 1; save_queue(rows); continue
            if await c.get_messages(user, limit=1):
                r['status'], r['data'], r['tg_id'] = 'uzhe_byla_perepiska', today, str(user.id)
                had_chat += 1; save_queue(rows); continue
            text = r['tekst_hy'] if LANG == 'hy' else r['tekst_ru']
            async with c.action(user, 'typing'):
                await asyncio.sleep(random.uniform(4, 9))
            await c.send_message(user, text)
            r['status'], r['data'], r['tg_id'] = 'otpravleno', today, str(user.id)
            sent.append(r)
            days[today] = days.get(today, 0) + 1
            save_queue(rows); save_state(st)
            if video.ok():
                await asyncio.sleep(random.uniform(3, 7))
                try:
                    async with c.action(user, 'video'):
                        await video.send(c, user)
                    video_sent += 1
                except (errors.PeerFloodError, errors.FloodWaitError):
                    raise
                except Exception as e:
                    print('Видео не отправлено:', type(e).__name__, e)
            print(f'{len(sent)}/{limit} отправлено: {r["nazvanie"]} ({r["kategoriya"]})')
        except (errors.PeerFloodError, errors.FloodWaitError) as e:
            wait = getattr(e, 'seconds', 0)
            st['pause_until'] = (t.date() + dt.timedelta(days=3)).isoformat()
            stop_reason = f'Telegram ограничил отправку ({type(e).__name__} {wait}s), пауза до {st["pause_until"]}'
            break
        except (errors.UserPrivacyRestrictedError, errors.UserIsBlockedError, errors.InputUserDeactivatedError,
                errors.PrivacyPremiumRequiredError) as e:
            r['status'], r['data'] = 'zakryt', today; save_queue(rows); continue
        except errors.AuthKeyUnregisteredError:
            stop_reason = 'сессия отозвана, нужен повторный вход'; break
        if len(sent) < limit:
            await asyncio.sleep(random.uniform(PAUSE_MIN, PAUSE_MAX))

    save_queue(rows); save_state(st)
    left = len([r for r in rows if r['status'] == ''])
    lines = [f'EVNWEB рассылка {today}: отправлено {len(sent)} из {limit}, с видео {video_sent}.']
    if sent: lines.append('Кому: ' + ', '.join(r['nazvanie'] for r in sent))
    if no_tg or had_chat: lines.append(f'Нет в Telegram: {no_tg}. Уже была переписка (пропущено): {had_chat}.')
    if replies:
        lines.append('Ответили:')
        lines += [f'• {r["nazvanie"]}: {r["otvet"][:120]}' for r in replies]
    if stop_reason: lines.append('Остановлено: ' + stop_reason)
    lines.append(f'В очереди осталось {left}. Завтра лимит {min(limit_for(day_no + 1), MAX_PER_DAY)}.')
    msg = '\n'.join(lines)
    print(msg); last_run(msg)
    await report(c, msg)
    await c.disconnect()


async def status():
    rows = load_queue()
    from collections import Counter
    print(Counter(r['status'] or 'v_ocheredi' for r in rows))
    print(json.dumps({k: v for k, v in load_state().items() if k != 'phone_code_hash'}, ensure_ascii=False))
    if SESSION.exists():
        c = client(load_session()); await c.connect()
        print('Сессия авторизована:', await c.is_user_authorized())
        await c.disconnect()


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if mode == 'send_code': asyncio.run(send_code())
    elif mode == 'sign_in': asyncio.run(sign_in(sys.argv[2]))
    elif mode == 'run': asyncio.run(run())
    else: asyncio.run(status())
