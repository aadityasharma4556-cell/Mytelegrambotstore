import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ================= CONFIGURATION (YAHAN APNI DETAILS DALEIN) =================
BOT_TOKEN = "8807197307:AAEt97vbkka5seC-TjC53I6APykduXuPSbM"
ADMIN_ID = 7961207555 # Apna Telegram ID
CHANNEL_ID = "@AADIFYAXX09" # Apna Update Channel
GROUP_ID = "@AADITYAMAKER" # Apna Support Group
UPI_ID = "Aadityasharma3315@fam" 
# =============================================================================

# Database Setup
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

# States for Admin
class AdminStates(StatesGroup):
    add_cat = State()
    add_country_name = State()
    add_country_emoji = State()
    add_stock_price = State()
    add_stock_details = State()

# --- HELPER: FORCE JOIN CHECK ---
async def check_join(user_id):
    try:
        c = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        g = await bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
        if c.status in ['member', 'administrator', 'creator'] and g.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        return False

# --- MAIN MENU (Screenshot 3 Jaisa) ---
def get_main_menu():
    kb = [
        [InlineKeyboardButton(text="🛒 Purchase Accounts", callback_data="menu_purchase")],
        [InlineKeyboardButton(text="💳 Deposit", callback_data="menu_deposit"), 
         InlineKeyboardButton(text="💰 Wallet", callback_data="menu_wallet")],
        [InlineKeyboardButton(text="📦 My Orders", callback_data="menu_orders"), 
         InlineKeyboardButton(text="🎁 Referral", callback_data="menu_ref")],
        [InlineKeyboardButton(text="📞 Support", callback_data="menu_support")],
        [InlineKeyboardButton(text="📜 Terms & Conditions", callback_data="menu_tnc")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- START COMMAND ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0))
    conn.commit()
    
    if not await check_join(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Updates Channel", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
            [InlineKeyboardButton(text="💬 Join Support Group", url=f"https://t.me/{GROUP_ID.replace('@', '')}")],
            [InlineKeyboardButton(text="✅ Try Again", callback_data="verify_join")]
        ])
        await message.answer("⚠️ **To use this bot, you must join our updates channel and group first.**", reply_markup=kb, parse_mode="Markdown")
        return

    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    text = f"👑 **Welcome to TG Accounts Store**\n\n🏦 **Your Balance:** ₹{bal:.2f} ($0.00)\n\n👇 Click Purchase Accounts below to browse & buy stock."
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "verify_join")
async def verify_join(call: types.CallbackQuery):
    if await check_join(call.from_user.id):
        await call.message.delete()
        await start_cmd(call.message)
    else:
        await call.answer("❌ You haven't joined both channel and group yet!", show_alert=True)

# --- MENU CALLBACKS ---
@dp.callback_query(F.data.startswith("menu_"))
async def menu_handler(call: types.CallbackQuery):
    action = call.data.split("_")[1]
    
    if action == "purchase":
        await show_categories(call)
    elif action == "wallet":
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
        bal = cursor.fetchone()[0]
        await call.message.edit_text(f"💰 **Your Wallet**\n\nCurrent Balance: ₹{bal:.2f}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_menu")]]), parse_mode="Markdown")
    elif action == "deposit":
        text = f"💳 **Deposit Funds**\n\nUPI ID: `{UPI_ID}`\n\nPay & send screenshot to Admin: `{ADMIN_ID}`"
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_menu")]]), parse_mode="Markdown")
    elif action == "orders":
        cursor.execute("SELECT details, price FROM orders WHERE user_id=?", (call.from_user.id,))
        orders = cursor.fetchall()
        if not orders:
            text = "📦 **My Orders**\n\nNo orders found."
        else:
            text = "📦 **My Orders**\n\n" + "\n".join([f"🔹 `{o[0]}` - ₹{o[1]}" for o in orders])
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_menu")]]), parse_mode="Markdown")
    elif action in ["support", "ref", "tnc"]:
        await call.answer("Yeh feature jald aa raha hai!", show_alert=True)

@dp.callback_query(F.data == "back_menu")
async def back_menu(call: types.CallbackQuery):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    bal = cursor.fetchone()[0]
    text = f"👑 **Welcome to TG Accounts Store**\n\n🏦 **Your Balance:** ₹{bal:.2f} ($0.00)\n\n👇 Click Purchase Accounts below to browse & buy stock."
    await call.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="Markdown")

