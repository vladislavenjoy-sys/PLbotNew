import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiosqlite
from datetime import datetime
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- DB ----------
async def init_db():
    async with aiosqlite.connect("data.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS demos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            sticks TEXT,
            buy INTEGER,
            rent INTEGER,
            reg INTEGER,
            comment TEXT,
            time TEXT
        )
        """)
        await db.commit()

# ---------- TEMP STORAGE ----------
user_data = {}

def add_stick(user_id, stick):
    if user_id not in user_data:
        user_data[user_id] = {"sticks": []}
    user_data[user_id]["sticks"].append(stick)

# ---------- START ----------
@dp.message(CommandStart())
async def start(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Нова демонстрація", callback_data="new_demo")
    kb.adjust(1)

    await message.answer("Привіт 👋\nНатисни кнопку:", reply_markup=kb.as_markup())

# ---------- NEW DEMO ----------
@dp.callback_query(F.data == "new_demo")
async def new_demo(call: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🩶 EVO Silver", callback_data="stick_silver")
    kb.button(text="🩷 EVO Pink Option", callback_data="stick_pink")
    kb.button(text="🧡 EVO Orange", callback_data="stick_orange")
    kb.button(text="✅ Завершити", callback_data="finish_sticks")
    kb.adjust(1)

    await call.message.answer("Які стіки використали?", reply_markup=kb.as_markup())

# ---------- STICKS ----------
@dp.callback_query(F.data.startswith("stick_"))
async def stick(call: CallbackQuery):
    uid = call.from_user.id

    if call.data == "stick_silver":
        add_stick(uid, "EVO Silver")
    elif call.data == "stick_pink":
        add_stick(uid, "EVO Pink Option")
    elif call.data == "stick_orange":
        add_stick(uid, "EVO Orange")

    await call.answer("Додано ✔️")

# ---------- FINISH ----------
@dp.callback_query(F.data == "finish_sticks")
async def finish(call: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="buy_yes")
    kb.button(text="Ні", callback_data="buy_no")
    kb.adjust(2)

    await call.message.answer("Чи була покупка пристрою?", reply_markup=kb.as_markup())

# ---------- BUY ----------
@dp.callback_query(F.data.startswith("buy_"))
async def buy(call: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="rent_yes")
    kb.button(text="Ні", callback_data="rent_no")
    kb.adjust(2)

    await call.message.answer("Чи був прокат?", reply_markup=kb.as_markup())

# ---------- RENT ----------
@dp.callback_query(F.data.startswith("rent_"))
async def rent(call: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="reg_yes")
    kb.button(text="Ні", callback_data="reg_no")
    kb.adjust(2)

    await call.message.answer("Чи була реєстрація?", reply_markup=kb.as_markup())

# ---------- REG ----------
@dp.callback_query(F.data.startswith("reg_"))
async def reg(call: CallbackQuery):
    await call.message.answer("Напиши коментар клієнта (або '-')")

# ---------- COMMENT + SAVE ----------
@dp.message()
async def save(message: Message):
    uid = message.from_user.id

    if uid not in user_data:
        return

    data = user_data.get(uid, {})
    sticks = ", ".join(data.get("sticks", []))

    buy = data.get("buy", 0)
    rent = data.get("rent", 0)
    reg = data.get("reg", 0)

    comment = message.text
    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    async with aiosqlite.connect("data.db") as db:
        await db.execute("""
        INSERT INTO demos (user_id, username, sticks, buy, rent, reg, comment, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            message.from_user.username,
            sticks,
            buy,
            rent,
            reg,
            comment,
            time
        ))
        await db.commit()

    user_data.pop(uid, None)

    await message.answer("✅ Збережено!")
    

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())