from typing import Any, Dict, List
from .crawler import SiteData
from .legal_checker import run_legal_audit
from .marketing_checker import run_marketing_audit


def compile_full_audit(site: SiteData) -> Dict[str, Any]:
    """Compiles both legal (27 items) and marketing audits into a unified report."""
    legal_items = run_legal_audit(site)
    marketing = run_marketing_audit(site)

    total_legal = 27
    passed_legal = sum(1 for item in legal_items if item["status"] == "passed")
    failed_legal = sum(1 for item in legal_items if item["status"] == "failed")
    warning_legal = sum(1 for item in legal_items if item["status"] == "warning")
    legal_percent = int(round((passed_legal / total_legal) * 100))

    # Calculate fines and risk levels
    has_critical_legal = any(item["status"] == "failed" and item.get("risk_level") == "critical" for item in legal_items)
    has_high_legal = any(item["status"] == "failed" and item.get("risk_level") == "high" for item in legal_items)

    if has_critical_legal or failed_legal >= 5:
        overall_risk = "Критический риск"
        risk_color = "#ef4444"
    elif has_high_legal or failed_legal >= 2:
        overall_risk = "Высокий риск"
        risk_color = "#f97316"
    elif warning_legal > 4 or failed_legal >= 1:
        overall_risk = "Умеренный риск"
        risk_color = "#eab308"
    else:
        overall_risk = "Минимальный риск"
        risk_color = "#22c55e"

    # Specific fine tags matching user's PDF
    form_items = [i for i in legal_items if i["id"] in [8, 9, 11]]
    form_failed = any(i["status"] == "failed" for i in form_items)
    fine_form_text = "до 700 000 ₽" if form_failed else "0 ₽ (В норме)"

    loc_items = [i for i in legal_items if i["id"] in [17, 18, 19]]
    loc_failed = any(i["status"] == "failed" for i in loc_items)
    fine_loc_text = "до 18 000 000 ₽" if loc_failed else "0 ₽ (В норме)"

    # Group legal items by blocks (1 to 7)
    blocks_dict: Dict[int, Dict[str, Any]] = {}
    for item in legal_items:
        b_id = item["block_id"]
        if b_id not in blocks_dict:
            blocks_dict[b_id] = {
                "block_id": b_id,
                "block_title": item["block_title"],
                "items": []
            }
        blocks_dict[b_id]["items"].append(item)

    blocks_list = list(blocks_dict.values())

    # Build concise text report for Telegram message
    top_legal_issues = [f"• {i['title']} ({i['fine_info']})" for i in legal_items if i["status"] == "failed"][:4]
    top_marketing_issues = [f"• {c['title']}: {c['impact']}" for c in marketing["checks"] if c["status"] == "failed"][:3]

    telegram_summary = (
        f"📊 **Экспресс-Аудит сайта:** {site.domain}\n"
        f"🌐 Движок: {'Tilda' if site.is_tilda else 'Сайт / CMS'}\n"
        f"⏱ Время ответа: {site.response_time_ms} мс | SSL: {'✅ HTTPS' if site.is_https else '❌ Без SSL'}\n\n"
        f"⚖️ **Юридическая готовность (2026 г.):** {passed_legal} / {total_legal} ({legal_percent}%)\n"
        f"🚨 Уровень риска: **{overall_risk}**\n"
        f"💸 Штраф за формы: **{fine_form_text}**\n"
        f"💸 Риск локализации: **{fine_loc_text}**\n\n"
        f"🚀 **Маркетинг и продажи (UX):** {marketing['score']}/100\n"
    )

    if top_legal_issues:
        telegram_summary += "\n🔴 **Критические юридические риски:**\n" + "\n".join(top_legal_issues) + "\n"
    if top_marketing_issues:
        telegram_summary += "\n⚠️ **Почему сайт теряет заявки:**\n" + "\n".join(top_marketing_issues) + "\n"

    telegram_summary += (
        f"\n💡 Подробный разбор и официальный PDF-отчет сформированы в Mini App.\n\n"
        f"📢 Канал автора: @yanv_tg\n"
        f"👨‍💻 Экспресс-аудит под ключ: @yanvtg"
    )

    return {
        "url": site.final_url or site.raw_url,
        "domain": site.domain,
        "is_tilda": site.is_tilda,
        "is_https": site.is_https,
        "response_time_ms": site.response_time_ms,
        "ip_address": site.ip_address,
        "hosting_provider": site.hosting_provider_guess,
        "is_ru_hosting": site.is_ru_hosting,
        "legal": {
            "total": total_legal,
            "passed": passed_legal,
            "failed": failed_legal,
            "warning": warning_legal,
            "percent": legal_percent,
            "overall_risk": overall_risk,
            "risk_color": risk_color,
            "fine_form": fine_form_text,
            "fine_loc": fine_loc_text,
            "blocks": blocks_list,
            "items": legal_items
        },
        "marketing": marketing,
        "telegram_summary": telegram_summary,
        "branding": {
            "channel": "@yanv_tg",
            "channel_link": "https://t.me/yanv_tg",
            "contact": "@yanvtg",
            "contact_link": "https://t.me/yanvtg",
            "tagline": "Чек-лист аудита и юридической защиты сайтов в РФ на 2026 год"
        }
    }
