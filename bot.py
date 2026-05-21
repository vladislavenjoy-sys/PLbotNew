import asyncio
import aiosqlite
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------------- DB ----------------
async def init_db():
    async with aiosqlite.connect("data.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS demos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sticks TEXT,
            buy INTEGER,
            rent INTEGER,
            reg INTEGER,
            comment TEXT,
            time TEXT
        )
        """)
        await db.commit()

# ---------------- MENU ----------------
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Нова демонстрація")],
            [KeyboardButton(text="📊 Моя статистика (7 днів)")]
        ],
        resize_keyboard=True
    )

# ---------------- START ----------------
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 Введіть ваше прізвище та ім’я:",
        reply_markup=main_menu()
    )

# ---------------- SAVE NAME ----------------
@dp.message()
async def handle_text(message: Message):
    uid = message.from_user.id
    text = message.text

    async with aiosqlite.connect("data.db") as db:
        user = await db.execute_fetchone(
            "SELECT name FROM users WHERE user_id = ?", (uid,)
        )

        # якщо користувача ще нема — зберігаємо ім'я
        if user is None:
            await db.execute(
                "INSERT INTO users (user_id, name) VALUES (?, ?)",
                (uid, text)
            )
            await db.commit()
            await message.answer("✅ Дякую! Дані збережено.", reply_markup=main_menu())
            return

    # якщо натиснув "нова демонстрація"
    if text == "➕ Нова демонстрація":
        kb = InlineKeyboardBuilder()
        kb.button(text="🩶 EVO Silver", callback_data="s_silver")
        kb.button(text="🩷 EVO Pink", callback_data="s_pink")
        kb.button(text="🧡 EVO Orange", callback_data="s_orange")
        kb.button(text="✅ Завершити", callback_data="done_sticks")
        kb.adjust(1)

        await message.answer("Які стіки використано?", reply_markup=kb.as_markup())

    elif text == "📊 Моя статистика (7 днів)":
        await weekly_stats(message)

# ---------------- TEMP DATA ----------------
temp = {}

def add_stick(uid, stick):
    if uid not in temp:
        temp[uid] = {"sticks": []}
    temp[uid]["sticks"].append(stick)

# ---------------- STICKS ----------------
@dp.callback_query(F.data.startswith("s_"))
async def sticks(call: CallbackQuery):
    uid = call.from_user.id

    if call.data == "s_silver":
        add_stick(uid, "EVO Silver")
    elif call.data == "s_pink":
        add_stick(uid, "EVO Pink Option")
    elif call.data == "s_orange":
        add_stick(uid, "EVO Orange")

    await call.answer("Додано ✔️")

# ---------------- FINISH ----------------
@dp.callback_query(F.data == "done_sticks")
async def done(call: CallbackQuery):
    uid = call.from_user.id
    temp.setdefault(uid, {})

    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="buy_yes")
    kb.button(text="Ні", callback_data="buy_no")
    kb.adjust(2)

    await call.message.answer("Чи була покупка?", reply_markup=kb.as_markup())

# ---------------- BUY / RENT / REG ----------------
@dp.callback_query(F.data.startswith("buy_"))
async def buy(call: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="rent_yes")
    kb.button(text="Ні", callback_data="rent_no")
    kb.adjust(2)

    await call.message.answer("Чи був прокат?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("rent_"))
async def rent(call: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="reg_yes")
    kb.button(text="Ні", callback_data="reg_no")
    kb.adjust(2)

    await call.message.answer("Чи була реєстрація?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("reg_"))
async def reg(call: CallbackQuery):
    await call.message.answer("Напиши коментар:")

# ---------------- SAVE ----------------
@dp.message()
async def save_demo(message: Message):
    uid = message.from_user.id

    if uid not in temp:
        return

    sticks = ", ".join(temp[uid].get("sticks", []))

    async with aiosqlite.connect("data.db") as db:
        await db.execute("""
        INSERT INTO demos (user_id, sticks, buy, rent, reg, comment, time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            sticks,
            0, 0, 0,
            message.text,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        await db.commit()

    temp.pop(uid, None)
    await message.answer("✅ Збережено!", reply_markup=main_menu())

# ---------------- WEEK STATS ----------------
async def weekly_stats(message: Message):
    uid = message.from_user.id
    week_ago = datetime.now() - timedelta(days=7)

    async with aiosqlite.connect("data.db") as db:
        rows = await db.execute_fetchall("""
        SELECT sticks, time FROM demos WHERE user_id = ?
        """, (uid,))

    count = 0
    silver = pink = orange = 0

    for r in rows:
        try:
            t = datetime.strptime(r[1], "%Y-%m-%d %H:%M")
            if t >= week_ago:
                count += 1
                sticks = r[0] or ""

                if "Silver" in sticks:
                    silver += 1
                if "Pink" in sticks:
                    pink += 1
                if "Orange" in sticks:
                    orange += 1
        except:
            pass

    await message.answer(
        f"""📊 Статистика за 7 днів:

👤 Ти: {count} демонстрацій

🩶 EVO Silver: {silver}
🩷 EVO Pink: {pink}
🧡 EVO Orange: {orange}
"""
    )

# ---------------- RUN ----------------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())