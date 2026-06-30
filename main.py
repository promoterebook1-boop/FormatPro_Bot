import os
import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from utils.converter import ImageConverter

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logging.error("❌ BOT_TOKEN is not set")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

SUPPORTED_FORMATS = ["PNG", "JPG", "JPEG", "WEBP", "BMP", "ICO", "GIF", "TIFF"]

class ConversionStates(StatesGroup):
    waiting_for_image = State()
    selecting_target_format = State()

def get_format_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for i, fmt in enumerate(SUPPORTED_FORMATS):
        row.append(InlineKeyboardButton(text=fmt, callback_data=f"format_{fmt}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "Welcome to FormatPro Bot - Image Converter!\n\n"
        "Send /convert to start converting images.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Convert", callback_data="start_convert")
            ]]
        ),
        parse_mode="Markdown"
    )

@dp.message(Command("convert"))
async def convert_command(message: Message, state: FSMContext):
    await state.set_state(ConversionStates.selecting_target_format)
    await message.answer(
        "Select target format:",
        reply_markup=get_format_keyboard()
    )

@dp.callback_query(lambda c: c.data == "start_convert")
async def start_convert_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await convert_command(callback.message, state)
    await callback.message.delete()

@dp.callback_query(lambda c: c.data.startswith("format_"))
async def format_selection_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    target_format = callback.data.split("_")[1]
    await state.update_data(target_format=target_format)
    await state.set_state(ConversionStates.waiting_for_image)
    await callback.message.answer(f"✅ Format: {target_format}\n\nSend me the image to convert.")

@dp.callback_query(lambda c: c.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer("❌ Cancelled. Use /convert to start again.")

@dp.message(ConversionStates.waiting_for_image)
async def handle_image(message: Message, state: FSMContext):
    try:
        if not message.photo and not message.document:
            await message.answer("Please send an image file.")
            return
        
        if message.photo:
            file = message.photo[-1]
            file_name = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        else:
            file = message.document
            if file.mime_type and not file.mime_type.startswith("image/"):
                await message.answer("Please send an image file.")
                return
            file_name = file.file_name or f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        processing_msg = await message.answer("⏳ Processing...")
        
        file_path = TEMP_DIR / file_name
        await bot.download(file, file_path)
        
        state_data = await state.get_data()
        target_format = state_data.get("target_format", "PNG")
        
        converter = ImageConverter()
        output_file = TEMP_DIR / f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{target_format.lower()}"
        
        success, result = await converter.convert(
            input_path=file_path,
            output_path=output_file,
            target_format=target_format.lower()
        )
        
        if not success:
            await processing_msg.edit_text(f"❌ {result}")
            return
        
        await processing_msg.delete()
        
        document = FSInputFile(output_file, filename=output_file.name)
        await message.answer_document(document, caption=f"✅ Converted to {target_format}")
        
        try:
            file_path.unlink()
            output_file.unlink()
        except:
            pass
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(f"❌ Error: {str(e)}")
        await state.clear()

@dp.message()
async def handle_unknown(message: Message):
    await message.answer("Use /start or /convert")

async def main():
    logger.info("🚀 Starting FormatPro Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
