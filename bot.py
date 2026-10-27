import sqlite3
import asyncio
import threading
import os
import io
import qrcode
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ================= CONFIGURATION =================
BOT_TOKEN = "8785209559:AAF3_nqhd0FabrSGiHr0TQP40qX4SfwHlPw"
ADMIN_ID = 7961207555 
UPI_ID = "aadityasharma3315@fam" # Yahan apna UPI ID daalein
# =================================================

# --- FLASK APP SETUP ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- BOT SETUP ---
conn = sqlite3.connect("super_store.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS countries (id INTEGER PRIMARY KEY AUTOINCREMENT, cat_id INTEGER, name TEXT, emoji TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, country_id INTEGER, price REAL, details TEXT, is_sold INTEGER DEFAULT 0)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, details TEXT, price REAL)""")
conn.commit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class SearchState(StatesGroup):
    waiting_for_country = State()
    
class DepositState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_screenshot = State()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

# --- MAIN MENU ---
def get_main_menu():
    kb = [
        [InlineKeyboardButton(text="🛒 Purchase Accounts", callback_data="menu_purchase")],
        [InlineKeyboardButton(text="💳 Deposit", callback_data="menu_deposit"), 
         InlineKeyboardButton(text="💰 Wallet", callback_data="menu_wallet")],
        [InlineKeyboardButton(text="📦 My Orders", callback_data="menu_orders")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- START COMMAND ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0))
    conn.commit()
    
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    text = f"👑 **Welcome to TG Accounts Store**\n\n🏦 **Your Balance:** ₹{bal:.2f} ($0.00)\n\n👇 Click Purchase Accounts below to browse & buy stock."
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="Markdown")

# --- MENU HANDLERS ---
@dp.callback_query(F.data.startswith("menu_"))
async def menu_handler(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    action = call.data.split("_")[1]
    
    if action == "purchase":
        await show_categories(call)
    elif action == "wallet":
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
        bal = cursor.fetchone()[0]
        await call.message.edit_text(f"💰 **Your Wallet**\n\nCurrent Balance: ₹{bal:.2f}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_menu")]]), parse_mode="Markdown")
    elif action == "deposit":
        await call.message.edit_text("💳 **Deposit Amount**\n\nKitne rupaye add karne hain? Sirf number likhein (jaise: 100):")
        await state.set_state(DepositState.waiting_for_amount)
    elif action == "orders":
        cursor.execute("SELECT details, price FROM orders WHERE user_id=?", (call.from_user.id,))
        orders = cursor.fetchall()
        if not orders:
            text = "📦 **My Orders**\n\nAapne abhi tak kuch nahi khareeda."
        else:
            text = "📦 **My Orders**\n\n" + "\n".join([f"🔹 `{o[0]}` - ₹{o[1]}" for o in orders])
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_menu")]]), parse_mode="Markdown")

@dp.callback_query(F.data == "back_menu")
async def back_menu(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    bal = cursor.fetchone()[0]
    text = f"👑 **Welcome to TG Accounts Store**\n\n🏦 **Your Balance:** ₹{bal:.2f} ($0.00)\n\n👇 Click Purchase Accounts below to browse & buy stock."
    await call.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="Markdown")

# --- DEPOSIT LOGIC WITH QR CODE ---
@dp.message(DepositState.waiting_for_amount)
async def process_deposit_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Kripya sirf number likhein (jaise: 100):")
        return
    
    amount = float(message.text)
    await state.update_data(deposit_amount=amount)
    
    # QR Code Generate karna
    upi_link = f"upi://pay?pa={UPI_ID}&pn=Store&am={amount}&cu=INR"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(upi_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # QR ko image file mein convert karna
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    photo = BufferedInputFile(buf.read(), filename="qr.png")
    
    text = f"💳 **Payment Details**\n\nAmount: ₹{amount}\nUPI ID: `{UPI_ID}`\n\n**Step 1:** Niche diye gaye QR code ko scan karein ya UPI ID par payment karein.\n\n**Step 2:** Payment karne ke baad, yahan apna **Payment ka Screenshot** bhejein."
    
    await message.answer_photo(photo=photo, caption=text, parse_mode="Markdown")
    await state.set_state(DepositState.waiting_for_screenshot)

@dp.message(DepositState.waiting_for_screenshot, F.photo)
async def process_deposit_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get('deposit_amount')
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    
    await message.answer("⏳ **Aapka screenshot Admin ko bhej diya gaya hai.** Verify hone ke baad balance add ho jayega.")
    await state.clear()
    
    # Admin ko screenshot bhejna
    admin_text = f"🔔 **Naya Deposit Request!**\n\nUser: @{username}\nUser ID: `{user_id}`\nAmount: ₹{amount}\n\nKya aapne payment receive ki hai?"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}_{amount}")],
        [InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}_{amount}")]
    ])
    
    # User ka screenshot admin ko forward karna
    await bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(DepositState.waiting_for_screenshot)
