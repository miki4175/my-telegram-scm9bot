import asyncio
import sqlite3
import datetime
import time
import random
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, PreCheckoutQuery, LabeledPrice, BotCommand, BotCommandScopeChat, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.dispatcher.event.bases import SkipHandler

bot = Bot(token="9260541145:AAHA_EiTKqGt-Q3pOF-uIlW9Mz4EQeyKYYM")
dp = Dispatcher()

ADMIN_ID = 7952502458
BOT_USERNAME = "scmofferslust_bot"
CHANNEL_LINK = "https://t.me/luvofers" 
PRIVATE_CHANNEL_LINK = "https://t.me/+ZR08sk1nSP5iYWNk"

PROMOCODES = {
    "SCAM10": 10,
    "LUCK5": 5,
    "LUCK10": 10,
    "LUCK20": 20,
}

CASE_FILE = "cases.json"

def load_cases():
    if os.path.exists(CASE_FILE):
        try:
            with open(CASE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cases(data):
    with open(CASE_FILE, "w") as f:
        json.dump(data, f)

def check_case_cooldown(user_id):
    cases = load_cases()
    if str(user_id) not in cases:
        return True, 0
    last_open = datetime.datetime.strptime(cases[str(user_id)], "%Y-%m-%d %H:%M:%S")
    hours_passed = (datetime.datetime.now() - last_open).total_seconds() / 3600
    if hours_passed >= 24:
        return True, 0
    return False, round(24 - hours_passed, 1)

def set_case_cooldown(user_id):
    cases = load_cases()
    cases[str(user_id)] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_cases(cases)

def init_db():
    if os.path.exists('users.db'):
        os.remove('users.db')
        
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        expire_date TEXT,
        referrer_id INTEGER,
        has_bought INTEGER DEFAULT 0,
        last_purchase_date TEXT,
        full_name TEXT,
        username TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        purchase_date TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS banned_users (
        user_id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT
    )''')
    conn.commit()
    conn.close()

def set_access(user_id, days):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    if days == 0:
        expire = "forever"
    else:
        expire = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR REPLACE INTO users (user_id, expire_date, referrer_id, has_bought) VALUES (?, ?, COALESCE((SELECT referrer_id FROM users WHERE user_id=?), NULL), COALESCE((SELECT has_bought FROM users WHERE user_id=?), 0))", (user_id, expire, user_id, user_id))
    conn.commit()
    conn.close()

def check_and_clear_access(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT expire_date FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        return None
    expire = res[0]
    if expire == "forever":
        conn.close()
        return "Навсегда"
    expire_date = datetime.datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
    if expire_date <= datetime.datetime.now():
        cursor.execute("UPDATE users SET expire_date = NULL WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return "Истекла"
    else:
        conn.close()
        return expire

def add_user(user_id, full_name, username, referrer_id=None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, referrer_id, has_bought, full_name, username) VALUES (?, ?, 0, ?, ?)", (user_id, referrer_id, full_name, username))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def add_payment(user_id, amount):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO payments (user_id, amount, purchase_date) VALUES (?, ?, ?)", (user_id, amount, now))
    cursor.execute("UPDATE users SET last_purchase_date = ? WHERE user_id = ?", (now, user_id))
    conn.commit()
    conn.close()

def get_ref_stats(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
    total_invited = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ? AND has_bought = 1", (user_id,))
    bought_count = cursor.fetchone()[0]
    conn.close()
    return total_invited, bought_count

def is_banned(user_id):
    conn = sqlite3.connect('users.db')
    res = conn.execute("SELECT user_id FROM banned_users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return res is not None

def ban_user(user_id, full_name, username):
    conn = sqlite3.connect('users.db')
    conn.execute("INSERT OR REPLACE INTO banned_users (user_id, full_name, username) VALUES (?, ?, ?)", (user_id, full_name, username))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect('users.db')
    conn.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_banned_list():
    conn = sqlite3.connect('users.db')
    res = conn.execute("SELECT user_id, full_name, username FROM banned_users").fetchall()
    conn.close()
    return res

@dp.message(F.text | F.photo | F.video | F.document)
async def check_ban_message(message: Message, **kwargs):
    if is_banned(message.from_user.id):
        return 
    raise SkipHandler()

@dp.callback_query()
async def check_ban_callback(call: CallbackQuery, **kwargs):
    if is_banned(call.from_user.id):
        await call.answer()
        return
    raise SkipHandler()

def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 ПОДПИСКА", callback_data="menu:subscribe")
    builder.button(text="🎁 КЕЙС ФОРТУНЫ", callback_data="menu:case")
    builder.button(text="🔑 МОЙ ДОСТУП", callback_data="menu:access")
    builder.button(text="👥 РЕФЕРАЛЬНАЯ СИСТЕМА", callback_data="menu:referral")
    builder.button(text="🤝 ПАРТНЕРСТВО", callback_data="menu:partnership")
    builder.button(text="🎟 ТГК (АКТУАЛЬНЫЕ ПРОМО)", callback_data="menu:channel")
    builder.adjust(1)
    return builder.as_markup()

def get_sub_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="7 дней - 150 ⭐", callback_data="sub_info:7")
    builder.button(text="30 дней - 300 ⭐", callback_data="sub_info:30")
    builder.button(text="Навсегда - 500 ⭐", callback_data="sub_info:0")
    builder.button(text="⬅️ Назад", callback_data="menu:back")
    builder.adjust(1)
    return builder.as_markup()

async def safe_answer(call: CallbackQuery):
    try:
        await call.answer(cache_time=0)
    except:
        pass

async def send_access_info(message_or_call):
    user_id = message_or_call.from_user.id
    status = check_and_clear_access(user_id)
    is_admin = (user_id == ADMIN_ID)
    builder = InlineKeyboardBuilder()
    
    if status == "Навсегда":
        builder.button(text="🔓 Войти в закрытый канал", url=PRIVATE_CHANNEL_LINK)
        if is_admin:
            builder.button(text="🎁 Тест подписка (Админ)", callback_data="admin_test")
        text = f"💎 <b>Ваш доступ:</b> Навсегда (вечный доступ)\n\n<i>Узнать свой ID: @userinfobot</i>\n\nДобро пожаловать в закрытый канал:"
        await message_or_call.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    elif status == "Истекла":
        if is_admin:
            builder.button(text="🎁 Тест подписка (Админ)", callback_data="admin_test")
        text = f"❌ <b>Ваша подписка истекла!</b>\n\n<i>Узнать свой ID: @userinfobot</i>\n\nВы можете продлить её в разделе «Подписка»."
        markup = builder.as_markup() if is_admin else None
        await message_or_call.answer(text, reply_markup=markup, parse_mode="HTML")
    elif status:
        builder.button(text="🔓 Войти в закрытый канал", url=PRIVATE_CHANNEL_LINK)
        if is_admin:
            builder.button(text="🎁 Тест подписка (Админ)", callback_data="admin_test")
        text = f"✅ <b>Ваша подписка активна до:</b>\n{status}\n\n<i>Узнать свой ID: @userinfobot</i>\n\nДобро пожаловать в закрытый канал:"
        await message_or_call.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        if is_admin:
            builder.button(text="🎁 Тест подписка (Админ)", callback_data="admin_test")
        text = f"🔒 <b>У вас нет активной подписки.</b>\n\n<i>Узнать свой ID: @userinfobot</i>\n\nКупите её в разделе «Подписка», чтобы получить доступ."
        markup = builder.as_markup() if is_admin else None
        await message_or_call.answer(text, reply_markup=markup, parse_mode="HTML")

@dp.message(CommandStart())
async def cmd_start(message: Message, command: Command):
    args = command.args
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username if message.from_user.username else ""
    referrer_id = None
    if args and args.startswith("ref_"):
        referrer_id = int(args.split("_")[1])
        if referrer_id == user_id:
            referrer_id = None
    is_new = add_user(user_id, full_name, username, referrer_id)
    if is_new:
        try:
            u = f"@{username}" if username else "нет юза"
            await bot.send_message(ADMIN_ID, f"👤 <b>Новый юзер:</b> {full_name} ({u})\nID: <code>{user_id}</code>", parse_mode="HTML")
        except:
            pass
    
    line = "―" * 36
    welcome_text = (
        "<b>SCM Offers</b>\n"
        f"{line}\n"
        "Управление доступом и рабочими инструментами.\n\n"
        "Выберите раздел:"
    )
    
    # --- ОТПРАВКА ВИДЕО С ЗАЩИТОЙ ---
    try:
        video = FSInputFile("VID_20261105_004655_088.mp4")
        await message.answer_video(video=video, caption=welcome_text, reply_markup=get_main_menu(), parse_mode="HTML")
    except Exception as e:
        # Если видео не отправилось, отправляем текст
        print(f"Ошибка видео: {e}")
        await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="HTML")
    # ---------------------------------

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    if message.reply_to_message and message.reply_to_message.forward_from:
        user = message.reply_to_message.forward_from
        ban_user(user.id, user.full_name, user.username)
        await message.answer(f"✅ Забанен (из пересланного): {user.full_name} | ID: {user.id}")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Пиши так: <code>/ban ID</code> или перешли сообщение и напиши <code>/ban</code> в ответ.", parse_mode="HTML")
        return
    target = args[1].replace("@", "")
    if not target.isdigit():
        conn = sqlite3.connect('users.db')
        user = conn.execute("SELECT user_id, full_name, username FROM users WHERE LOWER(username) = LOWER(?)", (target,)).fetchone()
        conn.close()
        if user:
            ban_user(user[0], user[1], user[2])
            await message.answer(f"✅ Забанен: {user[1]} (@{user[2]}) | ID: {user[0]}")
        else:
            await message.answer(f"❌ Юзернейм @{target} не найден. Перешли сообщение от него и напиши /ban.")
        return
    target_id = int(target)
    conn = sqlite3.connect('users.db')
    user = conn.execute("SELECT full_name, username FROM users WHERE user_id = ?", (target_id,)).fetchone()
    conn.close()
    if user:
        ban_user(target_id, user[0], user[1])
        await message.answer(f"✅ Забанен: {user[0]} | ID: {target_id}")
    else:
        ban_user(target_id, "Неизвестный", "")
        await message.answer(f"✅ Забанен: Неизвестный | ID: {target_id}")

@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    if message.reply_to_message and message.reply_to_message.forward_from:
        target_id = message.reply_to_message.forward_from.id
        unban_user(target_id)
        await message.answer(f"✅ Разбанен (из пересланного) | ID: {target_id}")
        return
    try:
        target = message.text.split()[1]
        if target.isdigit():
            unban_user(int(target))
            await message.answer(f"✅ Разбанен: ID {target}")
        else:
            await message.answer("❌ Введи ID.")
    except IndexError:
        await message.answer("❌ Пиши так: <code>/unban ID</code>", parse_mode="HTML")

@dp.message(Command("bans"))
async def cmd_bans(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    banned = get_banned_list()
    if not banned:
        await message.answer("✅ Список забаненных пуст.")
        return
    text = "🚫 <b>Список забаненных:</b>\n\n"
    for b in banned:
        text += f"• {b[1]} (@{b[2]}) | ID: <code>{b[0]}</code>\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        set_access(message.from_user.id, 30)
        await message.answer("👑 Выдал тебе подписку на 30 дней.")
    else:
        await message.answer("⛔ Нет прав.")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM payments")
    res_all = cursor.fetchone()
    total_purchases = res_all[0] if res_all[0] else 0
    total_stars = res_all[1] if res_all[1] else 0
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM payments WHERE purchase_date LIKE ?", (f"{today}%",))
    res_today = cursor.fetchone()
    today_purchases = res_today[0] if res_today[0] else 0
    today_stars = res_today[1] if res_today[1] else 0
    conn.close()
    text = f"📊 <b>Статистика</b>\n\n👥 Юзеров: <b>{total_users}</b>\n📅 Сегодня: <b>{today_purchases}</b> покупок на <b>{today_stars} ⭐</b>\n💰 Всего: <b>{total_purchases}</b> покупок на <b>{total_stars} ⭐</b>"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give(message: Message):
    if message.from_user.id != ADMIN_ID:
        return 
    try:
        args = message.text.split()
        if len(args) == 2:
            days = int(args[1])
            target_id = message.from_user.id
            msg_text = f"✅ Вам выдана подписка на {days} дней."
        elif len(args) == 3:
            days = int(args[1])
            target_id = int(args[2])
            msg_text = f"✅ Пользователю {target_id} выдана подписка на {days} дней."
        else:
            raise ValueError
        set_access(target_id, days)
        await message.answer(msg_text)
    except (IndexError, ValueError):
        await message.answer("❌ Ошибка формата!\nПиши так: <code>/give ДНИ</code> или <code>/give ДНИ ID</code>", parse_mode="HTML")

@dp.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    await message.answer("Выберите период подписки:", reply_markup=get_sub_menu())

@dp.message(Command("access"))
async def cmd_access(message: Message):
    await send_access_info(message)

@dp.message(Command("referral"))
async def cmd_referral(message: Message):
    user_id = message.from_user.id
    total, bought = get_ref_stats(user_id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    text = f"👥 <b>Рефералка</b>\n\nПриглашено: <b>{total}/3</b>\n🔗 <code>{ref_link}</code>"
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ ГЛАВНОЕ МЕНЮ", callback_data="menu:back")
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.message(Command("channel"))
async def cmd_channel(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Перейти в канал", url=CHANNEL_LINK)
    await message.answer("АКТУАЛЬНЫЕ ПРОМОКОДЫ в канале.", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "menu:back")
async def on_back(call: CallbackQuery):
    await safe_answer(call)
    line = "―" * 36
    welcome_text = f"<b>SCM Offers</b>\n{line}\nУправление доступом и рабочими инструментами.\n\nВыберите раздел:"
    
    # Такая же защита при возврате в меню
    try:
        video = FSInputFile("VID_20261105_004655_088.mp4")
        await call.message.answer_video(video=video, caption=welcome_text, reply_markup=get_main_menu(), parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка видео: {e}")
        await call.message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "menu:subscribe")
async def on_subscribe(call: CallbackQuery):
    await safe_answer(call)
    await call.message.answer("Выберите период подписки:", reply_markup=get_sub_menu())

@dp.callback_query(F.data == "menu:case")
async def on_case(call: CallbackQuery):
    await safe_answer(call)
    can_open, hours_left = check_case_cooldown(call.from_user.id)
    builder = InlineKeyboardBuilder()
    if can_open:
        builder.button(text="🔓 Открыть кейс", callback_data="open_case")
    else:
        builder.button(text=f"⏳ Перезарядка ({hours_left} ч.)", callback_data="no_case")
    builder.button(text="⬅️ Назад", callback_data="menu:back")
    text = "🎁 <b>КЕЙС ФОРТУНЫ</b>\n\n📦 Внутри: Пусто, Скидка 5%, 10%, 20%.\n<i>1 раз в 24 часа.</i>"
    await call.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data == "no_case")
async def on_no_case(call: CallbackQuery):
    await safe_answer(call)
    await call.answer("Кейс еще не перезарядился!", show_alert=True)

@dp.callback_query(F.data == "open_case")
async def on_open_case(call: CallbackQuery):
    await safe_answer(call)
    can_open, hours_left = check_case_cooldown(call.from_user.id)
    if not can_open:
        return await call.answer(f"Осталось {hours_left} ч.", show_alert=True)
    set_case_cooldown(call.from_user.id)
    msg = await call.message.answer("📦 <b>Кейс открывается...</b>", parse_mode="HTML")
    await asyncio.sleep(0.5)
    await msg.edit_text("🎲 <b>Крутим барабан...</b>", parse_mode="HTML")
    await asyncio.sleep(0.5)
    await msg.edit_text("✨ <b>Достаем приз...</b>", parse_mode="HTML")
    await asyncio.sleep(0.5)
    r = random.randint(1, 100)
    if r <= 40:
        res, code = "😢 <b>Пусто!</b>", None
    elif r <= 65:
        res, code = "🎉 <b>Скидка 5%!</b>", "LUCK5"
    elif r <= 85:
        res, code = "🔥 <b>Скидка 10%!</b>", "LUCK10"
    else:
        res, code = "💎 <b>Скидка 20%!</b>", "LUCK20"
    builder = InlineKeyboardBuilder()
    if code:
        res += f"\n\nПромокод: <code>{code}</code>"
        builder.button(text="🎟 Ввести промокод", callback_data="menu:subscribe")
    builder.button(text="⬅️ В МЕНЮ", callback_data="menu:back")
    await msg.edit_text(res, reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("sub_info:"))
async def on_sub_info(call: CallbackQuery):
    await safe_answer(call)
    days = int(call.data.split(":")[1])
    title, price = ("7 дней", 150) if days == 7 else ("30 дней", 300) if days == 30 else ("Навсегда", 500)
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Оплатить ({price} ⭐)", callback_data=f"buy:{days}:{price}")
    builder.button(text="🎟 Ввести промокод", callback_data=f"promo_prompt:{days}")
    builder.button(text="⬅️ Назад", callback_data="menu:subscribe")
    await call.message.answer(f"<b>Подписка на {title}</b>\n\nСтоимость: <b>{price} ⭐</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("promo_prompt:"))
async def on_promo_prompt(call: CallbackQuery):
    await safe_answer(call)
    days = call.data.split(":")[1]
    await call.message.answer(f"🎟 Введите промокод для тарифа {days} дней:")
    @dp.message()
    async def check_promo(message: Message):
        if message.text == "/cancel":
            dp.message.handlers.pop()
            return await message.answer("Отменено.")
        promo = message.text.strip().upper()
        if promo in PROMOCODES:
            discount = PROMOCODES[promo]
            old_price = 150 if days == "7" else 300 if days == "30" else 500
            new_price = int(old_price * (1 - discount / 100))
            builder = InlineKeyboardBuilder()
            builder.button(text=f"💳 Оплатить ({new_price} ⭐)", callback_data=f"buy:{days}:{new_price}")
            builder.button(text="⬅️ Назад", callback_data="menu:back")
            await message.answer(f"✅ <b>Промокод активирован!</b>\n<s>{old_price} ⭐</s> -> <b>{new_price} ⭐</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
            dp.message.handlers.pop()
        else:
            await message.answer("❌ Неверный промокод.")

@dp.callback_query(F.data == "menu:access")
async def on_access(call: CallbackQuery):
    await safe_answer(call)
    await send_access_info(call.message)

@dp.callback_query(F.data == "menu:referral")
async def on_referral(call: CallbackQuery):
    await safe_answer(call)
    total, bought = get_ref_stats(call.from_user.id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{call.from_user.id}"
    text = f"👥 <b>Рефералка</b>\n\nПриглашено: <b>{total}/3</b>\n🔗 <code>{ref_link}</code>"
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ МЕНЮ", callback_data="menu:back")
    await call.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data == "menu:partnership")
async def on_partnership(call: CallbackQuery):
    await safe_answer(call)
    builder = InlineKeyboardBuilder()
    builder.button(text="📩 Доказательства", url="https://t.me/menedger_offers")
    builder.button(text="⬅️ МЕНЮ", callback_data="menu:back")
    await call.message.answer(f"🤝 <b>Партнерка</b>\n\n20 комментов = 3 дня. Пример:\n<code>тут пользуюсь @{BOT_USERNAME}</code>", reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data == "menu:channel")
async def on_channel(call: CallbackQuery):
    await safe_answer(call)
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Канал", url=CHANNEL_LINK)
    await call.message.answer("АКТУАЛЬНЫЕ ПРОМОКОДЫ в канале.", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("buy:"))
async def on_buy(call: CallbackQuery):
    await safe_answer(call)
    parts = call.data.split(":")
    days = int(parts[1])
    price = int(parts[2])
    await bot.send_invoice(chat_id=call.message.chat.id, title="Подписка", description="Доступ", payload=f"sub_{days}_{price}", provider_token="", currency="XTR", prices=[LabeledPrice(label="Подписка", amount=price)], start_parameter="sub")

@dp.pre_checkout_query()
async def on_pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def on_payment(message: Message):
    user_id = message.from_user.id
    parts = message.successful_payment.invoice_payload.split("_")
    days, price = int(parts[1]), int(parts[2])
    add_payment(user_id, price)
    set_access(user_id, days)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET has_bought = 1 WHERE user_id = ?", (user_id,))
    cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    referrer_id = res[0] if res else None
    conn.commit()
    conn.close()
    builder = InlineKeyboardBuilder()
    builder.button(text="🔓 Войти в закрытый канал", url=PRIVATE_CHANNEL_LINK)
    await message.answer("✅ Оплата прошла! Доступ активирован.", reply_markup=builder.as_markup())
    try:
        await bot.send_message(ADMIN_ID, f"💰 Покупка! ID: <code>{user_id}</code> | Дней: {days} | Звезд: {price}", parse_mode="HTML")
    except:
        pass
    if referrer_id:
        total, bought = get_ref_stats(referrer_id)
        if total >= 3 and bought >= 1:
            current_access = check_and_clear_access(referrer_id)
            if not current_access or (current_access != "Навсегда" and current_access != "Истекла"):
                set_access(referrer_id, 0)
                try:
                    await bot.send_message(referrer_id, "🎉 Вам выдан доступ навсегда за рефералов!")
                except:
                    pass

async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="subscribe", description="Купить подписку"),
        BotCommand(command="access", description="Мой доступ"),
        BotCommand(command="referral", description="Реферальная система"),
        BotCommand(command="channel", description="Наш канал (ТГК)"),
    ])
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="admin", description="👑 Выдать себе подписку"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="give", description="🎁 Выдать подписку"),
        BotCommand(command="ban", description="🚫 Забанить"),
        BotCommand(command="unban", description="✅ Разбанить"),
        BotCommand(command="bans", description="📋 Список забаненных"),
    ], scope=BotCommandScopeChat(chat_id=ADMIN_ID))
    await dp.start_polling(bot)

if __name__ == "__main__":
    while True:
        try:
            print("🚀 Бот запущен...")
            asyncio.run(main())
        except Exception as e:
            print(f"💥 Ошибка: {e}")
            time.sleep(5)