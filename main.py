"""
Telegram Group Creator Userbot (Telethon)
+ Koyeb Health Check Fix (Flask Web Server on port 8000)
"""

import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, functions
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from flask import Flask
import threading

# ------- Koyeb web server -------
app = Flask(__name__)

@app.route("/")
def home():
    return "Userbot Running OK"

def run_web():
    app.run(host="0.0.0.0", port=8000)

threading.Thread(target=run_web).start()
# ----------------------------------------

# ---------- Load ENV ----------
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('TELETHON_SESSION_STRING', None)
OWNER_USERNAME = os.getenv('OWNER_USERNAME', '@Arya_Bro')

BIO_TEMPLATE = os.getenv('BIO_TEMPLATE', '{group_name} Owner - {owner}')
GROUP_NAME_TEMPLATE = os.getenv('GROUP_NAME_TEMPLATE', '{month_name} {day} Gc {num}')
DEFAULT_MODE = os.getenv('MODE', 'arabic')

if API_ID == 0 or not API_HASH:
    print("ERROR: API_ID/API_HASH missing")
    exit(1)

# ---------- Message banks ----------
ARABIC_MESSAGES = [
    "مرحبا بالجميع!", "كيف الحال؟", "أهلا وسهلا!", "من أي بلد أنتم؟",
    "تحياتنا لكم.", "مرحبا بكم.", "اهلا وسهلا بالجميع.",
    "اليوم جميل.", "شاركوا افكاركم.", "أهلا بكم معنا.",
] * 3

RUSSIAN_MESSAGES = [
    "Привет всем!", "Как дела?", "Добро пожаловать!", "Откуда вы?",
    "Мы рады вам!", "Хорошего дня!", "Пишите сообщения.",
] * 3

MIDDLE_EAST_SAMPLE_MESSAGES = {
    'egypt': ["أهلا من مصر!", "كيف الحال؟", "يوم جميل للجميع."] * 7,
    'lebanon': ["أهلا من لبنان!", "كيف بيروت اليوم؟", "مرحبا جميعا!"] * 7,
}

# ---------- Bot state ----------
state = {
    'mode': DEFAULT_MODE,
    'owner': OWNER_USERNAME.lower(),
    'creating': False,
    'total_created': 0,
    'today_created': 0,
}

# ---------- Helpers ----------
def month_short_name(dt):
    return dt.strftime('%b')

def build_group_name(i):
    now = datetime.now()
    return GROUP_NAME_TEMPLATE.format(
        month_name=month_short_name(now),
        day=now.day,
        num=i
    )

def build_bio(group_name):
    return BIO_TEMPLATE.format(group_name=group_name, owner=state['owner'])

def messages_for_mode(mode):
    if mode == "arabic":
        return ARABIC_MESSAGES
    if mode == "russian":
        return RUSSIAN_MESSAGES
    if mode.startswith("middleeast:"):
        country = mode.split(":", 1)[1]
        return MIDDLE_EAST_SAMPLE_MESSAGES.get(country, MIDDLE_EAST_SAMPLE_MESSAGES["egypt"])
    return ARABIC_MESSAGES

# ---------- Telethon Client ----------
session = StringSession(SESSION_STRING)
client = TelegramClient(session, API_ID, API_HASH)

# -------- owner check ---------
async def is_owner(event):
    try:
        sender = await event.get_sender()
        uname = (sender.username or "").lower()
        return uname == state['owner'].replace("@", "")
    except:
        return False

# -------- Commands --------
@client.on(events.NewMessage(pattern=r'^/start'))
async def start_handler(event):
    if not await is_owner(event): return
    await event.reply(
        "✅ Userbot Active!\n\nCommands:\n"
        "/set_mode <arabic|russian|middleeast:country>\n"
        "/start_create <count>\n"
        "/stop\n"
        "/status\n"
        "/autodelete on|off\n"
        "/cleansystem - delete old join/leave/pin msgs\n"
    )

@client.on(events.NewMessage(pattern=r'^/set_mode (.+)'))
async def mode_handler(event):
    if not await is_owner(event): return
    mode = event.pattern_match.group(1).strip().lower()
    if mode in ["arabic", "russian"]:
        state['mode'] = mode
    else:
        state['mode'] = "middleeast:" + mode
    await event.reply(f"✅ Mode set to {state['mode']}")

