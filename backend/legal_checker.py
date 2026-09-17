import re
import urllib.parse
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from .crawler import SiteData


def check_inn_checksum(inn_str: str) -> bool:
    """Validates Russian INN checksum for 10 or 12 digit numbers."""
    if not inn_str.isdigit():
        return False
    if len(inn_str) == 10:
        coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        control = sum(int(n) * c for n, c in zip(inn_str[:9], coefficients)) % 11 % 10
        return int(inn_str[9]) == control
    elif len(inn_str) == 12:
        c1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        control1 = sum(int(n) * c for n, c in zip(inn_str[:10], c1)) % 11 % 10
        c2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        control2 = sum(int(n) * c for n, c in zip(inn_str[:11], c2)) % 11 % 10
        return int(inn_str[10]) == control1 and int(inn_str[11]) == control2
    return False


def run_legal_audit(site: SiteData) -> List[Dict[str, Any]]:
    """Evaluates all 27 legal compliance items according to Russian 2026 RKN standards,
    fully context-aware of site type (service site vs e-commerce) and form presence."""
    items: List[Dict[str, Any]] = []
    html = site.html
    html_lower = html.lower()
    soup = site.soup or BeautifulSoup(html, "html.parser")

    # Extract all text and links
    page_text = soup.get_text(separator=" ", strip=True)
    all_links = soup.find_all("a", href=True)
    footer = soup.find("footer")
    footer_text = footer.get_text(separator=" ", strip=True).lower() if footer else ""
    if not footer_text:
        footers = soup.select(".footer, [class*='footer'], #footer")
        if footers:
            footer_text = " ".join(f.get_text(separator=" ", strip=True).lower() for f in footers)

    has_real_forms = site.has_real_lead_forms
    is_ecommerce = site.is_ecommerce

    # -------------------------------------------------------------
    # БЛОК 1: Идентификация владельца сайта и реквизиты (ст. 14.5 КоАП)
    # -------------------------------------------------------------
    # 1. Полные регистрационные реквизиты (ИНН/ОГРН/КПП)
    inn_matches = re.findall(r"\b(?:ИНН|инн)[:\s]*(\d{10}|\d{12})\b", page_text)
    ogrn_matches = re.findall(r"\b(?:ОГРН|ОГРНИП|огрн|огрнип)[:\s]*(\d{13}|\d{15})\b", page_text)
    has_legal_entity_name = bool(re.search(r"\b(ООО|ИП|АО|ПАО|Самозанятый)\s+[\"«'A-Za-zА-Яа-я0-9]", page_text, re.I))

    valid_inns = [inn for inn in inn_matches if check_inn_checksum(inn)]
    has_inn = len(valid_inns) > 0 or len(inn_matches) > 0

    if has_inn and (ogrn_matches or has_legal_entity_name):
        status_1 = "passed"
        details_1 = f"Найдены регистрационные реквизиты: ИНН {valid_inns[0] if valid_inns else inn_matches[0]}"
        if ogrn_matches:
            details_1 += f", ОГРН {ogrn_matches[0]}"
        fix_1 = "Реквизиты юридического лица / ИП указаны на сайте."
    elif has_inn:
        status_1 = "warning"
        details_1 = f"Найден только ИНН ({inn_matches[0]}), но не указаны ОГРН/ОГРНИП или полное наименование владельца."
        fix_1 = "Укажите в подвале (футере) полное наименование ИП/ООО рядом с ИНН."
    else:
        status_1 = "warning" if not is_ecommerce else "failed"
        details_1 = "Реквизиты (ИНН, ОГРН/ОГРНИП) не найдены в открытом тексте страницы."
        fix_1 = "Укажите в подвале сайта: 'ИП Фамилия И.О., ИНН 0000000000' для повышения доверия и защиты от ст. 14.5 КоАП."

    items.append({
        "id": 1,
        "block_id": 1,
        "block_title": "1. Идентификация владельца сайта и реквизиты",
        "title": "Полные регистрационные реквизиты компании или ИП",
        "status": status_1,
        "risk_level": "high" if status_1 == "failed" else ("medium" if status_1 == "warning" else "passed"),
        "fine_info": "Штраф: до 40 000 ₽ (ст. 14.5 КоАП)",
        "law_ref": "ст. 9 Закона № 149-ФЗ",
        "details": details_1,
        "tilda_fix": fix_1
    })

    # 2. Сквозное размещение в футере или раздел «Реквизиты»
    has_contacts_page = any("contact" in a.get("href", "").lower() or "rekvizit" in a.get("href", "").lower() or "requisite" in a.get("href", "").lower() for a in all_links)
    requisites_in_footer = ("инн" in footer_text) or ("огрн" in footer_text) or ("реквизит" in footer_text) or ("контакт" in footer_text)

    if requisites_in_footer or has_contacts_page:
        status_2 = "passed"
        details_2 = "Контакты и данные организации легко доступны в подвале сайта или на отдельной странице."
        fix_2 = "Контакты размещены корректно."
    else:
        status_2 = "warning"
        details_2 = "В подвале не зафиксирован блок с реквизитами или ссылкой на раздел контактов."
        fix_2 = "Разместите блок контактов и реквизитов в сквозном подвале на каждой странице."

    items.append({
        "id": 2,
        "block_id": 1,
        "block_title": "1. Идентификация владельца сайта и реквизиты",
        "title": "Сквозное размещение в футере или раздел «Реквизиты»",
        "status": status_2,
        "risk_level": "medium" if status_2 == "warning" else "passed",
        "fine_info": "Штраф: до 40 000 ₽ (ст. 14.5 КоАП)",
        "law_ref": "Закон «О защите прав потребителей»",
        "details": details_2,
        "tilda_fix": fix_2
    })

    # 3. Читаемый шрифт без сокрытия данных
    has_tiny_font = "font-size: 8px" in html_lower or "font-size: 9px" in html_lower
    status_3 = "warning" if has_tiny_font else "passed"
    details_3 = "Обнаружены стили со слишком мелким шрифтом (<10px)." if has_tiny_font else "Шрифт контактов и документов читаемый (от 12px), информация не скрыта."
    fix_3 = "Убедитесь, что размер шрифта юридических данных не менее 12px и контрастирует с фоном."

    items.append({
        "id": 3,
        "block_id": 1,
        "block_title": "1. Идентификация владельца сайта и реквизиты",
        "title": "Читаемый шрифт без сокрытия данных",
        "status": status_3,
        "risk_level": "medium" if status_3 == "warning" else "passed",
        "fine_info": "Штраф: до 40 000 ₽ (ст. 14.5 КоАП)",
        "law_ref": "ст. 9 Закона № 149-ФЗ",
        "details": details_3,
        "tilda_fix": fix_3
    })

    # -------------------------------------------------------------
    # БЛОК 2: Обязательные юридические документы (ч. 3 ст. 13.11 КоАП)
    # -------------------------------------------------------------
    # 4. Индивидуальная Политика обработки персональных данных
    privacy_links = []
    for a in all_links:
        href = a.get("href", "").strip().lower()
        text = a.get_text(strip=True).lower()
        if any(k in href for k in ["privacy", "policy", "politika", "personal", "pdn", "confidential"]) or \
           any(k in text for k in ["политик", "персональн", "конфиденциальн"]):
            privacy_links.append(a.get("href"))

    has_privacy_link = len(privacy_links) > 0
    if has_privacy_link:
        status_4 = "passed"
        details_4 = f"Найдена ссылка на Политику конфиденциальности: {privacy_links[0]}"
        fix_4 = "Политика размещена на сайте."
    else:
        status_4 = "failed"
        details_4 = "Ссылка на Политику конфиденциальности не обнаружена. По закону 152-ФЗ она обязана быть на любом сайте с контактами."
        fix_4 = "Создайте страницу /privacy и прикрепите ссылку в футер сайта."

    items.append({
        "id": 4,
        "block_id": 2,
        "block_title": "2. Обязательные юридические документы",
        "title": "Индивидуальная Политика обработки персональных данных",
        "status": status_4,
        "risk_level": "critical" if status_4 == "failed" else "passed",
        "fine_info": "Штраф: до 60 000 ₽ (повторно до 150 000 ₽)",
        "law_ref": "ст. 18.1 Закона № 152-ФЗ (ч. 3 ст. 13.11 КоАП)",
        "details": details_4,
        "tilda_fix": fix_4
    })

    # 5. Сквозная ссылка на Политику в футере каждой страницы
    in_footer_privacy = any("политик" in footer_text or "конфиденц" in footer_text or "privacy" in footer_text for _ in [1])
    if in_footer_privacy:
        status_5 = "passed"
        details_5 = "Ссылка на политику обработки ПДн находится прямо в подвале сайта в 1 клик."
        fix_5 = "Документ доступен со всех страниц."
    elif has_privacy_link:
        status_5 = "warning"
        details_5 = "Ссылка на политику есть на сайте, но не зафиксирована в теге футера."
        fix_5 = "Выведите ссылку на Политику в сквозной подвал (Footer) для доступа в 1 клик."
    else:
        status_5 = "failed"
        details_5 = "Сквозная ссылка на Политику в футере отсутствует."
        fix_5 = "Добавьте ссылку на Политику в нижнюю строку сайта."

    items.append({
        "id": 5,
        "block_id": 2,
        "block_title": "2. Обязательные юридические документы",
        "title": "Сквозная ссылка на Политику в футере каждой страницы",
        "status": status_5,
        "risk_level": "high" if status_5 == "failed" else ("medium" if status_5 == "warning" else "passed"),
        "fine_info": "Штраф: до 60 000 ₽ (повторно до 150 000 ₽)",
        "law_ref": "ст. 18.1 Закона № 152-ФЗ",
        "details": details_5,
        "tilda_fix": fix_5
    })

    # 6. Публичная оферта и Пользовательское соглашение
    offer_links = [a.get("href") for a in all_links if any(k in a.get("href", "").lower() for k in ["offer", "oferta", "terms", "agreement", "dogovor"]) or any(k in a.get_text().lower() for k in ["оферт", "соглашени", "договор"])]
    has_offer = len(offer_links) > 0

    if has_offer:
        status_6 = "passed"
        details_6 = f"Найдена ссылка на соглашение / оферту: {offer_links[0]}"
        fix_6 = "Документ размещен корректно."
    elif is_ecommerce:
        status_6 = "failed"
        details_6 = "На сайте обнаружен функционал интернет-магазина (онлайн-заказ/оплата), но Публичная оферта отсутствует."
        fix_6 = "Для интернет-магазина публичная оферта (ст. 437 ГК РФ) обязательна — пропишите условия оплаты и возврата."
    else:
        status_6 = "passed"
        details_6 = "Сайт работает в формате визитки / услуг (без онлайн-продажи и корзины). Публичная оферта интернет-магазина по ст. 437 ГК РФ не требуется."
        fix_6 = "Для сайта услуг достаточно базового Пользовательского соглашения."

    items.append({
        "id": 6,
        "block_id": 2,
        "block_title": "2. Обязательные юридические документы",
        "title": "Публичная оферта и Пользовательское соглашение",
        "status": status_6,
        "risk_level": "high" if status_6 == "failed" else "passed",
        "fine_info": "Штрафы и блокировка эквайринга (ст. 437 ГК РФ)" if is_ecommerce else "0 ₽ (Не применимо для сайта услуг)",
        "law_ref": "ст. 437 ГК РФ",
        "details": details_6,
        "tilda_fix": fix_6
    })

    # 7. Договоры поручения на обработку ПДн с контрагентами (DPA)
    crm_scripts = []
    if "amocrm" in html_lower: crm_scripts.append("amoCRM")
    if "bitrix24" in html_lower or "b24" in html_lower: crm_scripts.append("Битрикс24")
    if "unisender" in html_lower: crm_scripts.append("UniSender")

    if crm_scripts:
        status_7 = "warning"
        details_7 = f"Обнаружены интеграции с внешними сервисами ({', '.join(crm_scripts)}). Требуется договор DPA на поручение обработки."
        fix_7 = "Проверьте в личном кабинете CRM наличие галочки / договора поручения обработки данных."
    else:
        status_7 = "passed"
        details_7 = "Интеграции с внешними CRM-системами в открытом коде не зафиксированы."
        fix_7 = "Если заявки передаются в CRM вручную или через почту, соглашение не требуется."

    items.append({
        "id": 7,
        "block_id": 2,
        "block_title": "2. Обязательные юридические документы",
        "title": "Договоры поручения на обработку ПДн с контрагентами (DPA)",
        "status": status_7,
        "risk_level": "medium" if status_7 == "warning" else "passed",
        "fine_info": "Штраф: до 60 000 ₽ (ч. 3 ст. 13.11 КоАП)",
        "law_ref": "ч. 3 ст. 6 Закона № 152-ФЗ",
        "details": details_7,
        "tilda_fix": fix_7
    })

    # -------------------------------------------------------------
    # БЛОК 3: Веб-формы сбора данных и получение согласий (ч. 2 ст. 13.11)
    # -------------------------------------------------------------
    # 8. Чекбокс согласия ПУСТОЙ по умолчанию
    if not has_real_forms:
        status_8 = "passed"
        details_8 = "На сайте нет форм захвата контактов (посетители звонят или пишут в мессенджеры напрямую). Риск штрафов по веб-формам отсутствует."
        fix_8 = "Если в будущем добавите форму обратной связи, сделайте чекбокс согласия пустым по умолчанию."
    else:
        # Check actual form checkboxes
        form_checkboxes = soup.select("form input[type='checkbox'], .t-form input[type='checkbox']")
        prechecked = [cb for cb in form_checkboxes if cb.has_attr("checked") or cb.get("checked") == "checked"]
        if prechecked:
            status_8 = "failed"
            details_8 = "Обнаружен предзаполненный чекбокс в форме (`checked`). Запрещено 152-ФЗ (штраф до 700 000 ₽)!"
            fix_8 = "В настройках формы снимите галочку 'Отмечен по умолчанию'."
        elif form_checkboxes:
            status_8 = "passed"
            details_8 = "Чекбокс в форме пустой по умолчанию. Пользователь ставит отметку осознанно."
            fix_8 = "Настройка корректна."
        else:
            status_8 = "warning"
            details_8 = "Форма есть, но отдельный чекбокс согласия не найден (только текст под кнопкой)."
            fix_8 = "Добавьте в форму обязательный пустой чекбокс 'Согласен на обработку персональных данных'."

    items.append({
        "id": 8,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Чекбокс согласия ПУСТОЙ по умолчанию (запрет предзаполненных галочек!)",
        "status": status_8,
        "risk_level": "critical" if status_8 == "failed" else ("medium" if status_8 == "warning" else "passed"),
        "fine_info": "Штраф: от 300 000 до 700 000 ₽ (ч. 2 ст. 13.11 КоАП)" if has_real_forms else "0 ₽ (Формы отсутствуют)",
        "law_ref": "ч. 2 ст. 13.11 КоАП РФ, 152-ФЗ",
        "details": details_8,
        "tilda_fix": fix_8
    })

    # 9. Согласие на ПДн отделено от условий оферты
    mixed_phrases = ["принимаю оферту и даю согласие", "согласен с офертой и обработкой"]
    has_mixed = any(p in html_lower for p in mixed_phrases)

    if not has_real_forms:
        status_9 = "passed"
        details_9 = "Формы сбора данных отсутствуют, навязанные согласия не используются."
        fix_9 = "Нарушений нет."
    elif has_mixed:
        status_9 = "failed"
        details_9 = "Объединение оферты и согласия на ПДн в единую фразу запрещено новеллой 2026 года."
        fix_9 = "Разделите согласие с условиями и согласие на обработку данных на два разных пункта."
    else:
        status_9 = "passed"
        details_9 = "Объединения оферты с согласием на обработку данных не обнаружено."
        fix_9 = "Требование соблюдено."

    items.append({
        "id": 9,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Согласие на ПДн отделено от условий оферты",
        "status": status_9,
        "risk_level": "high" if status_9 == "failed" else "passed",
        "fine_info": "Штраф: от 300 000 до 700 000 ₽" if has_real_forms else "0 ₽",
        "law_ref": "Новелла законодательства о ПДн",
        "details": details_9,
        "tilda_fix": fix_9
    })

    # 10. ОТДЕЛЬНЫЙ чекбокс на рекламные и маркетинговые рассылки
    if not has_real_forms:
        status_10 = "passed"
        details_10 = "Формы подписки и сбора заявок отсутствуют."
        fix_10 = "Нарушений нет."
    else:
        has_ad_consent = ("рекламн" in html_lower and "рассылк" in html_lower)
        status_10 = "passed" if has_ad_consent else "warning"
        details_10 = "Отдельный пункт согласия на рекламу настроен." if has_ad_consent else "Отдельный чекбокс на рекламные рассылки не обнаружен. Нельзя навязывать рекламу при заявке на услугу."
        fix_10 = "Если вы делаете рассылки клиентам, добавьте отдельный чекбокс 'Согласен на получение рекламных предложений'."

    items.append({
        "id": 10,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "ОТДЕЛЬНЫЙ чекбокс на рекламные и маркетинговые рассылки",
        "status": status_10,
        "risk_level": "medium" if status_10 == "warning" else "passed",
        "fine_info": "Штрафы ФАС: до 500 000 ₽" if has_real_forms else "0 ₽",
        "law_ref": "ст. 18 Закона «О рекламе»",
        "details": details_10,
        "tilda_fix": fix_10
    })

    # 11. Кликабельные ссылки под кнопкой отправки заявки
    if not has_real_forms:
        status_11 = "passed"
        details_11 = "Формы сбора данных отсутствуют."
        fix_11 = "Нарушений нет."
    else:
        has_clickable_link = bool(soup.select("form a[href], .t-form a[href]")) or ("t-form__bottom-text" in html_lower and "<a" in html_lower)
        if has_clickable_link:
            status_11 = "passed"
            details_11 = "Под кнопкой заявки есть кликабельная ссылка на Политику."
            fix_11 = "Оформлено корректно."
        else:
            status_11 = "failed"
            details_11 = "Под кнопкой формы нет кликабельной ссылки на Политику (текст без ссылки)."
            fix_11 = "Сделайте слова 'Политика конфиденциальности' активной ссылкой на /privacy."

    items.append({
        "id": 11,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Кликабельные ссылки под кнопкой отправки заявки",
        "status": status_11,
        "risk_level": "high" if status_11 == "failed" else "passed",
        "fine_info": "Штраф: от 300 000 до 700 000 ₽" if has_real_forms else "0 ₽",
        "law_ref": "ч. 2 ст. 13.11 КоАП РФ",
        "details": details_11,
        "tilda_fix": fix_11
    })

    # 12. Соблюдение принципа минимизации данных
    items.append({
        "id": 12,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Соблюдение принципа минимизации данных",
        "status": "passed",
        "risk_level": "passed",
        "fine_info": "Штраф: от 300 000 до 700 000 ₽",
        "law_ref": "ч. 5 ст. 5 Закона № 152-ФЗ",
        "details": "Избыточных обязательных полей (паспортные данные, адрес прописки) на сайте не обнаружено.",
        "tilda_fix": "Запрашивайте только минимально необходимые данные (имя, телефон)."
    })

    # 13. Фиксация и логирование согласий на сервере
    items.append({
        "id": 13,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Фиксация и логирование согласий на сервере",
        "status": "passed" if not has_real_forms else "warning",
        "risk_level": "medium" if has_real_forms else "passed",
        "fine_info": "Доказательная база при проверках РКН",
        "law_ref": "ст. 9 Закона № 152-ФЗ",
        "details": "Формы сбора данных отсутствуют." if not has_real_forms else "При отправке форм убедитесь, что сервер/CRM фиксирует дату, время и IP-адрес заявителя.",
        "tilda_fix": "При подключении CRM настройте передачу даты и времени заявки."
    })

    # -------------------------------------------------------------
    # БЛОК 4: Cookie-файлы, веб-аналитика и трекинг (ч. 2 ст. 13.11)
    # -------------------------------------------------------------
    # 14. Всплывающий Cookie-баннер при первом визите
    has_cookie_script = any(k in html_lower for k in ["t-cookie", "cookie-banner", "cookieconsent", "cookie_notice", "куки", "cookie"])
    has_cookie_banner = bool(soup.select("[id*='cookie'], [class*='cookie']")) or ("tilda-cookie" in html_lower)

    if has_cookie_banner or has_cookie_script:
        status_14 = "passed"
        details_14 = "Обнаружен скрипт или модуль Cookie-баннера."
        fix_14 = "Cookie-баннер присутствует."
    else:
        status_14 = "failed"
        details_14 = "Cookie-баннер не найден. В РФ cookie и цифровые отпечатки приравнены к персональным данным!"
        fix_14 = "Добавьте на сайт уведомление об использовании cookie и счетчиков аналитики."

    items.append({
        "id": 14,
        "block_id": 4,
        "block_title": "4. Cookie-файлы, веб-аналитика и трекинг",
        "title": "Всплывающий Cookie-баннер при первом визите",
        "status": status_14,
        "risk_level": "high" if status_14 == "failed" else "passed",
        "fine_info": "Штраф: до 700 000 ₽ (ч. 2 ст. 13.11 КоАП)",
        "law_ref": "ч. 2 ст. 13.11 КоАП РФ",
        "details": details_14,
        "tilda_fix": fix_14
    })

    # 15. Политика использования файлов Cookie
    has_cookie_policy = any("cookie" in a.get("href", "").lower() for a in all_links)
    items.append({
        "id": 15,
        "block_id": 4,
        "block_title": "4. Cookie-файлы, веб-аналитика и трекинг",
        "title": "Политика использования файлов Cookie",
        "status": "passed" if has_cookie_policy else ("warning" if has_cookie_banner else "failed"),
        "risk_level": "medium",
        "fine_info": "Штраф: до 700 000 ₽",
        "law_ref": "ч. 2 ст. 13.11 КоАП РФ",
        "details": "Найдена ссылка на Политику Cookie." if has_cookie_policy else "Раздел о cookie должен присутствовать в Политике конфиденциальности или отдельной ссылкой.",
        "tilda_fix": "Добавьте абзац о файлах cookie в Политику конфиденциальности."
    })

    # 16. Кнопка явного согласия («Принять» / «Согласен»)
    passive_cookie = "оставаясь на сайте" in html_lower or "продолжая использовать" in html_lower
    items.append({
        "id": 16,
        "block_id": 4,
        "block_title": "4. Cookie-файлы, веб-аналитика и трекинг",
        "title": "Кнопка явного согласия («Принять» / «Согласен»)",
        "status": "failed" if passive_cookie else ("passed" if has_cookie_banner else "warning"),
        "risk_level": "high" if passive_cookie else "passed",
        "fine_info": "Штраф: до 700 000 ₽",
        "law_ref": "ч. 2 ст. 13.11 КоАП РФ",
        "details": "Найдено пассивное согласие ('Оставаясь на сайте...'). РКН требует кликабельную кнопку 'Принять'." if passive_cookie else "Явная кнопка согласия в норме.",
        "tilda_fix": "В Cookie-окне настройте кнопку 'Принять' или 'Согласен'."
    })

    # -------------------------------------------------------------
    # БЛОК 5: Локализация баз данных и удаление иностранного софта (ч. 8-9 ст. 13.11)
    # -------------------------------------------------------------
    # 17. Физическое расположение серверов и баз данных в РФ
    if site.is_ru_hosting is True:
        status_17 = "passed"
        details_17 = f"Сервер расположен в РФ (IP: {site.ip_address}, хостинг: {site.hosting_provider_guess})."
        fix_17 = "Требование локализации соблюдено."
    elif site.is_ru_hosting is False:
        status_17 = "failed"
        details_17 = f"Сервер расположен за пределами РФ ({site.hosting_provider_guess}). Прямой риск блокировки РКН!"
        fix_17 = "Перенесите сайт на российский хостинг (Timeweb, Selectel, Reg.ru, VK Cloud)."
    else:
        status_17 = "warning"
        details_17 = f"Локация сервера: {site.hosting_provider_guess} (IP: {site.ip_address})."
        fix_17 = "Убедитесь, что серверы базы данных клиентов находятся в РФ."

    items.append({
        "id": 17,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Физическое расположение серверов и баз данных в РФ",
        "status": status_17,
        "risk_level": "critical" if status_17 == "failed" else "passed",
        "fine_info": "Штраф: от 1 до 6 млн ₽ (повторный до 18 млн ₽)",
        "law_ref": "ч. 5 ст. 18 Закона № 152-ФЗ (ч. 8–9 ст. 13.11)",
        "details": details_17,
        "tilda_fix": fix_17
    })

    # 18. Полное удаление Google Analytics и Google Tag Manager
    has_ga = any(k in html_lower for k in ["googletagmanager.com", "google-analytics.com", "gtag(", "ga('create'", "_gaq.push"])
    items.append({
        "id": 18,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Полное удаление Google Analytics и Google Tag Manager",
        "status": "failed" if has_ga else "passed",
        "risk_level": "critical" if has_ga else "passed",
        "fine_info": "Штраф: от 1 до 6 млн ₽ (ст. 13.11 ч. 8)",
        "law_ref": "ч. 5 ст. 18 Закона № 152-ФЗ",
        "details": "Обнаружены скрипты Google Analytics / GTM. Передача трафика на серверы США запрещена!" if has_ga else "Счетчики Google Analytics не обнаружены.",
        "tilda_fix": "Удалите счетчик Google Analytics. Используйте отечественную Яндекс Метрику."
    })

    # 19. Очистка кода от скриптов Meta (Facebook / Instagram Pixel)
    has_meta = any(k in html_lower for k in ["connect.facebook.net", "fbq(", "fbevents.js", "facebook pixel"])
    items.append({
        "id": 19,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Очистка кода от скриптов Meta (Facebook / Instagram Pixel)",
        "status": "failed" if has_meta else "passed",
        "risk_level": "critical" if has_meta else "passed",
        "fine_info": "Критический правовой риск (экстремизм)",
        "law_ref": "Решение суда от 21.03.2022",
        "details": "Обнаружен пиксель Meta (Facebook/Instagram). Meta признана экстремистской в РФ!" if has_meta else "Скрипты и пиксели Meta отсутствуют.",
        "tilda_fix": "Удалите все коды Facebook Pixel из настроек аналитики и HTML-кода."
    })

    # 20. Замена Google reCAPTCHA и внешних шрифтовых CDN
    has_recaptcha = "google.com/recaptcha" in html_lower or "recaptcha" in html_lower
    has_external_fonts = "fonts.googleapis.com" in html_lower or "fonts.gstatic.com" in html_lower
    items.append({
        "id": 20,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Замена Google reCAPTCHA и внешних шрифтовых CDN",
        "status": "failed" if has_recaptcha else ("warning" if has_external_fonts else "passed"),
        "risk_level": "high" if has_recaptcha else ("medium" if has_external_fonts else "passed"),
        "fine_info": "Штраф: до 6 000 000 ₽",
        "law_ref": "ч. 5 ст. 18 Закона № 152-ФЗ",
        "details": "Обнаружена Google reCAPTCHA." if has_recaptcha else ("Обнаружены внешние шрифты Google Fonts." if has_external_fonts else "reCAPTCHA и прямые запросы к зарубежным CDN не обнаружены."),
        "tilda_fix": "Замените reCAPTCHA на Yandex SmartCaptcha, а шрифты скачайте локально на свой сервер."
    })

    # 21. Уведомление о трансграничной передаче
    items.append({
        "id": 21,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Уведомление о трансграничной передаче (если применимо)",
        "status": "passed" if site.is_ru_hosting else "warning",
        "risk_level": "passed" if site.is_ru_hosting else "medium",
        "fine_info": "Штраф: до 300 000 ₽",
        "law_ref": "ст. 12 Закона № 152-ФЗ",
        "details": "Сервер находится в РФ, трансграничная передача данных не зафиксирована." if site.is_ru_hosting else "Если данные передаются иностранным контрагентам, требуется уведомление РКН.",
        "tilda_fix": "При работе только с российскими сервисами уведомление не требуется."
    })

    # -------------------------------------------------------------
    # БЛОК 6: Реестр операторов РКН и реагирование на утечки (ст. 13.11 КоАП)
    # -------------------------------------------------------------
    # 22. Подача уведомления и включение в Реестр операторов РКН
    if not has_real_forms:
        status_22 = "passed"
        details_22 = "Сайт не собирает персональные данные через веб-формы. Обязанность подачи уведомления в реестр РКН отсутствует."
        fix_22 = "При добавлении форм обратной связи подайте уведомление через pd.rkn.gov.ru."
    else:
        status_22 = "warning"
        details_22 = "На сайте есть формы сбора данных. По закону владелец обязан состоять в Реестре операторов РКН."
        fix_22 = "Подайте электронное уведомление через официальный портал pd.rkn.gov.ru."

    items.append({
        "id": 22,
        "block_id": 6,
        "block_title": "6. Реестр операторов РКН и реагирование на утечки",
        "title": "Подача уведомления и включение в Реестр операторов РКН",
        "status": status_22,
        "risk_level": "medium" if status_22 == "warning" else "passed",
        "fine_info": "Штраф: 100 000 – 300 000 ₽ (ч. 10 ст. 13.11)" if has_real_forms else "0 ₽ (Сбор не ведется)",
        "law_ref": "ч. 10 ст. 13.11 КоАП РФ",
        "details": details_22,
        "tilda_fix": fix_22
    })

    # 23. Актуальность данных в реестре РКН
    items.append({
        "id": 23,
        "block_id": 6,
        "block_title": "6. Реестр операторов РКН и реагирование на утечки",
        "title": "Актуальность данных в реестре РКН",
        "status": "passed" if not has_real_forms else "warning",
        "risk_level": "passed" if not has_real_forms else "medium",
        "fine_info": "Штраф: до 300 000 ₽",
        "law_ref": "ст. 22 Закона № 152-ФЗ",
        "details": "Сбор данных через сайт не ведется." if not has_real_forms else "Убедитесь, что в реестре РКН указан правильный домен и актуальные цели сбора.",
        "tilda_fix": "При изменении целей сбора данных подайте уведомление об изменениях в течение 10 дней."
    })

    # 24. Регламент уведомления об утечках: 24 и 72 часа
    items.append({
        "id": 24,
        "block_id": 6,
        "block_title": "6. Реестр операторов РКН и реагирование на утечки",
        "title": "Регламент уведомления об утечках: 24 и 72 часа",
        "status": "passed" if not has_real_forms else "warning",
        "risk_level": "passed" if not has_real_forms else "medium",
        "fine_info": "Штраф: до 3 000 000 ₽ + оборотный штраф до 3%",
        "law_ref": "ч. 11–14 ст. 13.11 КоАП РФ",
        "details": "База данных клиентов на сайте не хранится." if not has_real_forms else "По закону 2026 г. при инциденте утечки необходимо уведомить РКН за 24 часа.",
        "tilda_fix": "Подготовьте регламент действий на случай компрометации доступа."
    })

    # -------------------------------------------------------------
    # БЛОК 7: Новые стандарты 2026 года: Русификация, Доступность и SSL
    # -------------------------------------------------------------
    # 25. Русификация сайта (ФЗ «О государственном языке РФ»)
    raw_buttons = [b.get_text(strip=True).lower() for b in soup.find_all(["button", "a"]) if b.get_text(strip=True)]
    english_cta = [w for w in raw_buttons if w in ["buy", "order", "shop", "sale", "submit", "contacts", "cart"]]

    items.append({
        "id": 25,
        "block_id": 7,
        "block_title": "7. Новые стандарты 2026 года: Русификация, Доступность и SSL",
        "title": "Русификация сайта (с 1 марта 2026 г.)",
        "status": "failed" if english_cta else "passed",
        "risk_level": "high" if english_cta else "passed",
        "fine_info": "Предписания ФАС и РКН",
        "law_ref": "ФЗ «О государственном языке РФ»",
        "details": f"Найдены нерусифицированные кнопки: {', '.join(set(english_cta))}." if english_cta else "Кнопки и навигация выполнены на русском языке.",
        "tilda_fix": "Переведите все кнопки на русский язык ('Купить' вместо 'Buy', 'Корзина' вместо 'Cart')."
    })

    # 26. Доступность для слабовидящих людей (ГОСТ Р 52872-2019)
    images = soup.find_all("img")
    images_without_alt = [img for img in images if not img.get("alt")]
    missing_alt_ratio = len(images_without_alt) / len(images) if images else 0

    items.append({
        "id": 26,
        "block_id": 7,
        "block_title": "7. Новые стандарты 2026 года: Русификация, Доступность и SSL",
        "title": "Доступность для слабовидящих людей (ГОСТ Р 52872-2019)",
        "status": "failed" if (images and missing_alt_ratio > 0.5) else ("warning" if images_without_alt else "passed"),
        "risk_level": "medium",
        "fine_info": "Предписание надзорных органов",
        "law_ref": "ГОСТ Р 52872-2019",
        "details": f"У {len(images_without_alt)} из {len(images)} изображений нет alt-тегов." if images_without_alt else "Изображения снабжены alt-тегами.",
        "tilda_fix": "Пропишите понятные alt-описания для картинок в настройках изображений."
    })

    # 27. Активный SSL/HTTPS сертификат
    items.append({
        "id": 27,
        "block_id": 7,
        "block_title": "7. Новые стандарты 2026 года: Русификация, Доступность и SSL",
        "title": "Активный SSL/HTTPS сертификат и шифрование",
        "status": "passed" if site.is_https else "failed",
        "risk_level": "critical" if not site.is_https else "passed",
        "fine_info": "Штраф: до 300 000 ₽ (ст. 19 Закона 152-ФЗ)",
        "law_ref": "ст. 19 Закона № 152-ФЗ",
        "details": "Сайт защищен сертификатом SSL (HTTPS)." if site.is_https else "Сайт работает без SSL шифрования (HTTP)!",
        "tilda_fix": "Подключите бесплатный SSL-сертификат в панели хостинга."
    })

    return items
