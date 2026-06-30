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
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

if not BOT_TOKEN:
    logging.error("❌ BOT_TOKEN is not set in environment variables")
    sys.exit(1)

log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

BOT_VERSION = "2.0.0"
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

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Convert Image", callback_data="start_convert"),
                InlineKeyboardButton(text="📋 Formats", callback_data="show_formats")
            ],
            [
                InlineKeyboardButton(text="ℹ️ About", callback_data="show_about"),
                InlineKeyboardButton(text="❓ Help", callback_data="show_help")
            ]
        ]
    )

@dp.message(Command("start"))
async def start_command(message: Message):
    welcome_text = (
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "Welcome to **FormatPro Bot** - your professional image conversion assistant!\n\n"
        "📸 **Features:**\n"
        "• Convert between 8 image formats\n"
        "• High-quality output\n"
        "• Fast processing\n"
        "• User-friendly interface\n\n"
        "🔧 **How to use:**\n"
        "1. Send /convert or click the button below\n"
        "2. Select your target format\n"
        "3. Upload the image\n"
        "4. Download your converted image!\n\n"
        "📊 **Commands:**\n"
        "/start - Show this menu\n"
        "/convert - Start conversion\n"
        "/formats - Show supported formats\n"
        "/about - Bot information\n"
        "/help - Get help"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

@dp.message(Command("convert"))
async def convert_command(message: Message, state: FSMContext):
    await state.set_state(ConversionStates.selecting_target_format)
    await message.answer(
        "🔄 **Start Image Conversion**\n\n"
        "Please select the **target format** you want to convert to:",
        reply_markup=get_format_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(Command("formats"))
async def formats_command(message: Message):
    formats_text = "📋 **Supported Image Formats:**\n\n"
    for fmt in SUPPORTED_FORMATS:
        formats_text += f"• `{fmt}`\n"
    await message.answer(formats_text, parse_mode="Markdown")

@dp.message(Command("about"))
async def about_command(message: Message):
    about_text = (
        "🤖 **FormatPro Bot**\n\n"
        f"📌 Version: `{BOT_VERSION}`\n"
        "⚡ Built with: `Aiogram 3` & `Pillow`\n"
        "📅 Status: ✅ **Online**\n\n"
        "💡 **Created for:** @FormatPro_Bot"
    )
    await message.answer(about_text, parse_mode="Markdown")

@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = (
        "🆘 **Help & Support**\n\n"
        "📖 **Basic Usage:**\n"
        "1. Send /convert\n"
        "2. Choose target format\n"
        "3. Upload image\n"
        "4. Wait for conversion\n\n"
        "⚡ **Tips:**\n"
        "• You can convert multiple images\n"
        "• Cancel with ❌ button\n"
        "• Large images may take a few seconds\n"
        "• Maximum file size: 20MB"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "start_convert")
async def start_convert_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await convert_command(callback.message, state)
    await callback.message.delete()

@dp.callback_query(lambda c: c.data == "show_formats")
async def show_formats_callback(callback: CallbackQuery):
    await callback.answer()
    await formats_command(callback.message)

@dp.callback_query(lambda c: c.data == "show_about")
async def show_about_callback(callback: CallbackQuery):
    await callback.answer()
    await about_command(callback.message)

@dp.callback_query(lambda c: c.data == "show_help")
async def show_help_callback(callback: CallbackQuery):
    await callback.answer()
    await help_command(callback.message)

@dp.callback_query(lambda c: c.data.startswith("format_"))
async def format_selection_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    target_format = callback.data.split("_")[1]
    await state.update_data(target_format=target_format)
    await state.set_state(ConversionStates.waiting_for_image)
    await callback.message.answer(
        f"✅ **Selected format:** `{target_format}`\n\n"
        "📤 **Now send me the image you want to convert.**\n"
        "You can send it as a photo or file.\n\n"
        "⚠️ Maximum file size: 20MB",
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        "❌ **Operation cancelled.**\n\n"
        "Use /convert to start again.",
        parse_mode="Markdown"
    )
    await callback.message.delete()

@dp.message(ConversionStates.waiting_for_image)
async def handle_image(message: Message, state: FSMContext):
    try:
        if not message.photo and not message.document:
            await message.answer(
                "⚠️ **Please send an image file.**\n\n"
                "You can send it as a photo or document.",
                parse_mode="Markdown"
            )
            return
        
        if message.photo:
            file = message.photo[-1]
            file_extension = "jpg"
            file_name = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        else:
            file = message.document
            if file.mime_type and not file.mime_type.startswith("image/"):
                await message.answer(
                    "⚠️ **Please send an image file.**\n\n"
                    f"Received: `{file.mime_type}`",
                    parse_mode="Markdown"
                )
                return
            file_extension = file.file_name.split('.')[-1].lower() if file.file_name else "jpg"
            file_name = file.file_name or f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        
        processing_msg = await message.answer("⏳ **Processing your image...**", parse_mode="Markdown")
        
        file_path = TEMP_DIR / file_name
        await bot.download(file, file_path)
        
        state_data = await state.get_data()
        target_format = state_data.get("target_format", "PNG")
        
        converter = ImageConverter(max_size_mb=20)
        
        source_format = file_extension.upper()
        if source_format == "JPG":
            source_format = "JPEG"
        
        output_format = target_format.lower()
        output_file = TEMP_DIR / f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
        
        success, result = await converter.convert(
            input_path=file_path,
            output_path=output_file,
            target_format=output_format,
            quality=90
        )
        
        if not success:
            await processing_msg.edit_text(f"❌ **Conversion Failed:** {result}", parse_mode="Markdown")
            await state.clear()
            return
        
        await processing_msg.delete()
        
        original_size = file_path.stat().st_size / 1024
        new_size = output_file.stat().st_size / 1024
        
        caption = (
            f"✅ **Conversion Complete!**\n\n"
            f"📄 **Source:** `{source_format}` → **Target:** `{target_format}`\n"
            f"📊 **Size:** `{original_size:.1f}KB` → `{new_size:.1f}KB`\n"
            f"📥 **Download your image below:**"
        )
        
        document = FSInputFile(output_file, filename=output_file.name)
        await message.answer_document(document, caption=caption, parse_mode="Markdown")
        
        await message.answer(
            "🎯 **Convert another image?**",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Convert Another", callback_data="start_convert")],
                    [InlineKeyboardButton(text="🏠 Main Menu", callback_data="start_convert")]
                ]
            ),
            parse_mode="Markdown"
        )
        
        try:
            file_path.unlink()
            output_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete temp files: {e}")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in handle_image: {e}")
        await message.answer(f"❌ **An error occurred:** `{str(e)}`", parse_mode="Markdown")
        await state.clear()

@dp.message()
async def handle_unknown(message: Message):
    await message.answer(
        "❓ **I don't understand that.**\n\n"
        "Use /help to see available commands or /start to get started.",
        parse_mode="Markdown"
    )

async def main():
    logger.info("🚀 Starting FormatPro Bot...")
    logger.info(f"📌 Version: {BOT_VERSION}")
    logger.info(f"🐍 Python: {sys.version}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
