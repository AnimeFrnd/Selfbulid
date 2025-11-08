# main.py
"""
Telegram Group Creator Userbot (Telethon)
- Uses a Telethon user session (string session recommended to avoid OTP on every start).
- Environment variables (set these in Koyeb / GitHub secrets / .env during dev):
    API_ID, API_HASH, TELETHON_SESSION_STRING (optional), SESSION_NAME (optional),
    OWNER_USERNAME (e.g. @Arya_Bro), BIO_TEMPLATE (optional),
    MODE (optional, default: arabic OR middleeast:egypt), MONGO_URI (optional)
- Start command: python3 main.py
"""

import os
import asyncio
import re
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon import functions

# ---------- Config from env ----------
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
SESSION_NAME = os.getenv('SESSION_NAME', 'AryaSession')
SESSION_STRING = os.getenv('TELETHON_SESSION_STRING', None)  # if provided, used instead of file session
OWNER_USERNAME = os.getenv('OWNER_USERNAME', '@Arya_Bro')
BIO_TEMPLATE = os.getenv('BIO_TEMPLATE', '{group_name} Owner - {owner}')
GROUP_NAME_TEMPLATE = os.getenv('GROUP_NAME_TEMPLATE', '{month_name} {day} Gc {num}')
DEFAULT_MODE = os.getenv('MODE', 'arabic')  # 'arabic' | 'russian' | 'middleeast:egypt' etc.

if API_ID == 0 or API_HASH == '':
    print("ERROR: Set API_ID and API_HASH environment variables.")
    exit(1)

# ---------- Message banks (20+ each) ----------
ARABIC_MESSAGES = [
    "مرحبا بالجميع!", "كيف الحال؟", "أهلا وسهلا في المجموعة.", "من أي بلد أنتم؟",
    "تواصلوا معنا دائمًا.", "نتمنى لكم يومًا سعيدًا!", "ما هي اهتماماتكم؟", "هل تحبون الأخبار؟",
    "شاركوا صوركم.", "مرحبًا بالجميع، نرجو الالتزام بالقواعد.", "هل هناك متحدثين باللغة الإنجليزية؟",
    "ما رأيكم في هذا الموضوع؟", "يرجى احترام الجميع.", "تحديث: حدث جديد اليوم.", "أهلاً بكم في فريقنا.",
    "لا تنسوا تقديم أنفسكم.", "تحياتنا من المشرفين.", "نحن هنا للمساعدة.", "ما هي هواياتكم؟",
    "سؤال اليوم: ما هو فيلمكم المفضل؟", "هذا مجرد نص تجريبي.", "شكراً لانضمامكم!"
]

RUSSIAN_MESSAGES = [
    "Привет всем!", "Как дела?", "Добро пожаловать в группу.", "Откуда вы?",
    "Свяжитесь с нами в любое время.", "Желаем вам хорошего дня!", "Какие у вас интересы?",
    "Любите ли вы новости?", "Поделитесь своими фотографиями.", "Пожалуйста, соблюдайте правила.",
    "Есть ли говорящие по-английски?", "Что вы думаете об этом?", "Пожалуйста уважайте друг друга.",
    "Обновление: новое событие сегодня.", "Добро пожаловать в нашу команду.", "Не забудьте представиться.",
    "С уважением, админы.", "Мы здесь, чтобы помочь.", "Какое ваше хобби?",
    "Вопрос дня: любимый фильм?", "Это тестовое сообщение.", "Спасибо за присоединение!"
]

MIDDLE_EAST_SAMPLE_MESSAGES = {
    'egypt': [
        "أهلا من مصر!", "القاهرة جميلة هذه الأيام.", "ما رأيكم في الطعام المصري؟", "شاركنا صورك من مصر.",
        "تحياتي من مصر.", "الهندسة المعمارية هنا رائعة.", "مرحبًا بالجميع!", "كيف الأحوال؟",
        "نحن سعداء بانضمامكم.", "هل زرت الأهرامات؟", "ما هي مدينتك؟", "سؤال اليوم: ماذا تحب أن تأكل؟",
        "هذا نص عربي مصري.", "شكراً لكم!", "مرحبا!", "أهلا وسهلا.", "شارك برأيك.", "تواصل معنا.",
        "هل هناك أحد من الإسكندرية؟", "نأمل يومًا سعيدًا.", "نحن هنا للمساعدة."
    ],
    'lebanon': [
        "أهلاً بكم من لبنان.", "بيروت مدينة الثقافة.", "هل تحبون الطعام اللبناني؟", "شاركنا صورك من لبنان.",
        "ما رأيكم في البحر المتوسط؟", "نحن هنا للمناقشة.", "تحياتي للجميع.", "سؤال: ما هو أفضل مطعم؟",
        "هذا نص تجريبي.", "أهلاً وسهلاً.", "نرجو الالتزام بالقواعد.", "هل هناك فعاليات محلية اليوم؟",
        "نحن سعداء بوجودكم.", "شاركوا أخباركم.", "تحياتي.", "مرحبا!", "شكراً لانضمامكم!", "تواصل معنا عند الحاجة.",
        "نتمنى لكم يومًا سعيدًا.", "ما هي هواياتكم؟", "هذا مجرد اختبار."
    ]
}

