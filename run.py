import asyncio
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

async def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    print("=" * 60)
    print("🚀 Запуск сервиса Экспресс-Аудита сайтов 2026 (@yanv_tg)")
    print(f"🌐 Telegram Mini App веб-сервер: http://localhost:{port}")
    print("=" * 60)

    # FastAPI Uvicorn Server Config
    config = uvicorn.Config(
        "backend.main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )
    server = uvicorn.Server(config)

    tasks = [asyncio.create_task(server.serve())]

    if bot_token and bot_token != "your_telegram_bot_token_here":
        from bot.bot import run_bot
        print("🤖 Запуск Telegram-бота...")
        tasks.append(asyncio.create_task(run_bot()))
    else:
        print("ℹ️ TELEGRAM_BOT_TOKEN не указан. Запущен только веб-сервер Telegram Mini App.")
        print("   Чтобы подключить Telegram-бота, укажите токен в файле .env")

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nОстановка сервиса.")