async def invalid_screenshot(message: types.Message):
    await message.answer("❌ Kripya sirf **Screenshot (Photo)** bhejein.")

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(call: types.CallbackQuery):
    _, user_id, amount = call.data.split("_")
    user_id = int(user_id)
    amount = float(amount)
    
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    
    await call.message.edit_caption(caption=f"{call.message.caption}\n\n✅ **APPROVED!** Balance added.", parse_mode="Markdown")
    await bot.send_message(user_id, f"🎉 **Payment Approved!**\nAapke wallet mein ₹{amount} add ho gaye hain.")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(call: types.CallbackQuery):
    _, user_id, amount = call.data.split("_")
    user_id = int(user_id)
    
    await call.message.edit_caption(caption=f"{call.message.caption}\n\n❌ **REJECTED!**", parse_mode="Markdown")
    await bot.send_message(user_id, f"❌ **Payment Rejected!**\nKripya Admin se contact karein.")

# --- BROADCAST FEATURE ---
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📢 **Broadcast Message**\n\nJo message aap sabko bhejna chahte hain, wo type karke bhejein (Photo, Video ya Text):")
    await state.set_state(BroadcastState.waiting_for_message)

@dp.message(BroadcastState.waiting_for_message)
async def send_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    
    success = 0
    for u in users:
        try:
            await message.copy_to(chat_id=u[0])
            success += 1
            await asyncio.sleep(0.1) # Telegram spam block se bachne ke liye
        except:
            pass
            
    await message.answer(f"✅ Broadcast sent to {success} users successfully!")
    await state.clear()

