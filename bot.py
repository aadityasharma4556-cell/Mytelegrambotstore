import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient
from telethon.sessions import StringSession
from flask import Flask
import threading
import os

# ================= CONFIGURATION =================
BOT_TOKEN ="9165058570:AAFxCPAFVSzEXhKJ1aEPR4tLOINu80oGOvY"
ADMIN_ID = 8909356328

API_ID = 31622094 
API_HASH = "b74736e120d25868093397f0aef9b972" 

# Yahan aapki 3 IDs ki String Sessions hain
ACCOUNTS = {
    "AADITYA55": "1BVtsOLBu5bcYDogmakYZ1GukIOOTQ_hLPSfk3b6ZyyYatJIJ9dFTaHLeiME7m9Ky34jki_54YjyWTJgs1XQ2AEYZwZgp3PUO51c4_gUP34Vq17YBDWL2ECHNaEfeF0ozFUm-963I2-AokFvbMC7Qm0SrdJLopoQVqjXn_Te9cgQqxxT27lIP0hyV6i1402q-w2-1EsAZs2pur45qxfB-3kdtt10SK0gClkehT5aFNmNkw73OWBF68_1mYRhN3qsBx6V1k_6s_dvGHcy_uOPU5DwVKIiZXArfSiM3qoTBFFMNKIEO0NCyQ8bpIPKnnwFgEEkF-24bai_Q7dLW6CxcVKr_IpS9U=",
    
    "PATEL_NXT": "1BVtsOLCBuOH8kxfU3sQM9VuRZjxUqyhGLtbScy5fg5LmnNwTXwmqYSUqP1AvHJRJe2BfW1nZRJ13tV1jmar3bswrO1lFh3R05RrnNGoaS1UpCkoofo-Cbsfb0ySJT90lVQ_aP1nfBaujGB1ZfcLuw3FsRF25m0CRmoXVia5SyX41tSx4YtFv3UDG06xwyWHMIrmTVmMzyMvrEJePG8xQRnUvOFsv0P0egkfRr9r5G6S9DmLp3nFK278y2vas7aJeRl0xpw_kFcNINto1ijBLCKtIBwr2J4_aU2_ZR9FyeAAaA6G9e_tws4MHQKG_h450pFjU3PVai8kf1qMKaJpF9paDZCxePR0yQ=",
    
    "HARSHA": "1BVtsOLCBu2Q9k7e5m7Wba7TNFmnBX-WAci_6N2YcsgzT_kLxVL1NWP1oGRU3KApr1RWM2S_WBwCLzN_P1qO7qOS3waPCSP3Wu-0lpVF_3HFGKlXtdJJ817w3SSTdD618KPG7KX512xULKab1WvYA4_hr_y5xEiU54HCVBCXOgAhzPyhqquBin_1UNm70z8PecLU20Sro_9R6AW5UMFztjYU3PFhswEYaxon5ngc168wzA4CTqLo18iKG1y2gmbn5Evg2MJbGHshxUTGZkOg824VkuoR2zI3wpI8f0HR7MX37j23HiCVT12HoGH8iVm3foq3QQ-FA89b3pux1aJrNjbaJyJlc="
}
# =================================================

app = Flask(__name__)
@app.route('/')
def home(): return "Multi-Session Userbot Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_data = {}

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🚀 **Multi-Account Userbot**\n\nPehle apna message type karein:")

# 1. Message Receive karna
@dp.message(F.text & ~F.text.startswith('/') & ~F.text.startswith('🚀'))
async def get_message(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    user_data[message.from_user.id] = {"text": message.text}
    
    kb = [
        [InlineKeyboardButton(text="📩 Send to DMs (Personal)", callback_data="target_dm")],
        [InlineKeyboardButton(text="👥 Send to Groups", callback_data="target_group")]
    ]
    await message.answer("✅ Message saved!\n\nAb select karein kahan bhejna hai:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# 2. DM ya Group Select karna
@dp.callback_query(F.data.startswith("target_"))
async def select_account(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    
    target_type = call.data.split("_")[1]
    user_data[call.from_user.id]["target"] = target_type
    
    kb = []
    for name in ACCOUNTS.keys():
        kb.append([InlineKeyboardButton(text=f"User: {name}", callback_data=f"acc_{name}")])
    
    await call.message.edit_text(f"📍 Target: **{target_type.upper()}**\n\nAb select karein kis ID se bhejna hai:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

# 3. ID Select karke Message Bhejna
@dp.callback_query(F.data.startswith("acc_"))
async def send_from_account(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    
    account_name = call.data.split("_")[1]
    data = user_data.get(call.from_user.id)
    
    if not data or "text" not in data or "target" not in data:
        await call.answer("❌ Data missing! Pehle message type karein.", show_alert=True)
        return
        
    msg_text = data["text"]
    target_type = data["target"]
    
    await call.message.edit_text(f"⏳ **{account_name}** se **{target_type.upper()}** mein bheja ja raha hai...")
    
    try:
        session_str = ACCOUNTS[account_name].strip()
        client = TelegramClient(StringSession(session_str), int(API_ID), API_HASH)
        await client.start()
        
        dialogs = await client.get_dialogs()
        
        if target_type == "dm":
            chats = [d.entity.id for d in dialogs if d.is_user]
        else:
            chats = [d.entity.id for d in dialogs if d.is_group]

        success = 0
        for chat_id in chats:
            try:
                await client.send_message(chat_id, msg_text)
                success += 1
                await asyncio.sleep(1.5)
            except: pass
        
        await client.disconnect()
        await call.message.edit_text(f"✅ **Success!**\n\n{account_name} se {success} {target_type.upper()} mein message chala gaya.")
    except Exception as e:
        await call.message.edit_text(f"❌ Error: {str(e)}")

async def main():
    print("FINAL USERBOT IS RUNNING...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
