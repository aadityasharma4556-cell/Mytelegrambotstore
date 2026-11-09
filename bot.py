import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient

# ================= CONFIGURATION =================
BOT_TOKEN = "9249899265:AAG_RdEz9axRfptwAggt6j9SEH62YFLeyTM" # @BotFather se lein
ADMIN_ID = 7961207555 # Apna Telegram ID
# =================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# States (Data lene ke liye)
class SetupState(StatesGroup):
    waiting_api_hash = State()
    waiting_phone = State()
    waiting_api_id = State()
    waiting_message = State()

# --- START COMMAND ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Yeh bot sirf Admin ke liye hai.")
        return
    
    await message.answer("🚀 **Welcome to Auto-DM Bot Setup!**\n\nPehle apni **API HASH** bhejein:")
    await state.set_state(SetupState.waiting_api_hash)

# --- STEP 1: API HASH ---
@dp.message(SetupState.waiting_api_hash)
async def get_api_hash(message: types.Message, state: FSMContext):
    await state.update_data(api_hash=message.text)
    await message.answer("✅ API HASH saved!\n\nAb apna **Phone Number** bhejein (jaise: +919876543210):")
    await state.set_state(SetupState.waiting_phone)

# --- STEP 2: PHONE NUMBER ---
@dp.message(SetupState.waiting_phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("✅ Phone Number saved!\n\nAb apni **API ID** bhejein:")
    await state.set_state(SetupState.waiting_api_id)

# --- STEP 3: API ID ---
@dp.message(SetupState.waiting_api_id)
async def get_api_id(message: types.Message, state: FSMContext):
    await state.update_data(api_id=message.text)
    await message.answer("✅ API ID saved!\n\nAb wo **Message** bhejein jo aap sabko bhejna chahte hain:")
    await state.set_state(SetupState.waiting_message)

# --- STEP 4: MESSAGE BHEJNA (FINAL STEP) ---
@dp.message(SetupState.waiting_message)
async def send_broadcast(message: types.Message, state: FSMContext):
    data = await state.get_data()
    api_hash = data.get('api_hash')
    phone = data.get('phone')
    api_id = data.get('api_id')
    msg_text = message.text

    await message.answer("⏳ Aapka Userbot connect ho raha hai... (OTP aa sakta hai)")

    try:
        # Userbot connect karo
        client = TelegramClient('session_' + phone, int(api_id), api_hash)
        await client.start(phone=phone)
        
        await message.answer("✅ Userbot Connected!\n\nAb sabhi users ko message bheja ja raha hai...")
        
        # Saare dialogs (chats) ki list nikalna
        dialogs = await client.get_dialogs()
        users_to_send = [d.entity.id for d in dialogs if d.is_user]

        success = 0
        for uid in users_to_send:
            try:
                await client.send_message(uid, msg_text)
                success += 1
                await asyncio.sleep(1) # 1 second delay (Spam se bachne ke liye)
            except:
                pass
        
        await client.disconnect()
        await message.answer(f"✅ **Success!**\n\nMessage {success} users ko bhej diya gaya hai.")
    
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}\n\nKripya details check karein.")

    await state.clear()

async def main():
    print("INTERACTIVE USERBOT RUNNING...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 
