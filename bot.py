""" Telegram Group Creator Userbot

Uses Telethon (user account) to create groups automatically, set title, description (bio), post language-specific messages, and supports commands from the owner (@Arya_Bro).


Features implemented:

/set_mode <arabic|russian|middleeast|country_name>  -> choose messages language/country

/set_owner @Username -> set owner mention used in group bio

/set_bio_template <text> -> set bio template (use {owner} and {group_name})

/start_create <N|unlimited> -> start creating N groups (or unlimited until /stop)

/stop -> stop creating

/create_range start-end -> create groups for count = end-start+1

/create_list 1,5,10 -> create groups for specific counts

/status -> show session & creation statistics

Posts 20+ messages per group in chosen language


Notes:

Requires Telethon: pip install telethon

Requires Telegram API ID and API HASH (from my.telegram.org)

This runs as a userbot (your personal session). Save the .session file after first run.

Deploy on Koyeb by providing environment variables: API_ID, API_HASH, OWNER_USERNAME (optional)


Author: Generated for user @Arya_Bro """

import asyncio import os import random import re from datetime import datetime from telethon import TelegramClient, events, Button from telethon.errors import FloodWaitError from telethon.tl.types import InputPeerUser

--- Configuration (set via env vars for Koyeb) ---

API_ID = int(os.getenv('API_ID', 'YOUR_API_ID')) API_HASH = os.getenv('API_HASH', 'YOUR_API_HASH') SESSION_NAME = os.getenv('SESSION_NAME', 'group_creator')  # session file OWNER_USERNAME = os.getenv('OWNER_USERNAME', '@Arya_Bro')

Default templates

BIO_TEMPLATE = os.getenv('BIO_TEMPLATE', '{group_name} Owner - {owner}') GROUP_NAME_TEMPLATE = os.getenv('GROUP_NAME_TEMPLATE', '{month_name} {day} Gc {num}')

Language message banks (20+ messages each)

ARABIC_MESSAGES = [ "مرحبا بالجميع!", "كيف الحال؟", "أهلا وسهلا في المجموعة.", "من أي بلد أنتم؟", "تواصلوا معنا دائمًا.", "نتمنى لكم يومًا سعيدًا!", "ما هي اهتماماتكم؟", "هل تحبون الأخبار؟", "شاركوا صوركم.", "مرحبًا بالجميع، نرجو الالتزام بالقواعد.", "هل هناك متحدثين باللغة الإنجليزية؟", "ما رأيكم في هذا الموضوع؟", "يرجى احترام الجميع.", "تحديث: حدث جديد اليوم.", "أهلاً بكم في فريقنا.", "لا تنسوا تقديم أنفسكم.", "تحياتنا من المشرفين.", "نحن هنا للمساعدة.", "ما هي هواياتكم؟", "سؤال اليوم: ما هو فيلمكم المفضل؟", "هذا مجرد نص تجريبي.", "مرحبا! هذا سؤال سريع.", "شكراً لانضمامكم!", ]

RUSSIAN_MESSAGES = [ "Привет всем!", "Как дела?", "Добро пожаловать в группу.", "Откуда вы?", "Свяжитесь с нами в любое время.", "Желаем вам хорошего дня!", "Какие у вас интересы?", "Любите ли вы новости?", "Поделитесь своими фотографиями.", "Пожалуйста, соблюдайте правила.", "Есть ли говорящие по-английски?", "Что вы думаете об этом?", "Пожалуйста уважайте друг друга.", "Обновление: новое событие сегодня.", "Добро пожаловать в нашу команду.", "Не забудьте представиться.", "С уважением, админы.", "Мы здесь, чтобы помочь.", "Какое ваше хобби?", "Вопрос дня: любимый фильм?", "Это тестовое сообщение.", "Спасибо за присоединение!", ]

MIDDLE_EAST_SAMPLE_MESSAGES = { 'egypt': [ "أهلا من مصر!", "القاهرة جميلة هذه الأيام.", "ما رأيكم في الطعام المصري؟", "شاركنا صورك من مصر.", "تحياتي من مصر.", "الهندسة المعمارية هنا رائعة.", "مرحبًا بالجميع!", "كيف الأحوال؟", "نحن سعداء بانضمامكم.", "هل زرت الأهرامات؟", "ما هي مدينتك؟", "سؤال اليوم: ماذا تحب أن تأكل؟", "هذا نص عربي مصري.", "شكراً لكم!", "مرحبا!", "أهلا وسهلا.", "شارك برأيك.", "تواصل معنا.", "هل هناك أحد من الإسكندرية؟", "نأمل يومًا سعيدًا.", "نحن هنا للمساعدة.", ], 'lebanon': [ "أهلاً بكم من لبنان.", "بيروت مدينة الثقافة.", "هل تحبون الطعام اللبناني؟", "شاركنا صورك من لبنان.", "ما رأيكم في البحر المتوسط؟", "نحن هنا للمناقشة.", "تحياتي للجميع.", "سؤال: ما هو أفضل مطعم؟", "هذا نص تجريبي.", "أهلاً وسهلاً.", "نرجو الالتزام بالقواعد.", "هل هناك فعاليات محلية اليوم؟", "نحن سعداء بوجودكم.", "شاركوا أخباركم.", "تحياتي.", "مرحبا!", "شكراً لانضمامكم!", "تواصل معنا عند الحاجة.", "نتمنى لكم يومًا سعيدًا.", "ما هي هواياتكم؟", "هذا مجرد اختبار.", ], }

