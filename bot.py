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
BOT_TOKEN = "9073036935:AAGrmTAE2ki6au8ZITDP_W_Ln_d_-0VGnAU"
ADMIN_ID = 7961207555 # Apna ID
MIN_WITHDRAW = 20.0
# =================================================

# --- FLASK SETUP ---
app = Flask(__name__)
@app.route('/')
def home(): return "Task Bot Running!"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- DATABASE ---
conn = sqlite3.connect("task_bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS channels (link TEXT PRIMARY KEY)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL, upi_id TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS withdraws (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, upi_id TEXT, status TEXT DEFAULT 'Pending')""")
conn.commit()

cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (ADMIN_ID,))
conn.commit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# States
class SetTask(StatesGroup):
    waiting_for_amount = State()
    waiting_for_upi = State()
class AddChannel(StatesGroup):
    waiting_for_channel = State()
class AddAdminState(StatesGroup):
    waiting_for_id = State()
class WithdrawState(StatesGroup):
    waiting_for_upi = State()
class BroadcastState(StatesGroup):
    waiting_for_msg = State()

# --- HELPERS ---
async def is_admin(uid):
    if uid == ADMIN_ID: return True
    cursor.execute("SELECT user_id FROM admins WHERE user_id=?", (uid,))
    return cursor.fetchone() is not None

async def check_join(uid):
    cursor.execute("SELECT link FROM channels")
    channels = cursor.fetchall()
    if not channels: return True 
    for ch in channels:
        try:
            chat_id = ch[0].split("/")[-1] 
            if not chat_id.startswith("@"):
                chat_id = "@" + chat_id
            member = await bot.get_chat_member(chat_id=chat_id, user_id=uid)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except: return False
    return True

