# main.py
"""
Telegram Group Creator Userbot (Telethon)
+ Koyeb Health Check Fix (Flask Web Server on port 8000)
"""

import os
import asyncio
import re
from datetime import datetime
from telethon import TelegramClient, events, Button, functions
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ------- Koyeb web server (added) -------
from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return "Userbot Running"

def run_web():
    app.run(host="0.0.0.0", port=8000)

threading.Thread(target=run_web).start()
# ----------------------------------------

# ---------- Config from env ----------
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
SESSION_NAME = os.getenv('SESSION_NAME', 'AryaSession')
SESSION_STRING = os.getenv('TELETHON_SESSION_STRING', None)
OWNER_USERNAME = os.getenv('OWNER_USERNAME', '@Arya_Bro')
BIO_TEMPLATE = os.getenv('BIO_TEMPLATE', '{group_name} Owner - {owner}')
GROUP_NAME_TEMPLATE = os.getenv('GROUP_NAME_TEMPLATE', '{month_name} {day} Gc {num}')
DEFAULT_MODE = os.getenv('MODE', 'arabic')

if API_ID == 0 or API_HASH == '':
    print("ERROR: Set API_ID and API_HASH correctly.")
    exit(1)

# ---------- Message banks ----------
ARABIC_MESSAGES = [
    "مرحبا بالجميع!", "كيف الحال؟", "أهلا وسهلا في المجموعة.", "من أي بلد أنتم؟",
    "تواصلوا معنا دائمًا.", "نتمنى لكم يومًا سعيدًا!", "ما هي اهتماماتكم؟",
    "هل تحبون الأخبار؟", "شاركوا صوركم.", "مرحبًا بالجميع نرجو الالتزام بالقواعد.",
    "هل هناك متحدثين باللغة الإنجليزية؟", "ما رأيكم في هذا الموضوع؟",
    "يرجى احترام الجميع.", "تحديث جديد اليوم.", "أهلاً بكم في فريقنا.",
    "لا تنسوا تقديم أنفسكم.", "تحياتنا من المشرفين.", "نحن هنا للمساعدة.",
    "ما هي هواياتكم؟", "سؤال اليوم: ما هو فيلمكم المفضل؟",
    "شكراً لانضمامكم!"
]

RUSSIAN_MESSAGES = [
    "Привет всем!", "Как дела?", "Добро пожаловать в группу.", "Откуда вы?",
    "Свяжитесь в любое время.", "Хорошего дня!", "Какие интересы?",
    "Любите новости?", "Поделитесь фото.", "Соблюдайте правила.",
    "Есть англоговорящие?", "Что думаете об этом?",
    "Уважайте друг друга.", "Новое событие сегодня.",
    "Добро пожаловать!", "Представьтесь.", "Мы здесь чтобы помочь.",
    "Какое хобби у вас?", "Любимый фильм?", "Тестовое сообщение.",
    "Спасибо за присоединение!"
]