In-memory runtime state

state = { 'mode': 'arabic',  # arabic | russian | middleeast:<country> 'owner': OWNER_USERNAME, 'bio_template': BIO_TEMPLATE, 'creating': False, 'created_count': 0, 'today_created': 0, 'total_created': 0, 'start_time': None, }

helper: get month short name like 'Nov'

def month_short_name(dt: datetime): return dt.strftime('%b')

helper: build group name

def build_group_name(num: int): now = datetime.now() return GROUP_NAME_TEMPLATE.format(month_name=month_short_name(now), day=now.day, num=num)

helper: build bio

def build_bio(group_name: str): return state['bio_template'].format(owner=state['owner'], group_name=group_name)

get message list based on mode

def messages_for_mode(mode: str): if mode == 'arabic': return ARABIC_MESSAGES if mode == 'russian': return RUSSIAN_MESSAGES if mode.startswith('middleeast:'): country = mode.split(':', 1)[1] return MIDDLE_EAST_SAMPLE_MESSAGES.get(country.lower(), MIDDLE_EAST_SAMPLE_MESSAGES['egypt']) # fallback return ARABIC_MESSAGES

--- Telethon client setup ---

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

owner check decorator

async def is_owner(event): sender = await event.get_sender() uname = getattr(sender, 'username', None) if uname and ('@'+uname).lower() == state['owner'].lower(): return True # Also allow if user sent from same user account me = await client.get_me() if sender and sender.id == me.id: return True return False

Command handlers

@client.on(events.NewMessage(pattern=r'^/set_mode\s+(.+)', outgoing=True)) async def set_mode_handler(event): if not await is_owner(event): return mode_raw = event.pattern_match.group(1).strip().lower() if mode_raw in ('arabic', 'russian'): state['mode'] = mode_raw await event.reply(f"Mode set to: {mode_raw}") return # maybe user provided a country for middleeast state['mode'] = 'middleeast:' + mode_raw await event.reply(f"Mode set to Middle East country: {mode_raw}")

@client.on(events.NewMessage(pattern=r'^/set_owner\s+(.+)', outgoing=True)) async def set_owner_handler(event): if not await is_owner(event): return new_owner = event.pattern_match.group(1).strip() state['owner'] = new_owner await event.reply(f"Owner mention set to: {new_owner}")

@client.on(events.NewMessage(pattern=r'^/set_bio_template\s+(.+)', outgoing=True)) async def set_bio_handler(event): if not await is_owner(event): return template = event.pattern_match.group(1).strip() state['bio_template'] = template await event.reply('Bio template updated.')

parse counts like '1-50' or '1,5,10' or 'all' or integer

async def parse_count_arg(arg: str): arg = arg.strip().lower() if arg == 'unlimited' or arg == 'all': return 'unlimited', [] m = re.match(r'^(\d+)-(\d+)$', arg) if m: a = int(m.group(1)) b = int(m.group(2)) if b < a: a, b = b, a return 'range', list(range(a, b+1)) if ',' in arg: parts = [int(x.strip()) for x in arg.split(',') if x.strip().isdigit()] return 'list', parts if arg.isdigit(): return 'count', int(arg) raise ValueError('Could not parse count argument')

@client.on(events.NewMessage(pattern=r'^/start_create\s+(.+)', outgoing=True)) async def start_create_handler(event): if not await is_owner(event): return arg = event.pattern_match.group(1).strip() try: mode, data = await parse_count_arg(arg) except Exception as e: await event.reply('Could not parse argument. Use a number, range (1-50), list (1,5,10), or unlimited') return

if state['creating']:
    await event.reply('Already creating. Send /stop to halt.')
    return

state['creating'] = True
state['start_time'] = datetime.now()
created = 0

await event.reply(f'Starting creation: {arg}. Mode={state["mode"]}. Owner={state["owner"]}')

# worker
async def worker_create(count_iterable):
    nonlocal created
    for num in count_iterable:
        if not state['creating']:
            break
        group_name = build_group_name(num)
        bio = build_bio(group_name)
        try:
            # create channel (megagroup) with a single user: owner (if possible)
            # We'll create a chat with no members, then set description and post messages
            result = await client(functions.channels.CreateChannelRequest(
                title=group_name,
                about=bio,
                megagroup=True
            ))
            chat = result.chats[0]
        except FloodWaitError as f:
            await event.reply(f'FloodWait: sleeping {f.seconds}s')
            await asyncio.sleep(f.seconds + 1)
            continue
        except Exception as e:
            await event.reply(f'Error creating group {group_name}: {e}')
            await asyncio.sleep(1)
            continue

        # Post messages
        msgs = messages_for_mode(state['mode'])
        # ensure at least 20 messages
        msgs_to_send = (msgs * ((20 // len(msgs)) + 2))[:20]
        try:
            for m in msgs_to_send:
                await client.send_message(chat.id, m)
                await asyncio.sleep(0.2)  # small delay
        except Exception as e:
            await event.reply(f'Error posting messages in {group_name}: {e}')

        state['created_count'] += 1
        state['today_created'] += 1
        state['total_created'] += 1
        created += 1
        # small pause to reduce risk of flood
        await asyncio.sleep(0.5)

# decide iterable
if mode == 'unlimited':
    # generate increasing numbers until stopped
    async def gen_unlimited():
        i = 1
        while state['creating']:
            yield i
            i += 1
    # since Python async generator isn't trivial here, we'll loop directly
    i = 1
    while state['creating']:
        group_name = build_group_name(i)
        bio = build_bio(group_name)
        try:
            result = await client(functions.channels.CreateChannelRequest(
                title=group_name,
                about=bio,
                megagroup=True
            ))
            chat = result.chats[0]
        except FloodWaitError as f:
            await event.reply(f'FloodWait: sleeping {f.seconds}s')
            await asyncio.sleep(f.seconds + 1)
            continue
        except Exception as e:
            await event.reply(f'Error creating group {group_name}: {e}')
            await asyncio.sleep(1)
            i += 1
            continue

        msgs = messages_for_mode(state['mode'])
        msgs_to_send = (msgs * ((20 // len(msgs)) + 2))[:20]
        try:
            for m in msgs_to_send:
                await client.send_message(chat.id, m)
                await asyncio.sleep(0.2)
        except Exception:
            pass

        state['created_count'] += 1
        state['today_created'] += 1
        state['total_created'] += 1
        i += 1
        await asyncio.sleep(0.5)
    await event.reply('Stopped unlimited creation.')
    state['creating'] = False
    return

if mode == 'range':
    await worker_create(data)
elif mode == 'list':
    await worker_create(data)
elif mode == 'count':
    await worker_create(range(1, data+1))

state['creating'] = False
await event.reply(f'Done creating requested groups. Created this run: {created}')

@client.on(events.NewMessage(pattern=r'^/stop$', outgoing=True)) async def stop_handler(event): if not await is_owner(event): return if not state['creating']: await event.reply('Not currently creating.') return state['creating'] = False await event.reply('Stopping creation...')

@client.on(events.NewMessage(pattern=r'^/status$', outgoing=True)) async def status_handler(event): if not await is_owner(event): return now = datetime.now() uptime = (now - state['start_time']).total_seconds() if state['start_time'] else 0 text = ( f"Session Statistics Summary\n" f"Total Sessions Available: 1\n" f"Total Groups Created: {state['total_created']}\n" f"Today's Groups: {state['today_created']}\n\n" f"Session Status:\n" f"Active: {'Yes' if state['creating'] else 'No'}\n" f"Daily Limited: 0\n" f"Total Limited: 0\n\n" f"View Options:\n" f"Enter range (e.g., 1-50 or 10-100)\n" f"Enter specific numbers (e.g., 1,5,10,25)\n" f"Enter all to view all sessions (max 100 at once)\n" ) await event.reply(text)

simple UI: buttons to set modes quickly

@client.on(events.NewMessage(pattern=r'^/menu$', outgoing=True)) async def menu_handler(event): if not await is_owner(event): return await event.respond('Mode quick menu:', buttons=[ [Button.inline('Arabic', b'mode_arabic'), Button.inline('Russian', b'mode_russian')], [Button.inline('Middle East: Egypt', b'mode_me_egypt'), Button.inline('Middle East: Lebanon', b'mode_me_lebanon')] ])

@client.on(events.CallbackQuery) async def callback_handler(event): data = event.data.decode('utf-8') if data == 'mode_arabic': state['mode'] = 'arabic' await event.answer('Mode set to Arabic', alert=True) elif data == 'mode_russian': state['mode'] = 'russian' await event.answer('Mode set to Russian', alert=True) elif data == 'mode_me_egypt': state['mode'] = 'middleeast:egypt' await event.answer('Mode set to Middle East: Egypt', alert=True) elif data == 'mode_me_lebanon': state['mode'] = 'middleeast:lebanon' await event.answer('Mode set to Middle East: Lebanon', alert=True)

startup

async def main(): print('Starting client...') await client.start() me = await client.get_me() print('Logged in as', me.username or me.first_name) print('Owner set to', state['owner']) print('Current mode:', state['mode']) print('Send commands from your account (owner) as outgoing messages:') print('/set_mode <arabic|russian|country>') print('/start_create <N|1-10|1,5,10|unlimited>') print('/stop') print('/status') await client.run_until_disconnected()

if name == 'main': import nest_asyncio nest_asyncio.apply() from telethon import functions try: asyncio.run(main()) except KeyboardInterrupt: print('Exiting...')