# ---------- runtime state ----------
state = {
    'mode': DEFAULT_MODE,
    'owner': OWNER_USERNAME,
    'bio_template': BIO_TEMPLATE,
    'creating': False,
    'created_count': 0,
    'today_created': 0,
    'total_created': 0,
    'start_time': None,
}

# helpers
def month_short_name(dt: datetime):
    return dt.strftime('%b')

def build_group_name(num: int):
    now = datetime.now()
    return GROUP_NAME_TEMPLATE.format(month_name=month_short_name(now), day=now.day, num=num)

def build_bio(group_name: str):
    return state['bio_template'].format(owner=state['owner'], group_name=group_name)

def messages_for_mode(mode: str):
    if mode == 'arabic':
        return ARABIC_MESSAGES
    if mode == 'russian':
        return RUSSIAN_MESSAGES
    if mode.startswith('middleeast:'):
        country = mode.split(':',1)[1]
        return MIDDLE_EAST_SAMPLE_MESSAGES.get(country.lower(), MIDDLE_EAST_SAMPLE_MESSAGES['egypt'])
    return ARABIC_MESSAGES

# ---------- Telethon client setup ----------
if SESSION_STRING:
    session = StringSession(SESSION_STRING)
else:
    session = SESSION_NAME

client = TelegramClient(session, API_ID, API_HASH)

# owner check: allow only owner (username) or self
async def is_owner(event):
    try:
        sender = await event.get_sender()
        uname = getattr(sender, 'username', None)
        if uname and ('@'+uname).lower() == state['owner'].lower():
            return True
        me = await client.get_me()
        if sender and sender.id == me.id:
            return True
    except:
        pass
    return False

# parse count arg
def parse_count_arg(arg: str):
    arg = arg.strip().lower()
    if arg in ('unlimited','all'):
        return 'unlimited', []
    m = re.match(r'^(\d+)-(\d+)$', arg)
    if m:
        a = int(m.group(1)); b = int(m.group(2))
        if b < a: a,b = b,a
        return 'range', list(range(a,b+1))
    if ',' in arg:
        parts = [int(x.strip()) for x in arg.split(',') if x.strip().isdigit()]
        return 'list', parts
    if arg.isdigit():
        return 'count', int(arg)
    raise ValueError('Could not parse count argument')

# --- Command handlers ---
@client.on(events.NewMessage(pattern=r'^/set_mode\s+(.+)', outgoing=True))
async def set_mode_handler(event):
    if not await is_owner(event): return
    mode_raw = event.pattern_match.group(1).strip().lower()
    if mode_raw in ('arabic','russian'):
        state['mode'] = mode_raw
        await event.reply(f"Mode set to: {mode_raw}")
        return
    # assume country for middleeast
    state['mode'] = 'middleeast:' + mode_raw
    await event.reply(f"Mode set to Middle East country: {mode_raw}")

@client.on(events.NewMessage(pattern=r'^/set_owner\s+(.+)', outgoing=True))
async def set_owner_handler(event):
    if not await is_owner(event): return
    new_owner = event.pattern_match.group(1).strip()
    state['owner'] = new_owner
    await event.reply(f"Owner mention set to: {new_owner}")

@client.on(events.NewMessage(pattern=r'^/set_bio_template\s+(.+)', outgoing=True))
async def set_bio_handler(event):
    if not await is_owner(event): return
    template = event.pattern_match.group(1).strip()
    state['bio_template'] = template
    await event.reply('Bio template updated.')