# --- PURCHASE FLOW & OTHER FEATURES (Puraane code jaisa hi hai) ---
async def show_categories(call: types.CallbackQuery):
    cursor.execute("SELECT id, name FROM categories")
    cats = cursor.fetchall()
    if not cats:
        await call.message.edit_text("⚠️ Admin ne abhi category nahi banayi hai!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_menu")]]))
        return
    kb = [[InlineKeyboardButton(text=f"🔖 {c[1]}", callback_data=f"cat_{c[0]}")] for c in cats]
    kb.append([InlineKeyboardButton(text="🔍 Search Country", callback_data="search_country")])
    kb.append([InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_menu")])
    await call.message.edit_text("📌 **Selected Category: Cheapest**\n\n👇 Select a category to browse stock or search:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("cat_"))
async def show_countries(call: types.CallbackQuery):
    await call.answer()
    cat_id = call.data.split("_")[1]
    cursor.execute("SELECT id, name, emoji FROM countries WHERE cat_id=?", (cat_id,))
    countries = cursor.fetchall()
    kb = []
    row = []
    for c in countries:
        row.append(InlineKeyboardButton(text=f"{c[2]} {c[1]}", callback_data=f"cntry_{c[0]}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row: kb.append(row)
    kb.append([InlineKeyboardButton(text="🌍 Global", callback_data="cntry_global")])
    kb.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_menu")])
    await call.message.edit_text("👇 **Select a region to browse stock:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data == "search_country")
async def ask_search(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("🔍 **Country ka naam type karein:**")
    await state.set_state(SearchState.waiting_for_country)

@dp.message(SearchState.waiting_for_country)
async def process_search(message: types.Message, state: FSMContext):
    search_term = message.text.strip().lower()
    cursor.execute("SELECT id, name, emoji FROM countries WHERE LOWER(name) LIKE ?", (f"%{search_term}%",))
    results = cursor.fetchall()
    if not results:
        await message.answer("❌ Koi country nahi mili.")
        await state.clear()
        return
    kb = [[InlineKeyboardButton(text=f"{c[2]} {c[1]}", callback_data=f"cntry_{c[0]}")] for c in results]
    kb.append([InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_menu")])
    await message.answer(f"🔍 **Search Results:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("cntry_"))
async def show_stock_page(call: types.CallbackQuery):
    await call.answer()
    data = call.data.split("_")
    country_id = data[1]
    page = int(data[2]) if len(data) > 2 else 1
    limit = 5
    offset = (page - 1) * limit
    if country_id == "global":
        cursor.execute("SELECT id, price FROM accounts WHERE is_sold=0 LIMIT ? OFFSET ?", (limit, offset))
        total_q = "SELECT COUNT(*) FROM accounts WHERE is_sold=0"
        count_args = ()
    else:
        cursor.execute("SELECT id, price FROM accounts WHERE country_id=? AND is_sold=0 LIMIT ? OFFSET ?", (country_id, limit, offset))
        total_q = "SELECT COUNT(*) FROM accounts WHERE country_id=? AND is_sold=0"
        count_args = (country_id,)
    accs = cursor.fetchall()
    cursor.execute(total_q, count_args)
    total_accs = cursor.fetchone()[0]
    if not accs:
        await call.message.edit_text("❌ Is category mein stock khatam hai!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_menu")]]))
        return
    text = f"🇮🇳 **Available Accounts** - Page {page}\n\n⚡ Instant Delivery | 🛡️ Spam-Free\n👇 **Select an account to purchase:**"
    kb = []
    for a in accs:
        kb.append([InlineKeyboardButton(text=f"💳 - ₹{a[1]:.2f} ($0.00)", callback_data=f"buy_{a[0]}")])
    nav_row = []
    if page > 1: nav_row.append(InlineKeyboardButton(text="⬅️ Back", callback_data=f"cntry_{country_id}_{page-1}"))
    if total_accs > page * limit: nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"cntry_{country_id}_{page+1}"))
    if nav_row: kb.append(nav_row)
    kb.append([InlineKeyboardButton(text="🔄 Refresh", callback_data=f"cntry_{country_id}_{page}"), InlineKeyboardButton(text="🔙 Menu", callback_data="back_menu")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(call: types.CallbackQuery):
    await call.answer()
    acc_id = call.data.split("_")[1]
    user_id = call.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    user_bal = cursor.fetchone()[0]
    cursor.execute("SELECT price, details FROM accounts WHERE id=? AND is_sold=0", (acc_id,))
    acc = cursor.fetchone()
    if not acc:
        await call.answer("❌ Sold out!", show_alert=True)
        return
    price, details = acc
    if user_bal < price:
        await call.answer(f"❌ Balance kam hai! Aapke paas ₹{user_bal} hain.", show_alert=True)
        return
    new_bal = user_bal - price
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, user_id))
    cursor.execute("UPDATE accounts SET is_sold=1 WHERE id=?", (acc_id,))
    cursor.execute("INSERT INTO orders (user_id, details, price) VALUES (?, ?, ?)", (user_id, details, price))
    conn.commit()
    await call.message.edit_text(f"✅ **Purchase Successful!**\n\n📦 **Details:**\n`{details}`\n\n💰 **New Balance:** ₹{new_bal:.2f}", parse_mode="Markdown")

@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    text = ("👑 **Admin Panel**\n\n"
            "🔹 `/addcat CategoryName` - Nayi category\n"
            "🔹 `/addcountry CategoryID CountryName Emoji` - Desh add karein\n"
            "🔹 `/addstock CountryID Price Details` - Stock add karein\n"
            "🔹 `/addbal UserID Amount` - User ko balance dein\n"
            "🔹 `/users` - Total users\n"
            "🔹 `/broadcast` - Sabko message bhejein")
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("users"))
async def admin_users(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    await message.answer(f"👥 Total Users: **{total}**", parse_mode="Markdown")

@dp.message(Command("addcat"))
async def admin_add_cat(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        name = message.text.split(" ", 1)[1]
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        await message.answer(f"✅ Category '{name}' added! ID: {cursor.lastrowid}")
    except: await message.answer("Format: `/addcat Cheapest`")

@dp.message(Command("addcountry"))
async def admin_add_country(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, cat_id, name, emoji = message.text.split()
        cursor.execute("INSERT INTO countries (cat_id, name, emoji) VALUES (?, ?, ?)", (cat_id, name, emoji))
        conn.commit()
        await message.answer(f"✅ Country '{name}' added! ID: {cursor.lastrowid}")
    except: await message.answer("Format: `/addcountry 1 India 🇮🇳`")

@dp.message(Command("addstock"))
async def admin_add_stock(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, country_id, price, details = message.text.split(" ", 3)
        cursor.execute("INSERT INTO accounts (country_id, price, details) VALUES (?, ?, ?)", (country_id, float(price), details))
        conn.commit()
        await message.answer(f"✅ Stock added! ID: {cursor.lastrowid}")
    except: await message.answer("Format: `/addstock 1 29 user_pass`")

@dp.message(Command("addbal"))
async def admin_add_bal(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid, amt = message.text.split()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(uid)))
        conn.commit()
        await message.answer(f"✅ Added ₹{amt} to User {uid}")
        await bot.send_message(int(uid), f"🎉 **Admin ne ₹{amt} add kiye hain!**", parse_mode="Markdown")
    except: await message.answer("Format: `/addbal 123456789 50`")

async def main():
    print("BOT IS RUNNING WITH QR & BROADCAST...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
