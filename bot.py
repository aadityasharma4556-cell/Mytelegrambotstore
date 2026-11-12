import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from telethon import TelegramClient
from telethon.sessions import StringSession
from flask import Flask
import threading
import os
import sqlite3

# ================= CONFIGURATION =================
BOT_TOKEN = "9165058570:AAFxCPAFVSzEXhKJ1aEPR4tLOINu80oGOvY"
ADMIN_ID = 8909356328
# =================================================

# --- RENDER KE LIYE FLASK ---
app = Flask(__name__)
@app.route('/')
def home(): return "Master Userbot Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- DATABASE ---
conn = sqlite3.connect('sessions.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, api_id TEXT, api_hash TEXT, session_string TEXT)""")
conn.commit()

# --- BOT SETUP ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class AddAccount(StatesGroup):
    waiting_phone = State()
    waiting_api_id = State()
    waiting_api_hash = State()
    waiting_otp = State()

def get_main_menu():
    kb = [
        [InlineKeyboardButton(text="📩 Send to DMs", callback_data="send_dm")],
        [InlineKeyboardButton(text="👥 Send to Groups", callback_data="send_group")],
        [InlineKeyboardButton(text="➕ Add New Account", callback_data="add_acc")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🚀 **Master Userbot**\n\nKya karna hai?", reply_markup=get_main_menu())

# --- ADD ACCOUNT PROCESS ---
@dp.callback_query(F.data == "add_acc")
async def add_account_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📱 Apna **Phone Number** bhejein (jaise: +919876543210):")
    await state.set_state(AddAccount.waiting_phone)

@dp.message(AddAccount.waiting_phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("🔑 Apni **API ID** bhejein:")
    await state.set_state(AddAccount.waiting_api_id)

@dp.message(AddAccount.waiting_api_id)
async def get_api_id(message: types.Message, state: FSMContext):
    await state.update_data(api_id=message.text)
    await message.answer("🔑 Apni **API HASH** bhejein:")
    await state.set_state(AddAccount.waiting_api_hash)

@dp.message(AddAccount.waiting_api_hash)
async def get_api_hash(message: types.Message, state: FSMContext):
    await state.update_data(api_hash=message.text) # <--- Yahan Hash save ho raha hai
    data = await state.get_data()
    
    api_hash = data.get('api_hash')
    phone = data.get('phone')
    api_id = data.get('api_id')
    
    await message.answer("⏳ OTP bheja ja raha hai... (Telegram par check karein)")
    
    try:
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        await client.connect()
        
        sent_code = await client.send_code_request(phone)
        
        session_str = client.session.save()
        await state.update_data(session_str=session_str, phone_code_hash=sent_code.phone_code_hash)
        
        await message.answer("📩 Apna **OTP** bhejein:")
        await state.set_state(AddAccount.waiting_otp)
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")
        await state.clear()
        await message.answer("Kya karna hai?", reply_markup=get_main_menu())

@dp.message(AddAccount.waiting_otp)
async def get_otp(message: types.Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get('phone')
    api_id = data.get('api_id')
    api_hash = data.get('api_hash')
    session_str = data.get('session_str')
    phone_code_hash = data.get('phone_code_hash')
    otp = message.text
    
    try:
        client = TelegramClient(StringSession(session_str), int(api_id), api_hash)
        await client.connect()
        
        await client.sign_in(phone, code=otp, phone_code_hash=phone_code_hash)
        
        final_session = client.session.save()
        
        cursor.execute("INSERT INTO accounts (phone, api_id, api_hash, session_string) VALUES (?, ?, ?, ?)", 
                       (phone, api_id, api_hash, final_session))
        conn.commit()
        
        await message.answer("✅ **Account Successfully Added!**\n\nAb aap is ID se message bhej sakte hain.")
        await client.disconnect()
    except Exception as e:
        await message.answer(f"❌ OTP Error: {str(e)}")
    
    await state.clear()
    await message.answer("Kya karna hai?", reply_markup=get_main_menu())

# --- SEND MESSAGE LOGIC ---
@dp.callback_query(F.data.startswith("send_"))
async def ask_message(call: types.CallbackQuery):
    target = call.data.split("_")[1] 
    await call.message.answer(f"📝 Aapne **{target.upper()}** select kiya hai.\n\nAb apna message type karein:")
    await call.message.edit_reply_markup(reply_markup=None)

@dp.message()
async def process_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    msg_text = message.text
    if msg_text.startswith("/") or msg_text.startswith("🚀") or msg_text.startswith("Kya karna"): return

    await message.answer("⏳ Saari IDs se message bheja ja raha hai...")

    cursor.execute("SELECT api_id, api_hash, session_string FROM accounts")
    accounts = cursor.fetchall()
    
    if not accounts:
        await message.answer("❌ Koi account nahi hai. Pehle 'Add New Account' karein.")
        return

    success = 0
    for api_id, api_hash, session_str in accounts:
        try:
            client = TelegramClient(StringSession(session_str), int(api_id), api_hash)
            await client.start()
            
            dialogs = await client.get_dialogs()
            chats = [d.entity.id for d in dialogs if d.is_user or d.is_group]

            for chat_id in chats:
                try:
                    await client.send_message(chat_id, msg_text)
                    success += 1
                    await asyncio.sleep(1.5)
                except: pass
            
            await client.disconnect()
        except Exception as e:
            print(f"Error on account {api_id}: {e}")

    await message.answer(f"✅ **Success!**\n\nMessage {success} jagah bhej diya gaya.")

async def main():
    print("MASTER USERBOT IS RUNNING...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
