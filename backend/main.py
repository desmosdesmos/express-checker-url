import os
import socket
from typing import Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

load_dotenv()

from .crawler import crawl_website
from .scorer import compile_full_audit
from .pdf_generator import generate_audit_pdf

app = FastAPI(
    title="Express Website Legal & Marketing Checker",
    description="Telegram Mini App service for auditing websites against 2026 RKN 152-FZ requirements and conversion factors.",
    version="1.1.0"
)

# Enable CORS for Telegram WebApp environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuditRequest(BaseModel):
    url: str


class SubCheckRequest(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None


@app.get("/api/health")
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Express Checker 2026", "author": "@yanv_tg"}


@app.post("/api/check-sub")
@app.post("/check-sub")
async def check_channel_subscription(req: SubCheckRequest):
    """Strictly verifies whether the user is subscribed to @yanv_tg channel."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "8902079020:AAGTldoxJ4u2UqlHVKiZPgLa96BJ4EvmEzM").strip() or "8902079020:AAGTldoxJ4u2UqlHVKiZPgLa96BJ4EvmEzM"
    channel = "@yanv_tg"
    channel_id = "-1002151986698"

    if not bot_token:
        return {
            "subscribed": False,
            "error": "no_bot_token",
            "message": "TELEGRAM_BOT_TOKEN не настроен на сервере"
        }

    if not req.user_id:
        return {
            "subscribed": False,
            "error": "no_user_id",
            "message": "Откройте сервис через Telegram-бота @auditurl_bot для проверки подписки"
        }

    try:
        session = AiohttpSession()
        session._connector_init = {"family": socket.AF_INET}
        bot = Bot(token=bot_token, session=session)

        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=req.user_id)
            is_sub = member.status in ["creator", "administrator", "member", "restricted"]
            return {
                "subscribed": is_sub,
                "status": member.status,
                "channel": channel,
                "channel_url": "https://t.me/yanv_tg",
                "message": "Подписка подтверждена!" if is_sub else "Вы не подписаны на канал @yanv_tg"
            }
        except Exception as api_err:
            err_text = str(api_err).lower()
            if "member list is inaccessible" in err_text or "not enough rights" in err_text or "chat not found" in err_text:
                return {
                    "subscribed": False,
                    "error": "bot_not_admin",
                    "channel": channel,
                    "channel_url": "https://t.me/yanv_tg",
                    "message": "Бот @auditurl_bot еще не добавлен в администраторы канала @yanv_tg. Добавьте бота в канал для проверки подписчиков!"
                }
            elif "user not found" in err_text:
                return {
                    "subscribed": False,
                    "error": "not_subscribed",
                    "channel": channel,
                    "channel_url": "https://t.me/yanv_tg",
                    "message": "Вы не подписаны на канал @yanv_tg. Подпишитесь и нажмите проверку еще раз."
                }
            else:
                return {
                    "subscribed": False,
                    "error": "telegram_error",
                    "detail": str(api_err),
                    "channel": channel,
                    "channel_url": "https://t.me/yanv_tg",
                    "message": f"Ошибка проверки подписки: {str(api_err)}"
                }
        finally:
            await bot.session.close()
    except Exception as e:
        return {
            "subscribed": False,
            "error": "network_error",
            "detail": str(e),
            "channel": channel,
            "channel_url": "https://t.me/yanv_tg",
            "message": "Ошибка связи с серверами Telegram"
        }


@app.post("/api/audit")
@app.post("/audit")
async def perform_audit(req: AuditRequest):
    raw_url = req.url.strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="Укажите URL сайта")

    site_data = await crawl_website(raw_url)
    if site_data.error:
        raise HTTPException(status_code=400, detail=site_data.error)

    report = compile_full_audit(site_data)
    return report


@app.post("/api/export-pdf")
@app.post("/export-pdf")
async def export_audit_pdf(req: AuditRequest):
    raw_url = req.url.strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="Укажите URL сайта")

    site_data = await crawl_website(raw_url)
    if site_data.error:
        raise HTTPException(status_code=400, detail=site_data.error)

    report = compile_full_audit(site_data)
    pdf_bytes = generate_audit_pdf(report)
    domain_clean = report.get("domain", "site").replace(".", "_")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="audit_2026_{domain_clean}.pdf"'
        }
    )


# Mount frontend static directory
public_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public"))
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
static_path = public_path if os.path.exists(public_path) else (frontend_path if os.path.exists(frontend_path) else None)
if static_path:
    app.mount("/", StaticFiles(directory=static_path, html=True), name="frontend")
