import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from .crawler import crawl_website
from .scorer import compile_full_audit
from .pdf_generator import generate_audit_pdf


app = FastAPI(
    title="Express Website Legal & Marketing Checker",
    description="Telegram Mini App service for auditing websites against 2026 RKN 152-FZ requirements and conversion factors.",
    version="1.0.0"
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


@app.get("/api/health")
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Express Checker 2026", "author": "@yanv_tg"}


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


# Mount frontend static directory if exists
public_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public"))
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
static_path = public_path if os.path.exists(public_path) else (frontend_path if os.path.exists(frontend_path) else None)
if static_path:
    app.mount("/", StaticFiles(directory=static_path, html=True), name="frontend")
