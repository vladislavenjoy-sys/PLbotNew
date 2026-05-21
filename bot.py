import asyncio
import aiosqlite
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os
from collections import defaultdict

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
            sale INTEGER,
            rent INTEGER,
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
    user_state[message.from_user.id] = "awaiting_name"
    await message.answer("👋 Введіть ваше прізвище та ім’я:")

# ================= STICKS =================
@dp.callback_query(F.data.startswith("s_"))
async def sticks(call: CallbackQuery):

    uid = call.from_user.id
    temp.setdefault(uid, {
        "sticks": [],
        "sale": 0,
        "rent": 0,
        "site_reg": 0,
        "device_reg": 0
    })

    if call.data == "s_silver":
        temp[uid]["sticks"].append("EVO Silver")
    elif call.data == "s_pink":
        temp[uid]["sticks"].append("EVO Pink Option")
    elif call.data == "s_orange":
        temp[uid]["sticks"].append("EVO Orange")

    await call.answer("Додано ✔️")

# ================= FLOW =================
@dp.callback_query(F.data == "done_sticks")
async def done(call: CallbackQuery):

    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="sale_yes")
    kb.button(text="Ні", callback_data="sale_no")
    kb.adjust(2)

    await call.message.answer("Чи була продаж пристрою?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("sale_"))
async def sale(call: CallbackQuery):

    uid = call.from_user.id
    if uid in temp:
        temp[uid]["sale"] = 1 if call.data == "sale_yes" else 0

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
    kb.button(text="Так", callback_data="site_yes")
    kb.button(text="Ні", callback_data="site_no")
    kb.adjust(2)

    await call.message.answer("Чи була реєстрація на сайті?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("site_"))
async def site(call: CallbackQuery):

    uid = call.from_user.id
    if uid in temp:
        temp[uid]["site_reg"] = 1 if call.data == "site_yes" else 0

    kb = InlineKeyboardBuilder()
    kb.button(text="Так", callback_data="device_yes")
    kb.button(text="Ні", callback_data="device_no")
    kb.adjust(2)

    await call.message.answer("Чи була реєстрація пристрою?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("device_"))
async def device(call: CallbackQuery):

    uid = call.from_user.id
    if uid in temp:
        temp[uid]["device_reg"] = 1 if call.data == "device_yes" else 0

    user_state[uid] = "awaiting_comment"
    await call.message.answer("Напиши коментар (або '-')")

# ================= SAVE =================
@dp.message()
async def handle_all(message: Message):

    uid = message.from_user.id
    text = message.text

    # NAME
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

    # NEW DEMO
    if text == "➕ Нова демонстрація":

        temp[uid] = {
            "sticks": [],
            "sale": 0,
            "rent": 0,
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

    # SAVE
    if user_state.get(uid) == "awaiting_comment" and uid in temp:

        data = temp[uid]
        sticks = ", ".join(data["sticks"])

        async with aiosqlite.connect("data.db") as db:
            await db.execute("""
            INSERT INTO demos (
                user_id, sticks,
                sale, rent,
                site_reg, device_reg,
                comment, time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                uid,
                sticks,
                data["sale"],
                data["rent"],
                data["site_reg"],
                data["device_reg"],
                text,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
            await db.commit()

        temp.pop(uid, None)
        user_state[uid] = "ready"

        await message.answer("✅ Збережено!", reply_markup=main_menu())
        return

    # ================= PERSONAL KPI =================
    if text == "📊 Моя статистика (7 днів)":

        async with aiosqlite.connect("data.db") as db:
            rows = await db.execute_fetchall("""
            SELECT sale, rent, site_reg, device_reg
            FROM demos
            WHERE user_id = ?
            """, (uid,))

        total = sale = rent = site = device = 0

        for r in rows:
            total += 1
            sale += r[0]
            rent += r[1]
            site += r[2]
            device += r[3]

        conv = round((sale / total * 100), 1) if total > 0 else 0

        await message.answer(f"""
📊 Моя KPI статистика:

📌 Демо: {total}

💰 Продажі: {sale}
📦 Прокати: {rent}
🌐 Сайт: {site}
📱 Пристрій: {device}

📈 Конверсія: {conv}%
""")
        return

    # ================= TEAM + KPI + USERS =================
    if text == "👥 Командна статистика":

        if uid != ADMIN_ID:
            await message.answer("⛔ Немає доступу")
            return

        async with aiosqlite.connect("data.db") as db:

            demos = await db.execute_fetchall("""
            SELECT user_id, sale, rent, site_reg, device_reg
            FROM demos
            """)

            users = await db.execute_fetchall("""
            SELECT user_id, name FROM users
            """)

        names = {u[0]: u[1] for u in users}

        stats = defaultdict(lambda: {
            "demo": 0,
            "sale": 0,
            "rent": 0,
            "site": 0,
            "device": 0
        })

        for r in demos:
            uid2 = r[0]
            stats[uid2]["demo"] += 1
            stats[uid2]["sale"] += r[1]
            stats[uid2]["rent"] += r[2]
            stats[uid2]["site"] += r[3]
            stats[uid2]["device"] += r[4]

        total_demo = len(demos)

        out = f"""
👥 КОМАНДА KPI

📊 Загалом демо: {total_demo}

━━━━━━━━━━━━━━
👤 Експерти:
"""

        ranking = []

        for user_id, s in stats.items():

            conv = (s["sale"] / s["demo"] * 100) if s["demo"] > 0 else 0
            ranking.append((conv, user_id, s))

        ranking.sort(reverse=True)

        for i, (conv, user_id, s) in enumerate(ranking, 1):

            out += f"""
{i}. {names.get(user_id, "Невідомий")}
📊 Демо: {s['demo']}
💰 Продажі: {s['sale']}
📦 Прокати: {s['rent']}
🌐 Сайт: {s['site']}
📱 Пристрій: {s['device']}
📈 KPI: {round(conv,1)}%
"""

        await message.answer(out)
        return

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())