@client.on(events.NewMessage(pattern=r'^/start_create (\d+)'))
async def create_handler(event):
    if not await is_owner(event): return
    count = int(event.pattern_match.group(1))

    if state['creating']:
        await event.reply("⚠ Already running")
        return

    state['creating'] = True
    await event.reply(f"✅ Starting creation for {count} groups...")

    for i in range(1, count + 1):
        if not state['creating']:
            break

        name = build_group_name(i)
        bio = build_bio(name)

        try:
            res = await client(
                functions.channels.CreateChannelRequest(
                    title=name,
                    about=bio,
                    megagroup=True
                )
            )
            chat = res.chats[0]
        except FloodWaitError as f:
            await asyncio.sleep(f.seconds)
            continue

        msgs = messages_for_mode(state['mode'])[:20]
        for msg in msgs:
            await client.send_message(chat.id, msg)
            await asyncio.sleep(0.2)

        state['total_created'] += 1
        state['today_created'] += 1
        await asyncio.sleep(1)

    state['creating'] = False
    await event.reply("✅ Finished creation.")

@client.on(events.NewMessage(pattern=r'^/stop'))
async def stop_handler(event):
    if not await is_owner(event): return
    state['creating'] = False
    await event.reply("🛑 Stopped.")

@client.on(events.NewMessage(pattern=r'^/status'))
async def status_handler(event):
    if not await is_owner(event): return
    await event.reply(
        f"📊 Status:\n"
        f"Total: {state['total_created']}\n"
        f"Today: {state['today_created']}\n"
        f"Active: {state['creating']}"
    )

# -------- Auto Delete Join/Leave/Pin Messages --------
AUTO_DELETE = False
DELETE_KEYWORDS = [
    "joined the group",
    "left the group",
    "was removed",
    "was kicked",
    "pinned a message",
    "unpinned a message"
]

@client.on(events.NewMessage(pattern=r"^/autodelete(?:\s+(on|off))?$"))
async def toggle_autodelete(event):
    """Turn AutoDelete on/off or check status"""
    global AUTO_DELETE
    if not await is_owner(event):
        return
    arg = event.pattern_match.group(1)
    if not arg:
        await event.reply(f"🧹 AutoDelete is currently **{'ON' if AUTO_DELETE else 'OFF'}**")
        return
    AUTO_DELETE = (arg.lower() == "on")
    await event.reply(f"🧹 AutoDelete is now **{'ON' if AUTO_DELETE else 'OFF'}**")

@client.on(events.NewMessage())
async def auto_delete_messages(event):
    """Deletes join/leave/pin system messages when enabled"""
    if not AUTO_DELETE:
        return
    try:
        if not event.is_group:
            return

        if event.message.action:
            await event.delete()
            return

        text = (event.raw_text or "").lower()
        if any(k in text for k in DELETE_KEYWORDS):
            await event.delete()
    except Exception as e:
        print("Delete error:", e)

# -------- Manual Cleanup Command --------
@client.on(events.NewMessage(pattern=r"^/cleansystem$"))
async def clean_system_messages(event):
    """Deletes old system messages manually"""
    if not await is_owner(event):
        return

    if not AUTO_DELETE:
        await event.reply("⚠️ Please enable AutoDelete first using /autodelete on")
        return

    chat = await event.get_input_chat()
    await event.reply("🧹 Starting cleanup of recent system messages...")

    deleted_count = 0
    async for msg in client.iter_messages(chat, limit=500):
        try:
            if msg.action:
                await msg.delete()
                deleted_count += 1
                continue
            text = (msg.raw_text or "").lower()
            if any(k in text for k in DELETE_KEYWORDS):
                await msg.delete()
                deleted_count += 1
        except Exception as e:
            print("Cleanup error:", e)

    await event.reply(f"✅ Cleanup done — deleted {deleted_count} system messages.")

# ---------- Start ----------
async def main():
    print("Starting Telethon session...")
    await client.start()
    me = await client.get_me()
    print("Logged in as:", me.username or me.first_name)
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