def user_menu():
    kb = [
        [InlineKeyboardButton(text="🆘 SOS (Support)", callback_data="u_sos")],
        [InlineKeyboardButton(text="💸 Withdraw", callback_data="u_withdraw"), InlineKeyboardButton(text="📸 Get QR", callback_data="u_getqr")],
        [InlineKeyboardButton(text="📊 Pending Payment", callback_data="u_pending")],
        [InlineKeyboardButton(text="📤 Direct Screenshot Bhejein", callback_data="u_direct_ss")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_menu():
    kb = [
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="a_broadcast"), InlineKeyboardButton(text="👑 Add Admin", callback_data="a_addadmin")],
        [InlineKeyboardButton(text="📸 Set Task (QR)", callback_data="a_settask"), InlineKeyboardButton(text="📢 Add Channel", callback_data="a_addchannel")],
        [InlineKeyboardButton(text="👥 Total Users", callback_data="a_users"), InlineKeyboardButton(text="💸 Pending Withdraws", callback_data="a_withdraws")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    conn.commit()
    
    if not await check_join(uid):
        cursor.execute("SELECT link FROM channels")
        channels = cursor.fetchall()
        kb = []
        for ch in channels:
            kb.append([InlineKeyboardButton(text="📢 Join Channel", url=ch[0])])
        kb.append([InlineKeyboardButton(text="✅ Try Again", callback_data="verify_join")])
        await message.answer("⚠️ **Bot use karne ke liye pehle channel join karein!**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
        return

    if await is_admin(uid):
        await message.answer("👑 **Welcome Admin!**", reply_markup=admin_menu(), parse_mode="Markdown")
    else:
        await message.answer(f"👋 **Welcome to Task Bot**\n\n🆔 Your ID: `{uid}`\n\nScreenshot bhejein ya Get QR dabayein.", reply_markup=user_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "verify_join")
async def verify_join(call: types.CallbackQuery):
    if await check_join(call.from_user.id):
        await call.message.delete()
        await start_cmd(call.message)
    else:
        await call.answer("❌ Aapne abhi tak join nahi kiya!", show_alert=True)

# --- AUTO DELETE TASK (3 MINUTE) ---
async def delete_task_later(chat_id, message_id, delay=180):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# --- USER FEATURES ---
@dp.callback_query(F.data == "u_sos")
async def u_sos(call: types.CallbackQuery):
    await call.message.edit_text("🆘 **Support**\n\nAdmin se contact karein: @YourAdminUsername", reply_markup=user_menu())

@dp.callback_query(F.data == "u_getqr")
async def u_getqr(call: types.CallbackQuery):
    cursor.execute("SELECT amount, upi_id FROM tasks ORDER BY id DESC LIMIT 1")
    task = cursor.fetchone()
    if not task:
        await call.answer("❌ Admin ne abhi koi task nahi dala!", show_alert=True)
        return
    
    amount, upi_id = task
    upi_link = f"upi://pay?pa={upi_id}&pn=Task&am={amount}&cu=INR"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(upi_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    text = f"📸 **Task QR**\n\nAmount: ₹{amount}\nUPI: `{upi_id}`\n\n⚠️ **Yeh QR 3 minute baad delete ho jayega.**\n\nPayment karne ke baad apna screenshot bhejein."
    
    msg = await call.message.answer_photo(photo=BufferedInputFile(buf.read(), filename="qr.png"), caption=text, parse_mode="Markdown")
    
    # 3 minute baad delete karne ka task
    asyncio.create_task(delete_task_later(call.message.chat.id, msg.message_id, 180))

@dp.callback_query(F.data == "u_withdraw")
async def u_withdraw(call: types.CallbackQuery, state: FSMContext):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    bal = cursor.fetchone()[0]
    if bal < MIN_WITHDRAW:
        await call.answer(f"❌ Minimum withdraw ₹{MIN_WITHDRAW} hai. Balance: ₹{bal}", show_alert=True)
        return
    await call.message.edit_text(f"💸 Balance: ₹{bal}\n\nApni UPI ID type karein:")
    await state.set_state(WithdrawState.waiting_for_upi)

@dp.message(WithdrawState.waiting_for_upi)
async def process_withdraw(message: types.Message, state: FSMContext):
    upi = message.text
    uid = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    bal = cursor.fetchone()[0]
    
    cursor.execute("INSERT INTO withdraws (user_id, amount, upi_id) VALUES (?, ?, ?)", (uid, bal, upi))
    cursor.execute("UPDATE users SET balance = 0 WHERE user_id=?", (uid,))
    conn.commit()
    w_id = cursor.lastrowid
    
    await message.answer("✅ Withdraw request bhej di gayi!")
    await state.clear()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Approve", callback_data=f"w_app_{w_id}_{uid}_{bal}")]])
    await bot.send_message(ADMIN_ID, f"🔔 **Withdraw Request**\nUser: `{uid}`\nAmount: ₹{bal}\nUPI: `{upi}`", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("w_app_"))
async def approve_withdraw(call: types.CallbackQuery):
    _, w_id, uid, amt = call.data.split("_")
    await bot.send_message(int(uid), f"🎉 **Withdraw Approved!** ₹{amt} bhej diye gaye hain.")
    await call.message.edit_text(f"{call.message.text}\n\n✅ **Paid!**")

@dp.callback_query(F.data == "u_pending")
async def u_pending(call: types.CallbackQuery):
    await call.answer("Aapki koi pending payment nahi hai.", show_alert=True)

@dp.callback_query(F.data == "u_direct_ss")
async def ask_direct_ss(call: types.CallbackQuery):
    await call.message.answer("📸 Kripya apna Payment Screenshot bhejein:")
    await call.answer()

# --- ADMIN FEATURES ---
@dp.callback_query(F.data == "a_addadmin")
async def a_addadmin(call: types.CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id): return
    await call.message.edit_text("👑 Naye Admin ki Telegram ID bhejein:")
    await state.set_state(AddAdminState.waiting_for_id)

@dp.message(AddAdminState.waiting_for_id)
async def save_admin(message: types.Message, state: FSMContext):
    try:
        new_id = int(message.text)
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_id,))
        conn.commit()
        await message.answer(f"✅ {new_id} ab Admin hai!")
    except:
        await message.answer("❌ Invalid ID.")
    await state.clear()

@dp.callback_query(F.data == "a_addchannel")
async def a_addchannel(call: types.CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id): return
    await call.message.edit_text("📢 Channel ka link bhejein (jaise: https://t.me/YourChannel):")
    await state.set_state(AddChannel.waiting_for_channel)

@dp.message(AddChannel.waiting_for_channel)
async def save_channel(message: types.Message, state: FSMContext):
    cursor.execute("INSERT OR IGNORE INTO channels (link) VALUES (?)", (message.text,))
    conn.commit()
    await message.answer("✅ Channel add ho gaya! Ab users ko pehle join karna hoga.")
    await state.clear()

@dp.callback_query(F.data == "a_settask")
async def a_settask(call: types.CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id): return
    await call.message.edit_text("💰 Task ka Amount likhein (jaise: 10):")
    await state.set_state(SetTask.waiting_for_amount)

@dp.message(SetTask.waiting_for_amount)
async def set_task_amt(message: types.Message, state: FSMContext):
    await state.update_data(amount=float(message.text))
    await message.answer("📱 UPI ID likhein:")
    await state.set_state(SetTask.waiting_for_upi)

@dp.message(SetTask.waiting_for_upi)
async def set_task_upi(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO tasks (amount, upi_id) VALUES (?, ?)", (data['amount'], message.text))
    conn.commit()
    await message.answer("✅ Task set ho gaya! Users ab QR code dekh sakte hain.")
    await state.clear()

@dp.callback_query(F.data == "a_broadcast")
async def a_broadcast(call: types.CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id): return
    await call.message.edit_text("📢 Jo message sabko bhejna hai, type karein:")
    await state.set_state(BroadcastState.waiting_for_msg)

@dp.message(BroadcastState.waiting_for_msg)
async def send_broadcast(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    success = 0
    await message.answer("⏳ Bheja ja raha hai...")
    for u in users:
        try:
            await message.copy_to(chat_id=u[0])
            success += 1
            await asyncio.sleep(0.1)
        except: pass
    await message.answer(f"✅ {success} users ko bhej diya gaya!")
    await state.clear()

@dp.callback_query(F.data == "a_users")
async def a_users(call: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    await call.answer(f"👥 Total Users: {total}", show_alert=True)

# --- SCREENSHOT CATCHER (DIRECT BHEJNE PAR) ---
@dp.message(F.photo)
async def catch_screenshot(message: types.Message):
    uid = message.from_user.id
    admin_text = f"🔔 **Naya Payment Screenshot!**\n\nUser ID: `{uid}`\n\nKya aapne paisa receive kiya hai?"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve ₹10", callback_data=f"ss_app_{uid}_10")],
        [InlineKeyboardButton(text="❌ Reject", callback_data=f"ss_rej_{uid}")]
    ])
    await bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=kb, parse_mode="Markdown")
    await message.answer("⏳ **Screenshot Admin ko bhej diya gaya hai.**")

@dp.callback_query(F.data.startswith("ss_app_"))
async def approve_screenshot(call: types.CallbackQuery):
    _, uid, amt = call.data.split("_")
    uid = int(uid)
    amt = float(amt)
    
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
    conn.commit()
    
    await call.message.edit_caption(caption=f"{call.message.caption}\n\n✅ **APPROVED! ₹{amt} add ho gaye.**")
    await bot.send_message(uid, f"🎉 **Payment Approved!** ₹{amt} aapke wallet mein add ho gaye hain.")

@dp.callback_query(F.data.startswith("ss_rej_"))
async def reject_screenshot(call: types.CallbackQuery):
    await call.message.edit_caption(caption=f"{call.message.caption}\n\n❌ **REJECTED!**")

async def main():
    print("TASK BOT IS RUNNING...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