@client.on(events.NewMessage(pattern=r'^/start_create\s+(.+)', outgoing=True))
async def start_create_handler(event):
    if not await is_owner(event): return
    arg = event.pattern_match.group(1).strip()
    try:
        mode, data = parse_count_arg(arg)
    except Exception:
        await event.reply('Could not parse argument. Use a number, range (1-50), list (1,5,10), or unlimited')
        return
    if state['creating']:
        await event.reply('Already creating. Send /stop to halt.')
        return
    state['creating'] = True
    state['start_time'] = datetime.now()
    created = 0
    await event.reply(f'Starting creation: {arg}. Mode={state["mode"]}. Owner={state["owner"]}')

    async def create_group_number(i):
        group_name = build_group_name(i)
        bio = build_bio(group_name)
        try:
            res = await client(functions.channels.CreateChannelRequest(
                title=group_name,
                about=bio,
                megagroup=True
            ))
            chat = res.chats[0]
        except FloodWaitError as f:
            await event.reply(f'FloodWait: sleeping {f.seconds}s')
            await asyncio.sleep(f.seconds + 1)
            return False
        except Exception as e:
            await event.reply(f'Error creating {group_name}: {e}')
            return False

        msgs = messages_for_mode(state['mode'])
        msgs_to_send = (msgs * ((20 // len(msgs)) + 2))[:20]
        try:
            for m in msgs_to_send:
                await client.send_message(chat.id, m)
                await asyncio.sleep(0.15)
        except Exception as e:
            # ignore post failures
            pass

        state['created_count'] += 1
        state['today_created'] += 1
        state['total_created'] += 1
        return True

    # unlimited loop
    if mode == 'unlimited':
        i = 1
        while state['creating']:
            await create_group_number(i)
            i += 1
            await asyncio.sleep(0.6)
        await event.reply('Stopped unlimited creation.')
        state['creating'] = False
        return

    # range/list/count
    iterable = []
    if mode == 'range' or mode == 'list':
        iterable = data
    elif mode == 'count':
        iterable = list(range(1, data+1))

    for n in iterable:
        if not state['creating']:
            break
        await create_group_number(n)
        await asyncio.sleep(0.5)

    state['creating'] = False
    await event.reply(f'Done creating requested groups.')

@client.on(events.NewMessage(pattern=r'^/stop$', outgoing=True))
async def stop_handler(event):
    if not await is_owner(event): return
    if not state['creating']:
        await event.reply('Not currently creating.')
        return
    state['creating'] = False
    await event.reply('Stopping creation...')

@client.on(events.NewMessage(pattern=r'^/status$', outgoing=True))
async def status_handler(event):
    if not await is_owner(event): return
    now = datetime.now()
    uptime = (now - state['start_time']).total_seconds() if state['start_time'] else 0
    text = (
        f"Session Statistics Summary\n"
        f"Total Sessions Available: 1\n"
        f"Total Groups Created: {state['total_created']}\n"
        f"Today's Groups: {state['today_created']}\n\n"
        f"Session Status:\n"
        f"Active: {'Yes' if state['creating'] else 'No'}\n"
        f"Daily Limited: 0\n"
        f"Total Limited: 0\n\n"
        f"View Options:\nEnter range (e.g., 1-50 or 10-100)\nEnter specific numbers (e.g., 1,5,10,25)\nEnter all to view all sessions (max 100 at once)\n"
    )
    await event.reply(text)

@client.on(events.NewMessage(pattern=r'^/menu$', outgoing=True))
async def menu_handler(event):
    if not await is_owner(event): return
    await event.respond('Mode quick menu:', buttons=[
        [Button.inline('Arabic', b'mode_arabic'), Button.inline('Russian', b'mode_russian')],
        [Button.inline('ME: Egypt', b'mode_me_egypt'), Button.inline('ME: Lebanon', b'mode_me_lebanon')]
    ])

@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    if data == 'mode_arabic':
        state['mode'] = 'arabic'
        await event.answer('Mode set to Arabic', alert=True)
    elif data == 'mode_russian':
        state['mode'] = 'russian'
        await event.answer('Mode set to Russian', alert=True)
    elif data == 'mode_me_egypt':
        state['mode'] = 'middleeast:egypt'
        await event.answer('Mode set to Middle East: Egypt', alert=True)
    elif data == 'mode_me_lebanon':
        state['mode'] = 'middleeast:lebanon'
        await event.answer('Mode set to Middle East: Lebanon', alert=True)

# ---- startup ----
async def main():
    print("Starting client...")
    await client.start()
    me = await client.get_me()
    print("Logged in as:", me.username or me.first_name)
    print("Owner:", state['owner'])
    print("Current mode:", state['mode'])
    print("Commands (send as outgoing messages from owner account):")
    print("/set_mode <arabic|russian|country>")
    print("/set_owner @Username")
    print("/set_bio_template <text>")
    print("/start_create <N|1-50|1,5,10|unlimited>")
    print("/stop")
    print("/status")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exiting...')
