import asyncio
import aiosqlite
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

# ---------------- TOKEN ----------------
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------------- STATE ----------------
user_state = {}
temp = {}

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
    uid = message.from_user.id
    user_state[uid] = "awaiting_name"

    await message.answer("👋 Введіть ваше прізвище та ім’я:")

# ---------------- MAIN TEXT HANDLER ----------------
@dp.message()
async def handle_text(message: Message):

    uid = message.from_user.id
    text = message.text

    # ---------------- REGISTRATION ----------------
    if user_state.get(uid) == "awaiting_name":

        async with aiosqlite.connect("data.db") as db:
            await db.execute("""
                INSERT OR REPLACE INTO users (user_id, name)
                VALUES (?, ?)
            """, (uid, text))
            await db.commit()

        user_state[uid] = "ready"

        await message.answer("✅ Зареєстровано!", reply_markup=main_menu())
        return

    # ---------------- NEW DEMO ----------------
    if text == "➕ Нова демонстрація":

        temp[uid] = {"sticks": [], "buy": 0, "rent": 0, "reg": 0}

        kb = InlineKeyboardBuilder()
        kb.button(text="🩶 EVO Silver", callback_data="s_silver")
        kb.button(text="🩷 EVO Pink Option", callback_data="s_pink")
        kb.button(text="🧡 EVO Orange", callback_data="s_orange")
        kb.button(text="✅ Завершити", callback_data="done_sticks")
        kb.adjust(1)

        await message.answer("Які стіки використано?", reply_markup=kb.as_markup())
        return

    # ---------------- STATS ----------------
    if text == "📊 Моя статистика (7 днів)":
        await weekly_stats(message)
        return

# ---------------- STICKS ----------------
@dp.callback_query(F.data.startswith("s_"))
async def sticks(call: CallbackQuery):

    uid = call.from_user.id

    if uid not in temp:
        temp[uid] = {"sticks": [], "buy": 0, "rent": 0, "reg": 0}

    if call.data == "s_silver":
        temp[uid]["sticks"].append("EVO Silver")
    elif call.data == "s_pink":
        temp[uid]["sticks"].append("EVO Pink Option")
    elif call.data == "s_orange":
        temp[uid]["sticks"].append("EVO Orange")

    await call.answer("Додано ✔️")

# ---------------- FINISH STICKS ----------------
@dp.callback_query(F.data == "done_sticks")
async def done(call: CallbackQuery):

    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="buy_yes")
    kb.button(text="Ні", callback_data="buy_no")
    kb.adjust(2)

    await call.message.answer("Чи була покупка пристрою?", reply_markup=kb.as_markup())

# ---------------- BUY ----------------
@dp.callback_query(F.data.startswith("buy_"))
async def buy(call: CallbackQuery):

    uid = call.from_user.id
    if uid in temp:
        temp[uid]["buy"] = 1 if call.data == "buy_yes" else 0

    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="rent_yes")
    kb.button(text="Ні", callback_data="rent_no")
    kb.adjust(2)

    await call.message.answer("Чи був прокат?", reply_markup=kb.as_markup())

# ---------------- RENT ----------------
@dp.callback_query(F.data.startswith("rent_"))
async def rent(call: CallbackQuery):

    uid = call.from_user.id
    if uid in temp:
        temp[uid]["rent"] = 1 if call.data == "rent_yes" else 0

    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="reg_yes")
    kb.button(text="Ні", callback_data="reg_no")
    kb.adjust(2)

    await call.message.answer("Чи була реєстрація?", reply_markup=kb.as_markup())

# ---------------- REG ----------------
@dp.callback_query(F.data.startswith("reg_"))
async def reg(call: CallbackQuery):

    uid = call.from_user.id
    if uid in temp:
        temp[uid]["reg"] = 1 if call.data == "reg_yes" else 0

    await call.message.answer("Напиши коментар (або '-')")

# ---------------- SAVE DEMO ----------------
@dp.message()
async def save_demo(message: Message):

    uid = message.from_user.id

    if uid not in temp:
        return

    data = temp[uid]

    sticks = ", ".join(data.get("sticks", []))

    async with aiosqlite.connect("data.db") as db:
        await db.execute("""
        INSERT INTO demos (user_id, sticks, buy, rent, reg, comment, time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            sticks,
            data.get("buy", 0),
            data.get("rent", 0),
            data.get("reg", 0),
            message.text,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        await db.commit()

    temp.pop(uid, None)

    await message.answer("✅ Демонстрацію збережено!", reply_markup=main_menu())

# ---------------- WEEK STATS ----------------
async def weekly_stats(message: Message):

    uid = message.from_user.id
    week_ago = datetime.now() - timedelta(days=7)

    async with aiosqlite.connect("data.db") as db:
        rows = await db.execute_fetchall("""
        SELECT sticks, time FROM demos WHERE user_id = ?
        """, (uid,))

    total = 0
    silver = pink = orange = 0

    for r in rows:
        try:
            t = datetime.strptime(r[1], "%Y-%m-%d %H:%M")
            if t >= week_ago:
                total += 1
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

📌 Демонстрації: {total}

🩶 EVO Silver: {silver}
🩷 EVO Pink Option: {pink}
🧡 EVO Orange: {orange}
"""
    )

# ---------------- RUN ----------------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())