MIDDLE_EAST_SAMPLE_MESSAGES = {
    'egypt': [
        "أهلا من مصر!", "كيف الحال؟", "شاركنا صورك.", "الأهرامات رائعة!",
        "تحياتي!", "مرحبًا بالجميع.", "سؤال اليوم لك.", "أهلا وسهلا!"
    ] * 3,
    'lebanon': [
        "أهلا من لبنان!", "كيف بيروت اليوم؟", "هل تحب الطعام اللبناني؟",
        "شاركنا صورك.", "مرحبا بالجميع!", "تحياتي.", "نحن هنا للدعم."
    ] * 3
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
    return GROUP_NAME_TEMPLATE.format(
        month_name=month_short_name(now),
        day=now.day,
        num=num
    )

def build_bio(group_name: str):
    return state['bio_template'].format(owner=state['owner'], group_name=group_name)

def messages_for_mode(mode: str):
    if mode == 'arabic':
        return ARABIC_MESSAGES
    if mode == 'russian':
        return RUSSIAN_MESSAGES
    if mode.startswith('middleeast:'):
        country = mode.split(':', 1)[1]
        return MIDDLE_EAST_SAMPLE_MESSAGES.get(country, MIDDLE_EAST_SAMPLE_MESSAGES['egypt'])
    return ARABIC_MESSAGES

# ---------- Telethon client setup ----------
session = StringSession(SESSION_STRING) if SESSION_STRING else SESSION_NAME
client = TelegramClient(session, API_ID, API_HASH)

async def is_owner(event):
    try:
        sender = await event.get_sender()
        uname = getattr(sender, 'username', None)
        if uname and ('@' + uname).lower() == state['owner'].lower():
            return True
        me = await client.get_me()
        return sender.id == me.id
    except:
        return False

def parse_count_arg(arg: str):
    arg = arg.strip().lower()
    if arg in ('unlimited', 'all'):
        return 'unlimited', []
    if re.match(r'^\d+-\d+$', arg):
        a, b = map(int, arg.split('-'))
        if b < a: a, b = b, a
        return 'range', list(range(a, b+1))
    if ',' in arg:
        return 'list', [int(x) for x in arg.split(',') if x.strip().isdigit()]
    if arg.isdigit():
        return 'count', int(arg)
    raise ValueError

# ------------ COMMANDS (same as before) ------------

@client.on(events.NewMessage(pattern=r'^/set_mode\s+(.+)', outgoing=True))
async def set_mode_handler(event):
    if not await is_owner(event): return
    mode_raw = event.pattern_match.group(1).strip().lower()
    if mode_raw in ('arabic', 'russian'):
        state['mode'] = mode_raw
    else:
        state['mode'] = 'middleeast:' + mode_raw
    await event.reply(f"Mode set to: {state['mode']}")

@client.on(events.NewMessage(pattern=r'^/set_owner\s+(.+)', outgoing=True))
async def set_owner_handler(event):
    if not await is_owner(event): return
    state['owner'] = event.pattern_match.group(1).strip()
    await event.reply(f"Owner set to {state['owner']}")

@client.on(events.NewMessage(pattern=r'^/set_bio_template\s+(.+)', outgoing=True))
async def set_bio_handler(event):
    if not await is_owner(event): return
    state['bio_template'] = event.pattern_match.group(1).strip()
    await event.reply('Bio template updated.')

@client.on(events.NewMessage(pattern=r'^/start_create\s+(.+)', outgoing=True))
async def start_create_handler(event):
    if not await is_owner(event): return

    try:
        mode, data = parse_count_arg(event.pattern_match.group(1).strip())
    except:
        await event.reply("Invalid format.")
        return

    if state['creating']:
        await event.reply("Already creating.")
        return

    state['creating'] = True
    state['start_time'] = datetime.now()

    await event.reply(f"Started... Mode {state['mode']}")

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
            await asyncio.sleep(f.seconds + 1)
            return False
        except Exception as e:
            await event.reply(f"Error: {e}")
            return False

        msgs = messages_for_mode(state['mode'])[:20]
        for m in msgs:
            try:
                await client.send_message(chat.id, m)
                await asyncio.sleep(0.2)
            except:
                pass

        state['total_created'] += 1
        state['today_created'] += 1
        return True

    if mode == 'unlimited':
        i = 1
        while state['creating']:
            await create_group_number(i)
            i += 1
            await asyncio.sleep(0.5)
        return

    if mode == 'range' or mode == 'list':
        nums = data
    else:
        nums = list(range(1, data + 1))

    for n in nums:
        if not state['creating']:
            break
        await create_group_number(n)
        await asyncio.sleep(0.5)

    state['creating'] = False
    await event.reply("Finished.")

@client.on(events.NewMessage(pattern=r'^/stop$', outgoing=True))
async def stop_handler(event):
    if not await is_owner(event): return
    state['creating'] = False
    await event.reply("Stopped.")

@client.on(events.NewMessage(pattern=r'^/status$', outgoing=True))
async def status_handler(event):
    if not await is_owner(event): return
    await event.reply(
        f"Total: {state['total_created']}\n"
        f"Today: {state['today_created']}\n"
        f"Active: {state['creating']}"
    )

# ---- startup ----
async def main():
    print("Starting client...")
    await client.start()
    me = await client.get_me()
    print("Logged in as:", me.username or me.first_name)
    await client.run_until_disconnected()

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
