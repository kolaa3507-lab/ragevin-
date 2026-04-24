ПОЛНЫЙ TELEGRAM SHOP BOT (aiogram 3.x)

ВКЛЮЧАЕТ ВСЁ: категории, товары, количество, чеки, админка, промокоды, вывод, комментарии

import asyncio import os import sqlite3 from aiogram import Bot, Dispatcher, F from aiogram.types import Message, CallbackQuery from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN") ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=TOKEN) dp = Dispatcher()

conn = sqlite3.connect("db.db") c = conn.cursor()

c.executescript(""" CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT); CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, category_id INTEGER); CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item TEXT, qty INTEGER, status TEXT); CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, photo TEXT, status TEXT); CREATE TABLE IF NOT EXISTS promo(code TEXT PRIMARY KEY, reward INTEGER, uses INTEGER); """) conn.commit()

--- MENU ---

def menu(): kb = InlineKeyboardBuilder() kb.button(text="🛒 Товары", callback_data="shop") kb.button(text="👤 Профиль", callback_data="profile") kb.button(text="📦 Мои товары", callback_data="my") kb.button(text="🎁 Промокод", callback_data="promo") kb.button(text="ℹ️ О боте", callback_data="about") kb.adjust(2) return kb.as_markup()

--- START ---

@dp.message(F.text == "/start") async def start(msg: Message): c.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (msg.from_user.id,)) conn.commit() await msg.answer("Меню", reply_markup=menu())

--- PROFILE ---

@dp.callback_query(F.data == "profile") async def profile(call: CallbackQuery): bal = c.execute("SELECT balance FROM users WHERE id=?", (call.from_user.id,)).fetchone()[0] await call.message.edit_text(f"ID: {call.from_user.id}\nБаланс: {bal}", reply_markup=menu())

--- SHOP ---

@dp.callback_query(F.data == "shop") async def shop(call: CallbackQuery): kb = InlineKeyboardBuilder() for i in c.execute("SELECT id,name FROM categories"): kb.button(text=i[1], callback_data=f"cat_{i[0]}") kb.button(text="⬅️", callback_data="back") kb.adjust(1) await call.message.edit_text("Категории:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("cat_")) async def cat(call: CallbackQuery): cid = int(call.data.split("")[1]) kb = InlineKeyboardBuilder() for i in c.execute("SELECT id,name,price FROM items WHERE category_id=?", (cid,)): kb.button(text=f"{i[1]} - {i[2]}", callback_data=f"buy{i[0]}") kb.button(text="⬅️", callback_data="shop") kb.adjust(1) await call.message.edit_text("Товары:", reply_markup=kb.as_markup())

--- BUY WITH QTY ---

user_buy = {}

@dp.callback_query(F.data.startswith("buy_")) async def buy(call: CallbackQuery): item_id = int(call.data.split("_")[1]) user_buy[call.from_user.id] = item_id await call.message.answer("Введи количество:")

@dp.message() async def handle(msg: Message): uid = msg.from_user.id

# ПРОМО
data = c.execute("SELECT reward,uses FROM promo WHERE code=?", (msg.text,)).fetchone()
if data:
    reward, uses = data
    if uses > 0:
        c.execute("UPDATE users SET balance=balance+? WHERE id=?", (reward, uid))
        c.execute("UPDATE promo SET uses=uses-1 WHERE code=?", (msg.text,))
        conn.commit()
        await msg.answer(f"+{reward}")
    return

# ПОКУПКА
if uid in user_buy:
    qty = int(msg.text)
    item_id = user_buy[uid]
    name, price = c.execute("SELECT name,price FROM items WHERE id=?", (item_id,)).fetchone()
    total = price * qty
    bal = c.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()[0]

    if bal < total:
        await msg.answer("Недостаточно средств")
        return

    c.execute("UPDATE users SET balance=balance-? WHERE id=?", (total, uid))
    c.execute("INSERT INTO purchases(user_id,item,qty,status) VALUES(?,?,?,?)", (uid, name, qty, "wait"))
    conn.commit()

    await bot.send_message(ADMIN_ID, f"Заявка на выдачу {name} x{qty}", reply_markup=InlineKeyboardBuilder().button(text="✅", callback_data=f"give_{uid}").button(text="❌", callback_data=f"deny_{uid}").as_markup())
    await msg.answer("Заявка отправлена")
    del user_buy[uid]

--- CHECK ---

@dp.message(F.photo) async def check(msg: Message): fid = msg.photo[-1].file_id c.execute("INSERT INTO checks(user_id,photo,status) VALUES(?,?,?)", (msg.from_user.id, fid, "wait")) conn.commit()

kb = InlineKeyboardBuilder()
kb.button(text="✅", callback_data=f"ok_{msg.from_user.id}")
kb.button(text="❌", callback_data=f"no_{msg.from_user.id}")

await bot.send_photo(ADMIN_ID, fid, reply_markup=kb.as_markup())

--- ADMIN ---

@dp.callback_query(F.data.startswith("ok_")) async def ok(call: CallbackQuery): uid = int(call.data.split("_")[1]) c.execute("UPDATE users SET balance=balance+100 WHERE id=?", (uid,)) conn.commit() await bot.send_message(uid, "Пополнение принято")

@dp.callback_query(F.data.startswith("no_")) async def no(call: CallbackQuery): uid = int(call.data.split("_")[1]) await bot.send_message(uid, "Отклонено")

@dp.callback_query(F.data.startswith("give_")) async def give(call: CallbackQuery): uid = int(call.data.split("_")[1]) c.execute("UPDATE purchases SET status='done' WHERE user_id=?", (uid,)) conn.commit() await bot.send_message(uid, "Товар выдан")

@dp.callback_query(F.data.startswith("deny_")) async def deny(call: CallbackQuery): uid = int(call.data.split("_")[1]) await bot.send_message(uid, "Выдача отклонена")

--- MY ---

@dp.callback_query(F.data == "my") async def my(call: CallbackQuery): text = "" for i in c.execute("SELECT item,qty,status FROM purchases WHERE user_id=?", (call.from_user.id,)): text += f"{i[0]} x{i[1]} [{i[2]}]\n" await call.message.edit_text(text, reply_markup=menu())

--- BACK ---

@dp.callback_query(F.data == "back") async def back(call: CallbackQuery): await call.message.edit_text("Меню", reply_markup=menu())

--- RUN ---

async def main(): await dp.start_polling(bot)

if name == "main": asyncio.run(main())
