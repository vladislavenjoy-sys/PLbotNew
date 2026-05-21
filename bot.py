import asyncio
import aiosqlite
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

# ================= TOKEN =================
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= ADMIN =================
ADMIN_ID = 1066065772

# ================= STATE =================
user_state = {}
temp = {}

# ================= DB =================
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
            site_reg INTEGER,
            device_reg INTEGER,
            comment TEXT,
            time TEXT
        )
        """)

        await db.commit()

# ================= MENU =================
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Нова демонстрація")],
            [KeyboardButton(text="📊 Моя статистика (7 днів)")],
            [KeyboardButton(text="👥 Командна статистика")],
            [KeyboardButton(text="🏆 ТОП експерти")]
        ],
        resize_keyboard=True
    )

# ================= START =================
@dp.message(CommandStart())
async def start(message: Message):
    uid = message.from_user.id
    user_state[uid] = "awaiting_name"

    await message.answer("👋 Введіть ваше прізвище та ім’я:")

# ================= CALLBACK STICKS =================
@dp.callback_query(F.data.startswith("s_"))
async def sticks(call: CallbackQuery):

    uid = call.from_user.id
    temp.setdefault(uid, {"sticks": [], "buy": 0, "rent": 0, "reg": 0, "site_reg": 0, "device_reg": 0})

    if call.data == "s_silver":
        temp[uid]["sticks"].append("EVO Silver")
    elif call.data == "s_pink":
        temp[uid]["sticks"].append("EVO Pink Option")
    elif call.data == "s_orange":
        temp[uid]["sticks"].append("EVO Orange")

    await call.answer("Додано ✔️")

@dp.callback_query(F.data == "done_sticks")
async def done(call: CallbackQuery):

    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="buy_yes")
    kb.button(text="Ні", callback_data="buy_no")
    kb.adjust(2)

    await call.message.answer("Чи була покупка пристрою?", reply_markup=kb.as_markup())

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

@dp.callback_query(F.data.startswith("rent_"))
async def rent(call: CallbackQuery):

    uid = call.from_user.id
    if uid in temp:
        temp[uid]["rent"] = 1 if call.data == "rent_yes" else 0

    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="reg_yes")
    kb.button(text="Ні", callback_data="reg_no")
    kb.adjust(2)

    await call.message.answer("Чи була реєстрація на сайті?")

@dp.callback_query(F.data.startswith("reg_"))
async def reg(call: CallbackQuery):

    uid = call.from_user.id
    if uid in temp:
        temp[uid]["site_reg"] = 1 if call.data == "reg_yes" else 0

    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="device_yes")
    kb.button(text="Ні", callback_data="device_no")
    kb.adjust(2)

    await call.message.answer("Чи була реєстрація пристрою?")

@dp.callback_query(F.data.startswith("device_"))
async def device(call: CallbackQuery):

    uid = call.from_user.id
    if uid in temp:
        temp[uid]["device_reg"] = 1 if call.data == "device_yes" else 0

    user_state[uid] = "awaiting_comment"

    await call.message.answer("Напиши коментар (або '-')")

# ================= MAIN HANDLER =================
@dp.message()
async def handle_all(message: Message):

    uid = message.from_user.id
    text = message.text

    # -------- NAME --------
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

    # -------- NEW DEMO --------
    if text == "➕ Нова демонстрація":

        temp[uid] = {
            "sticks": [],
            "buy": 0,
            "rent": 0,
            "reg": 0,
            "site_reg": 0,
            "device_reg": 0
        }

        kb = InlineKeyboardBuilder()
        kb.button(text="🩶 EVO Silver", callback_data="s_silver")
        kb.button(text="🩷 EVO Pink Option", callback_data="s_pink")
        kb.button(text="🧡 EVO Orange", callback_data="s_orange")
        kb.button(text="✅ Завершити", callback_data="done_sticks")
        kb.adjust(1)

        await message.answer("Які стіки використано?", reply_markup=kb.as_markup())
        return

    # -------- STATS --------
    if text == "📊 Моя статистика (7 днів)":
        await weekly_stats(message)
        return

    # -------- COMMENT SAVE --------
    if user_state.get(uid) == "awaiting_comment" and uid in temp:

        data = temp[uid]
        sticks = ", ".join(data.get("sticks", []))

        async with aiosqlite.connect("data.db") as db:
            await db.execute("""
            INSERT INTO demos (
                user_id, sticks,
                buy, rent, reg,
                site_reg, device_reg,
                comment, time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                uid,
                sticks,
                data.get("buy", 0),
                data.get("rent", 0),
                data.get("reg", 0),
                data.get("site_reg", 0),
                data.get("device_reg", 0),
                text,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
            await db.commit()

        temp.pop(uid, None)
        user_state[uid] = "ready"

        await message.answer("✅ Демонстрацію збережено!", reply_markup=main_menu())
        return

    # -------- TEAM STATS (ADMIN ONLY) --------
    if text == "👥 Командна статистика":

        if uid != ADMIN_ID:
            await message.answer("⛔ Немає доступу")
            return

        async with aiosqlite.connect("data.db") as db:
            rows = await db.execute_fetchall("SELECT * FROM demos")

        buy = rent = reg = site = device = 0

        for r in rows:
            buy += r[3]
            rent += r[4]
            reg += r[5]
            site += r[6]
            device += r[7]

        await message.answer(f"""
👥 Командна статистика:

📊 Демо: {len(rows)}

💰 Покупки: {buy}
📦 Прокати: {rent}
📲 Реєстрації: {reg}
🌐 Сайт реєстрація: {site}
📱 Реєстрація пристрою: {device}
""")
        return

    # -------- TOP EXPERTS (ADMIN ONLY) --------
    if text == "🏆 ТОП експерти":

        if uid != ADMIN_ID:
            await message.answer("⛔ Немає доступу")
            return

        async with aiosqlite.connect("data.db") as db:
            rows = await db.execute_fetchall("""
            SELECT user_id, COUNT(*) as cnt
            FROM demos
            GROUP BY user_id
            ORDER BY cnt DESC
            LIMIT 10
            """)

            users = await db.execute_fetchall("SELECT user_id, name FROM users")

        names = {u[0]: u[1] for u in users}

        out = "🏆 ТОП експерти:\n\n"

        for i, r in enumerate(rows, 1):
            out += f"{i}. {names.get(r[0], 'Невідомий')} — {r[1]} демо\n"

        await message.answer(out)
        return

# ================= WEEK STATS =================
async def weekly_stats(message: Message):

    uid = message.from_user.id
    week = datetime.now() - timedelta(days=7)

    async with aiosqlite.connect("data.db") as db:
        rows = await db.execute_fetchall("""
        SELECT sticks, time FROM demos WHERE user_id = ?
        """, (uid,))

    total = silver = pink = orange = 0

    for r in rows:
        try:
            t = datetime.strptime(r[1], "%Y-%m-%d %H:%M")
            if t >= week:
                total += 1
                s = r[0] or ""

                if "Silver" in s:
                    silver += 1
                if "Pink" in s:
                    pink += 1
                if "Orange" in s:
                    orange += 1
        except:
            pass

    await message.answer(f"""
📊 Статистика (7 днів):

📌 Демо: {total}

🩶 Silver: {silver}
🩷 Pink: {pink}
🧡 Orange: {orange}
""")

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())