from pyrogram import Client, filters
import asyncio
import random
from datetime import datetime
import motor.motor_asyncio
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME")
OWNER = os.getenv("OWNER_USERNAME")
MONGO = os.getenv("MONGO_URI")

client = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

db = motor.motor_asyncio.AsyncIOMotorClient(MONGO)
session_db = db["autogroups"]["stats"]

ARABIC_TEXTS = [
    "مرحبا كيف حالك",
    "هذا مثال نص عربي",
    "نص عربي تجريبي"
]

RUSSIAN_TEXTS = [
    "Привет как дела",
    "Это русский текст",
    "Тест русских сообщений"
]

COUNTRY_TEXTS = [
    "UAE group message",
    "Qatar sample text",
    "Saudi Arabia text"
]


def random_messages(mode):
    if mode == "arabic":
        return random.sample(ARABIC_TEXTS, 20)
    if mode == "russian":
        return random.sample(RUSSIAN_TEXTS, 20)
    return random.sample(COUNTRY_TEXTS, 20)


@client.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply("✅ Auto Group Creator Bot Running\nUse /create to make groups.")


@client.on_message(filters.command("create"))
async def create_group(_, msg):
    args = msg.text.split(" ")

    if len(args) < 2:
        return await msg.reply("Usage: /create arabic OR /create russian OR /create country")

    mode = args[1].lower()

    if mode not in ["arabic", "russian", "country"]:
        return await msg.reply("Invalid mode.")

    # numbering
    now = datetime.utcnow()
    day = now.strftime("%b %d")

    count = random.randint(1, 999)
    group_name = f"{day} Gc {count}"

    bio = f"{day} Gc {count} Owner - {OWNER}"

    # create group
    chat = await client.create_group(group_name, [msg.from_user.id])

    # set description
    await client.set_chat_description(chat.id, bio)

    # send sample messages
    for t in random_messages(mode):
        await client.send_message(chat.id, t)

    # save stats
    await session_db.insert_one({"group": group_name, "mode": mode, "date": str(now)})

    await msg.reply(f"✅ Group Created: {group_name}")


@client.on_message(filters.command("stats"))
async def stats(_, msg):
    total = await session_db.count_documents({})
    today = datetime.utcnow().strftime("%Y-%m-%d")
    today_count = await session_db.count_documents({"date": {"$regex": today}})

    text = f"""
📊 Session Statistics Summary

Total Sessions Available: 1
Total Groups Created: {total}
Today's Groups: {today_count}

Session Status:
Active: ✅
Daily Limited: 0
Total Limited: 0
"""
    await msg.reply(text)


client.run()
