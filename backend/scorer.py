from typing import Any, Dict, List
from .crawler import SiteData
from .legal_checker import run_legal_audit
from .marketing_checker import run_marketing_audit


def compile_full_audit(site: SiteData) -> Dict[str, Any]:
    """Compiles both legal and marketing audits into a unified, executive-level report."""
    legal_items = run_legal_audit(site)
    marketing = run_marketing_audit(site)

    total_legal = 27
    passed_legal = sum(1 for item in legal_items if item["status"] == "passed")
    failed_legal = sum(1 for item in legal_items if item["status"] == "failed")
    warning_legal = sum(1 for item in legal_items if item["status"] == "warning")
    legal_percent = int(round((passed_legal / total_legal) * 100))

    # Critical & high issues
    critical_items = [i for i in legal_items if i["status"] == "failed" and i.get("risk_level") == "critical"]
    high_items = [i for i in legal_items if i["status"] == "failed" and i.get("risk_level") == "high"]
    other_failed = [i for i in legal_items if i["status"] == "failed" and i not in critical_items and i not in high_items]

    all_failed_count = len(critical_items) + len(high_items) + len(other_failed)

    if critical_items:
        overall_risk = "Критический риск"
        risk_color = "#ef4444"
        verdict_badge = "Критические риски"
        verdict_title = f"Обнаружено {all_failed_count} нарушений законодательства"
    elif high_items or failed_legal >= 2:
        overall_risk = "Высокий риск"
        risk_color = "#f97316"
        verdict_badge = "Высокий риск"
        verdict_title = f"Обнаружено {all_failed_count} нарушений"
    elif failed_legal >= 1 or warning_legal > 4:
        overall_risk = "Умеренный риск"
        risk_color = "#eab308"
        verdict_badge = "Требует внимания"
        verdict_title = "Есть мелкие замечания"
    else:
        overall_risk = "Минимальный риск"
        risk_color = "#10b981"
        verdict_badge = "Всё чисто"
        verdict_title = "Сайт юридически безопасен"

    # Specific fine tags
    form_items = [i for i in legal_items if i["id"] in [8, 9, 11]]
    form_failed = any(i["status"] == "failed" for i in form_items)
    fine_form_text = "до 700 000 ₽" if form_failed else "0 ₽ (В норме)"

    loc_items = [i for i in legal_items if i["id"] in [17, 18, 19]]
    loc_failed = any(i["status"] == "failed" for i in loc_items)
    fine_loc_text = "до 18 000 000 ₽" if loc_failed else "0 ₽ (В норме)"

    # Short executive takeaways (до 4 главных пунктов простым языком)
    takeaways = []
    if not site.has_real_lead_forms:
        takeaways.append({
            "type": "positive",
            "text": "Формы захвата контактов отсутствуют (посетители звонят/пишут напрямую) — риски штрафов за формы и чекбоксы исключены."
        })
    elif form_failed:
        takeaways.append({
            "type": "negative",
            "text": "В веб-формах обнаружены нарушения (нет пустого чекбокса или активной ссылки на политику) — риск штрафа до 700 000 ₽."
        })

    if site.is_ru_hosting is True:
        takeaways.append({
            "type": "positive",
            "text": f"Сервер расположен в РФ ({site.hosting_provider_guess}) — закон о локализации баз данных соблюден."
        })
    elif site.is_ru_hosting is False:
        takeaways.append({
            "type": "negative",
            "text": f"Сервер находится за пределами РФ ({site.hosting_provider_guess}) — критический риск блокировки РКН."
        })

    privacy_item = next((i for i in legal_items if i["id"] == 4), None)
    if privacy_item and privacy_item["status"] == "failed":
        takeaways.append({
            "type": "negative",
            "text": "Не найдена Политика конфиденциальности — штраф до 60 000 ₽ (ст. 13.11 ч. 3 КоАП)."
        })

    ga_item = next((i for i in legal_items if i["id"] == 18), None)
    if ga_item and ga_item["status"] == "failed":
        takeaways.append({
            "type": "negative",
            "text": "Установлен счетчик Google Analytics — передача данных в США запрещена."
        })

    site_type_label = "Интернет-магазин (онлайн-оплата)" if site.is_ecommerce else "Сайт услуг / Визитка (прямая связь)"

    # Group legal items by blocks
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

    telegram_summary = (
        f"📋 Экспресс-Аудит сайта: {site.domain}\n"
        f"Тип: {site_type_label} | Платформа: {site.cms_platform}\n"
        f"Хостинг: {site.hosting_provider_guess} ({'РФ' if site.is_ru_hosting else 'Зарубеж'})\n\n"
        f"Юридическая готовность (2026 г.): {passed_legal} / {total_legal} ({legal_percent}%)\n"
        f"Вердикт: {overall_risk}\n"
        f"Штраф за формы: {fine_form_text}\n"
        f"Штраф за локализацию: {fine_loc_text}\n"
        f"Оценка конверсии: {marketing['score']}/100\n\n"
    )

    if critical_items or high_items:
        telegram_summary += "Ключевые риски:\n"
        for it in (critical_items + high_items)[:3]:
            telegram_summary += f"• {it['title']} ({it['fine_info']})\n"
        telegram_summary += "\n"

    telegram_summary += (
        "Канал Яна: @yanv_tg\n"
        "Связь и экспресс-аудит под ключ: @yanvtg"
    )

    return {
        "url": site.final_url or site.raw_url,
        "domain": site.domain,
        "cms_platform": site.cms_platform,
        "is_tilda": site.is_tilda,
        "site_type": site_type_label,
        "is_https": site.is_https,
        "response_time_ms": site.response_time_ms,
        "ip_address": site.ip_address,
        "hosting_provider": site.hosting_provider_guess,
        "is_ru_hosting": site.is_ru_hosting,
        "executive_summary": {
            "verdict_badge": verdict_badge,
            "verdict_title": verdict_title,
            "overall_risk": overall_risk,
            "risk_color": risk_color,
            "all_failed_count": all_failed_count,
            "warning_count": warning_legal,
            "takeaways": takeaways
        },
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