# --- PURCHASE FLOW: CATEGORIES & COUNTRIES ---
async def show_categories(call: types.CallbackQuery):
    cursor.execute("SELECT id, name FROM categories")
    cats = cursor.fetchall()
    if not cats:
        await call.answer("Admin ne abhi category nahi banayi hai!", show_alert=True)
        return
    
    kb = [[InlineKeyboardButton(text=f"🔖 {c[1]}", callback_data=f"cat_{c[0]}")] for c in cats]
    kb.append([InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_menu")])
    await call.message.edit_text("📌 **Selected Category: Cheapest**\n\n👇 Select a category to browse stock:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("cat_"))
async def show_countries(call: types.CallbackQuery):
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

# --- PAGINATION & STOCK VIEW (Screenshot 1 Jaisa) ---
@dp.callback_query(F.data.startswith("cntry_"))
async def show_stock_page(call: types.CallbackQuery):
    data = call.data.split("_")
    country_id = data[1]
    page = int(data[2]) if len(data) > 2 else 1
    limit = 6
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

    text = f"🇮🇳 **Available Accounts** - Page {page}\n\n⚡ Instant Delivery | 🛡️ Spam-Free\n👇 **Select an account to purchase:**"
    
    kb = []
    for a in accs:
        kb.append([InlineKeyboardButton(text=f"💳 🇮🇳 - ₹{a[1]:.2f} ($0.00)", callback_data=f"buy_{a[0]}")])
        
    # Pagination Buttons
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Back", callback_data=f"cntry_{country_id}_{page-1}"))
    if total_accs > page * limit:
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"cntry_{country_id}_{page+1}"))
        
    if nav_row:
        kb.append(nav_row)
    
    kb.append([InlineKeyboardButton(text="🔄 Refresh", callback_data=f"cntry_{country_id}_{page}")])
    kb.append([InlineKeyboardButton(text="🔙 Main Menu", callback_data="back_menu")])
    
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

# --- BUY LOGIC ---
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(call: types.CallbackQuery):
    acc_id = call.data.split("_")[1]
    user_id = call.from_user.id
    
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    user_bal = cursor.fetchone()[0]
    
    cursor.execute("SELECT price, details FROM accounts WHERE id=? AND is_sold=0", (acc_id,))
    acc = cursor.fetchone()
    
    if not acc:
        await call.answer("❌ Sold out! Kisi aur ne khareed liya.", show_alert=True)
        return
        
    price, details = acc
    
    if user_bal < price:
        await call.answer(f"❌ Balance kam hai! Aapke paas ₹{user_bal} hain, iski price ₹{price} hai.", show_alert=True)
        return
        
    new_bal = user_bal - price
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, user_id))
    cursor.execute("UPDATE accounts SET is_sold=1 WHERE id=?", (acc_id,))
    cursor.execute("INSERT INTO orders (user_id, details, price) VALUES (?, ?, ?)", (user_id, details, price))
    conn.commit()
    
    success_text = f"✅ **Purchase Successful!**\n\n📦 **Account Details:**\n`{details}`\n\n💰 **New Balance:** ₹{new_bal:.2f}"
    await call.message.edit_text(success_text, parse_mode="Markdown")

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    text = ("👑 **Admin Panel**\n\n"
            "🔹 `/addcat CategoryName` - Nayi category (e.g. Cheapest)\n"
            "🔹 `/addcountry CategoryID CountryName Emoji` - Desh add karein\n"
            "🔹 `/addstock CountryID Price Details` - Stock add karein\n"
            "🔹 `/addbal UserID Amount` - User ko balance dein\n\n"
            "*Note: Details mein space mat dena, underscore (_) use karein.*")
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("addcat"))
async def admin_add_cat(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        name = message.text.split(" ", 1)[1]
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        await message.answer(f"✅ Category '{name}' added! ID: {cursor.lastrowid}")
    except:
        await message.answer("Format: `/addcat Cheapest`", parse_mode="Markdown")

@dp.message(Command("addcountry"))
async def admin_add_country(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, cat_id, name, emoji = message.text.split()
        cursor.execute("INSERT INTO countries (cat_id, name, emoji) VALUES (?, ?, ?)", (cat_id, name, emoji))
        conn.commit()
        await message.answer(f"✅ Country '{name}' added to Category {cat_id}! ID: {cursor.lastrowid}")
    except:
        await message.answer("Format: `/addcountry 1 India 🇮🇳`", parse_mode="Markdown")

@dp.message(Command("addstock"))
async def admin_add_stock(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, country_id, price, details = message.text.split(" ", 3)
        cursor.execute("INSERT INTO accounts (country_id, price, details) VALUES (?, ?, ?)", (country_id, float(price), details))
        conn.commit()
        await message.answer(f"✅ Stock added! Account ID: {cursor.lastrowid}")
    except:
        await message.answer("Format: `/addstock 1 29 +91_9876543210|Pass123`", parse_mode="Markdown")

@dp.message(Command("addbal"))
async def admin_add_bal(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid, amt = message.text.split()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(uid)))
        conn.commit()
        await message.answer(f"✅ Added ₹{amt} to User {uid}")
        await bot.send_message(int(uid), f"🎉 **Admin ne aapke wallet mein ₹{amt} add kiye hain!**", parse_mode="Markdown")
    except:
        await message.answer("Format: `/addbal 123456789 50`", parse_mode="Markdown")

async def main():
    print("SUPER BOT IS RUNNING...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
