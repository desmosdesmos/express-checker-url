import asyncio
import io
import os
import re
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    MenuButtonWebApp,
    BufferedInputFile
)
from dotenv import load_dotenv

from backend.crawler import crawl_website
from backend.scorer import compile_full_audit
from backend.pdf_generator import generate_audit_pdf

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-mini-app-domain.com")
CHANNEL_URL = "https://t.me/yanv_tg"
AUTHOR_URL = "https://t.me/yanvtg"

dp = Dispatcher()


def get_welcome_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="🚀 Запустить Экспресс-Аудит (Mini App)",
                web_app=WebAppInfo(url=webapp_url)
            )
        ],
        [
            InlineKeyboardButton(text="📢 Канал Яна (@yanv_tg)", url=CHANNEL_URL),
            InlineKeyboardButton(text="💬 Связь (@yanvtg)", url=AUTHOR_URL)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_result_keyboard(webapp_url: str, domain: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="🚀 Открыть подробный разбор в Mini App",
                web_app=WebAppInfo(url=f"{webapp_url}?site={domain}")
            )
        ],
        [
            InlineKeyboardButton(text="📢 Канал @yanv_tg", url=CHANNEL_URL),
            InlineKeyboardButton(text="👨‍💻 Экспресс-аудит под ключ", url=AUTHOR_URL)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot):
    # Setup bottom menu button for quick WebApp launch
    try:
        await bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(
                text="🚀 Аудит 2026",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
    except Exception:
        pass

    welcome_text = (
        "👋 **Добро пожаловать в сервис Экспресс-Аудита сайтов 2026!**\n\n"
        "Этот сервис разработан для проверки сайтов и интернет-магазинов (включая Tilda) "
        "на соответствие актуальному законодательству РФ и конверсионным стандартам продаж.\n\n"
        "⚖️ **Что проверяется:**\n"
        "• 152-ФЗ и новые штрафы до 18 000 000 ₽\n"
        "• Запрет предустановленных галочек в формах\n"
        "• Скрытые счетчики Google Analytics и Meta Pixel\n"
        "• Русификация по закону о госязыке 2026\n"
        "• Почему сайт не продает: оффер, CTA, мессенджеры\n\n"
        "👇 **Нажмите кнопку ниже, чтобы открыть интерактивный Mini App, либо просто отправьте ссылку на сайт в этот чат:**"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_welcome_keyboard(WEBAPP_URL))


@dp.message(F.text)
async def handle_url_message(message: types.Message):
    text = message.text.strip()

    # Simple domain / URL detector
    url_pattern = r"^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(\/.*)?$"
    if not re.match(url_pattern, text):
        await message.answer(
            "✍️ Отправьте адрес сайта (например: `tilda.cc` или `mysite.ru`), либо запустите удобный Mini App:",
            parse_mode="Markdown",
            reply_markup=get_welcome_keyboard(WEBAPP_URL)
        )
        return

    status_msg = await message.answer(f"🔍 **Сканирую сайт `{text}`...**\nПроверяю 152-ФЗ, РКН, формы и конверсию...", parse_mode="Markdown")

    try:
        site_data = await crawl_website(text)
        if site_data.error:
            await status_msg.edit_text(f"❌ Ошибка при проверке: {site_data.error}")
            return

        report = compile_full_audit(site_data)
        summary_text = report["telegram_summary"]

        # Generate PDF report
        pdf_bytes = generate_audit_pdf(report)
        pdf_file = BufferedInputFile(pdf_bytes, filename=f"audit_2026_{report['domain'].replace('.', '_')}.pdf")

        await status_msg.delete()

        # Send text summary
        await message.answer(
            summary_text,
            parse_mode="Markdown",
            reply_markup=get_result_keyboard(WEBAPP_URL, report["domain"])
        )

        # Send branded PDF file
        await message.answer_document(
            document=pdf_file,
            caption=f"📄 **Официальный PDF-отчет аудита для {report['domain']}**\nПодготовлено каналом @yanv_tg",
            parse_mode="Markdown"
        )

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Произошла непредвиденная ошибка: {str(e)}")


async def run_bot():
    if not BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set in environment or .env. Bot runner skipped.")
        return

    bot = Bot(token=BOT_TOKEN)
    print("Telegram bot started polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_bot())
