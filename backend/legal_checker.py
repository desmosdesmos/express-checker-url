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
    """Evaluates all 27 legal compliance items according to Russian 2026 RKN standards."""
    items: List[Dict[str, Any]] = []
    html = site.html
    html_lower = html.lower()
    soup = site.soup or BeautifulSoup(html, "html.parser")

    # Extract all text and links
    page_text = soup.get_text(separator=" ", strip=True)
    all_links = soup.find_all("a", href=True)
    footer = soup.find("footer")
    footer_text = footer.get_text(separator=" ", strip=True).lower() if footer else ""
    if not footer_text and site.is_tilda:
        # In Tilda, footers are often in blocks with class t-footer or t-records last blocks
        t_footers = soup.select(".t-footer, [class*='footer'], #footer, #rec*")
        if t_footers:
            footer_text = " ".join(f.get_text(separator=" ", strip=True).lower() for f in t_footers[-3:])

    # Extract forms and inputs
    forms = soup.find_all("form")
    has_forms = len(forms) > 0 or ("t-form" in html_lower)

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
        fix_1 = "Реквизиты корректно указаны на сайте."
    elif has_inn:
        status_1 = "warning"
        details_1 = f"Найден только ИНН ({inn_matches[0]}), но не обнаружены ОГРН/ОГРНИП или полное юридическое наименование."
        fix_1 = "В Tilda укажите в подвале (футере) полное наименование юрлица/ИП, ОГРН/ОГРНИП рядом с ИНН."
    else:
        status_1 = "failed"
        details_1 = "Реквизиты (ИНН, ОГРН/ОГРНИП, данные юрлица/ИП) не найдены в коде страницы."
        fix_1 = "Укажите в подвале сайта: 'ИП Иванов И.И., ИНН 0000000000, ОГРНИП 0000000000000' или данные ООО."

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
    requisites_in_footer = ("инн" in footer_text) or ("огрн" in footer_text) or ("реквизит" in footer_text)

    if requisites_in_footer or has_contacts_page:
        status_2 = "passed"
        details_2 = "Реквизиты/контакты присутствуют в футере или доступна отдельная страница контактов/реквизитов."
        fix_2 = "Контакты и реквизиты легко доступны пользователям."
    else:
        status_2 = "failed"
        details_2 = "В футере нет блока с реквизитами и нет ссылки на страницу 'Реквизиты' / 'Контакты'."
        fix_2 = "В Tilda настройте сквозной подвал (Header and Footer) с разделом контактов и реквизитов на каждой странице."

    items.append({
        "id": 2,
        "block_id": 1,
        "block_title": "1. Идентификация владельца сайта и реквизиты",
        "title": "Сквозное размещение в футере или раздел «Реквизиты»",
        "status": status_2,
        "risk_level": "high" if status_2 == "failed" else "passed",
        "fine_info": "Штраф: до 40 000 ₽ (ст. 14.5 КоАП)",
        "law_ref": "Закон «О защите прав потребителей»",
        "details": details_2,
        "tilda_fix": fix_2
    })

    # 3. Читаемый шрифт без сокрытия данных
    # Check if text isn't hidden by display:none or microscopic font in css
    has_tiny_font = "font-size: 8px" in html_lower or "font-size: 9px" in html_lower or "font-size: 10px" in html_lower
    status_3 = "warning" if has_tiny_font else "passed"
    details_3 = "Обнаружены стили со слишком мелким шрифтом (<12px) в коде." if has_tiny_font else "Шрифт реквизитов и документов соответствует норме (от 12px), информация не скрыта."
    fix_3 = "Убедитесь, что размер шрифта юридических сносок не меньше 12px и контрастирует с фоном."

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
        fix_4 = "Убедитесь, что политика содержит 5 обязательных разделов: цели, категории ПДн, правовые основания, субъекты, сроки уничтожения."
    else:
        status_4 = "failed"
        details_4 = "Ссылка на Политику обработки персональных данных не обнаружена."
        fix_4 = "В Tilda создайте страницу /privacy и добавьте ссылку в подвал сайта и во все формы."

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
        details_5 = "Ссылка на политику обработки ПДн размещена в сквозном футере."
        fix_5 = "Политика доступна в 1 клик с любой страницы."
    elif has_privacy_link:
        status_5 = "warning"
        details_5 = "Ссылка на политику найдена на странице, но не зафиксирована в теге футера."
        fix_5 = "В Tilda добавьте прямую ссылку на /privacy в глобальный блок подвала (Footer)."
    else:
        status_5 = "failed"
        details_5 = "Сквозная ссылка на Политику в футере отсутствует."
        fix_5 = "Обязательно выведите ссылку на Политику в самый низ сайта в 1 клик."

    items.append({
        "id": 5,
        "block_id": 2,
        "block_title": "2. Обязательные юридические документы",
        "title": "Сквозная ссылка на Политику в футере каждой страницы",
        "status": status_5,
        "risk_level": "high" if status_5 == "failed" else ("medium" if status_5 == "warning" else "passed"),
        "fine_info": "Штраф: до 60 000 ₽ (повторный до 150 000 ₽)",
        "law_ref": "ст. 18.1 Закона № 152-ФЗ",
        "details": details_5,
        "tilda_fix": fix_5
    })

    # 6. Публичная оферта и Пользовательское соглашение
    offer_links = [a.get("href") for a in all_links if any(k in a.get("href", "").lower() for k in ["offer", "oferta", "terms", "agreement", "dogovor"]) or any(k in a.get_text().lower() for k in ["оферт", "соглашени", "договор"])]
    has_offer = len(offer_links) > 0
    # If commercial site (has cart or prices), offer is crucial
    has_shop = ("cart" in html_lower or "t-cart" in html_lower or "корзин" in page_text.lower() or "купить" in page_text.lower() or "оплат" in page_text.lower())
    
    if has_offer:
        status_6 = "passed"
        details_6 = f"Найдена оферта или пользовательское соглашение: {offer_links[0]}"
        fix_6 = "Документ размещен корректно."
    elif has_shop:
        status_6 = "failed"
        details_6 = "На сайте есть элементы онлайн-торговли/оплаты, но Публичная оферта не найдена."
        fix_6 = "Создайте страницу публичной оферты (ст. 437 ГК РФ) с условиями оплаты, возврата и доставки."
    else:
        status_6 = "warning"
        details_6 = "Публичная оферта не найдена. Если вы продаете услуги/товары, оферта обязательна."
        fix_6 = "Для сайта услуг или курсов создайте страницу оферты с реквизитами и порядком оказания услуг."

    items.append({
        "id": 6,
        "block_id": 2,
        "block_title": "2. Обязательные юридические документы",
        "title": "Публичная оферта и Пользовательское соглашение",
        "status": status_6,
        "risk_level": "high" if status_6 == "failed" else ("medium" if status_6 == "warning" else "passed"),
        "fine_info": "Штрафы и блокировка эквайринга (ст. 437 ГК РФ)",
        "law_ref": "ст. 437 ГК РФ, Закон о защите прав потребителей",
        "details": details_6,
        "tilda_fix": fix_6
    })

    # 7. Договоры поручения на обработку ПДн с контрагентами (DPA)
    crm_scripts = []
    if "amocrm" in html_lower: crm_scripts.append("amoCRM")
    if "bitrix24" in html_lower or "b24" in html_lower: crm_scripts.append("Битрикс24")
    if "unisender" in html_lower: crm_scripts.append("UniSender")
    if "mindbox" in html_lower: crm_scripts.append("Mindbox")

    if crm_scripts:
        status_7 = "warning"
        details_7 = f"Обнаружены интеграции с внешними сервисами: {', '.join(crm_scripts)}. Требуется подписанный договор DPA."
        fix_7 = "Проверьте в личном кабинете сервисов наличие соглашения о поручении обработки персональных данных (DPA)."
    else:
        status_7 = "passed"
        details_7 = "Скрипты сторонних CRM/рассыльщиков на главной странице не найдены."
        fix_7 = "Если заявки из Tilda уходят в CRM, убедитесь, что заключен договор поручения обработки."

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
    # 8. Чекбокс согласия ПУСТОЙ по умолчанию (запрет предзаполненных галочек!)
    prechecked_boxes = []
    has_checkboxes = False
    all_checkbox_inputs = soup.find_all("input", {"type": "checkbox"})
    if all_checkbox_inputs:
        has_checkboxes = True
        for cb in all_checkbox_inputs:
            if cb.has_attr("checked") or cb.get("checked") == "checked":
                prechecked_boxes.append(cb)

    if prechecked_boxes:
        status_8 = "failed"
        details_8 = f"Обнаружено {len(prechecked_boxes)} предзаполненных чекбоксов (`checked`). Главная мишень ботов РКН!"
        fix_8 = "В Tilda в настройках формы (Блок формы -> Поля для ввода) снимите отметку 'Отмечен по умолчанию'."
    elif has_checkboxes:
        status_8 = "passed"
        details_8 = "Чекбоксы найдены и они не отмечены по умолчанию. Пользователь ставит галочку лично."
        fix_8 = "Настройка чекбоксов корректна."
    elif has_forms:
        status_8 = "warning"
        details_8 = "На сайте есть форма сбора данных, но отдельный явный тег чекбокса не обнаружен."
        fix_8 = "В Tilda в настройках формы добавьте поле типа 'Галочка (Согласие)' без предзаполнения."
    else:
        status_8 = "passed"
        details_8 = "Формы сбора данных на главной странице отсутствуют."
        fix_8 = "При добавлении формы обязательно сделайте чекбокс пустым."

    items.append({
        "id": 8,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Чекбокс согласия ПУСТОЙ по умолчанию (запрет предзаполненных галочек!)",
        "status": status_8,
        "risk_level": "critical" if status_8 == "failed" else ("medium" if status_8 == "warning" else "passed"),
        "fine_info": "Штраф: от 300 000 до 700 000 ₽ (ч. 2 ст. 13.11 КоАП)",
        "law_ref": "ч. 2 ст. 13.11 КоАП РФ, 152-ФЗ",
        "details": details_8,
        "tilda_fix": fix_8
    })

    # 9. Согласие на ПДн отделено от условий оферты
    mixed_phrases = ["принимаю оферту и даю согласие", "согласен с офертой и обработкой", "принимаете оферту и соглашаетесь"]
    has_mixed_consent = any(p in html_lower for p in mixed_phrases)

    if has_mixed_consent:
        status_9 = "failed"
        details_9 = "Обнаружено объединение оферты и согласия на ПДн в одну фразу. Это прямое нарушение 2026 года!"
        fix_9 = "Разделите на 2 разных пункта: 1) Согласие с офертой; 2) Согласие на обработку ПДн."
    else:
        status_9 = "passed"
        details_9 = "Объединения согласия на ПДн с офертой в единую неразделимую фразу не обнаружено."
        fix_9 = "Все согласия должны быть разделены."

    items.append({
        "id": 9,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Согласие на ПДн отделено от условий оферты",
        "status": status_9,
        "risk_level": "high" if status_9 == "failed" else "passed",
        "fine_info": "Штраф: от 300 000 до 700 000 ₽",
        "law_ref": "Новелла законодательства о ПДн (ч. 2 ст. 13.11 КоАП)",
        "details": details_9,
        "tilda_fix": fix_9
    })

    # 10. ОТДЕЛЬНЫЙ чекбокс на рекламные и маркетинговые рассылки
    has_ad_consent = ("рекламн" in html_lower and "рассылк" in html_lower) or ("маркетинг" in html_lower and "соглас" in html_lower)
    status_10 = "passed" if has_ad_consent else ("warning" if has_forms else "passed")
    details_10 = "Найдены элементы раздельного согласия на рекламу." if has_ad_consent else "Отдельный чекбокс на получение рекламных рассылок не найден. Нельзя навязывать рекламу вместе с заявкой."
    fix_10 = "Если вы планируете звонить или отправлять рассылки, добавьте в Tilda второй отдельный чекбокс 'Согласен получать рассылку'."

    items.append({
        "id": 10,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "ОТДЕЛЬНЫЙ чекбокс на рекламные и маркетинговые рассылки",
        "status": status_10,
        "risk_level": "medium" if status_10 == "warning" else "passed",
        "fine_info": "Штрафы ФАС: до 500 000 ₽",
        "law_ref": "ст. 18 Закона «О рекламе»",
        "details": details_10,
        "tilda_fix": fix_10
    })

    # 11. Кликабельные ссылки под кнопкой отправки заявки
    has_clickable_form_link = False
    if has_forms:
        for f in forms:
            links_in_form = f.find_all("a", href=True)
            if links_in_form:
                has_clickable_form_link = True
                break
        if not has_clickable_form_link and "t-form" in html_lower:
            # Check Tilda form text
            if "t-form__bottom-text" in html_lower and "<a" in html_lower:
                has_clickable_form_link = True

    if has_clickable_form_link:
        status_11 = "passed"
        details_11 = "Под кнопками форм обнаружены кликабельные ссылки на соглашения/политику."
        fix_11 = "Формы оформлены корректно."
    elif has_forms:
        status_11 = "failed"
        details_11 = "В формах сбора заявок нет активных ссылок на Политику (текст без тегов <a>)."
        fix_11 = "В настройках блока Tilda в поле 'Подпись под формой' вставьте ссылку: 'Нажимая кнопку, соглашаюсь с <a href=\"/privacy\">Политикой</a>'."
    else:
        status_11 = "passed"
        details_11 = "Формы сбора данных отсутствуют."
        fix_11 = "При создании формы обязательно добавьте активную ссылку на Политику."

    items.append({
        "id": 11,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Кликабельные ссылки под кнопкой отправки заявки",
        "status": status_11,
        "risk_level": "high" if status_11 == "failed" else "passed",
        "fine_info": "Штраф: от 300 000 до 700 000 ₽",
        "law_ref": "ч. 2 ст. 13.11 КоАП РФ",
        "details": details_11,
        "tilda_fix": fix_11
    })

    # 12. Соблюдение принципа минимизации данных
    excessive_fields = []
    for inp in soup.find_all("input"):
        name_attr = (inp.get("name", "") + " " + inp.get("placeholder", "")).lower()
        if any(w in name_attr for w in ["паспорт", "passport", "адрес регистрации", "snils", "снилс"]):
            if inp.has_attr("required"):
                excessive_fields.append(name_attr)

    if excessive_fields:
        status_12 = "failed"
        details_12 = f"Найдены избыточные обязательные поля: {', '.join(excessive_fields)}. Нарушение принципа соразмерности."
        fix_12 = "Удалите обязательное требование паспортных данных или адреса, если это обычная заявка или лид-магнит."
    else:
        status_12 = "passed"
        details_12 = "Избыточных обязательных полей (паспорт, СНИЛС) в формах не обнаружено."
        fix_12 = "Принцип минимизации соблюдается."

    items.append({
        "id": 12,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Соблюдение принципа минимизации данных",
        "status": status_12,
        "risk_level": "high" if status_12 == "failed" else "passed",
        "fine_info": "Штраф: от 300 000 до 700 000 ₽",
        "law_ref": "ч. 5 ст. 5 Закона № 152-ФЗ",
        "details": details_12,
        "tilda_fix": fix_12
    })

    # 13. Фиксация и логирование согласий на сервере
    status_13 = "warning"
    details_13 = "Требуется проверка настроек CRM/сервера: сохраняется ли дата, точное время, IP-адрес заявителя и версия оферты."
    fix_13 = "В Tilda подключите вебхук или CRM, которая фиксирует дату, время и IP-адрес отправки заявки для доказательства в РКН."

    items.append({
        "id": 13,
        "block_id": 3,
        "block_title": "3. Веб-формы сбора данных и получение согласий",
        "title": "Фиксация и логирование согласий на сервере",
        "status": status_13,
        "risk_level": "medium",
        "fine_info": "Доказательная база при проверках РКН",
        "law_ref": "ст. 9 Закона № 152-ФЗ",
        "details": details_13,
        "tilda_fix": fix_13
    })

    # -------------------------------------------------------------
    # БЛОК 4: Cookie-файлы, веб-аналитика и трекинг (ч. 2 ст. 13.11)
    # -------------------------------------------------------------
    # 14. Всплывающий Cookie-баннер при первом визите
    has_cookie_script = any(k in html_lower for k in [
        "tilda-cookie", "t-cookie", "cookie-banner", "cookieconsent", "cookie_notice",
        "куки", "cookie", "cookies"
    ])
    has_cookie_banner = bool(soup.select("[id*='cookie'], [class*='cookie'], [class*='Cookie']")) or ("tilda-cookie" in html_lower)

    if has_cookie_banner or has_cookie_script:
        status_14 = "passed"
        details_14 = "Обнаружен скрипт или модуль Cookie-баннера на сайте."
        fix_14 = "Cookie-баннер настроен."
    else:
        status_14 = "failed"
        details_14 = "Cookie-баннер не найден. В РФ cookie и цифровые отпечатки приравнены к персональным данным!"
        fix_14 = "В Tilda добавьте стандартный блок Tilda T849 (Всплывающее окно согласия на использование файлов cookie)."

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
    has_cookie_policy = any("cookie" in a.get("href", "").lower() or "куки" in a.get_text().lower() for a in all_links)
    if has_cookie_policy:
        status_15 = "passed"
        details_15 = "Найдена ссылка на Политику использования файлов Cookie."
        fix_15 = "Документ оформлен."
    elif has_cookie_banner:
        status_15 = "warning"
        details_15 = "Cookie-баннер есть, но отдельная ссылка на Политику файлов Cookie не зафиксирована."
        fix_15 = "В блоке T849 добавьте ссылку на раздел Политики с описанием типов cookie (технические, аналитические)."
    else:
        status_15 = "failed"
        details_15 = "Политика использования cookie отсутствует."
        fix_15 = "Включите пункт о cookie в общую Политику конфиденциальности или создайте страницу /cookie-policy."

    items.append({
        "id": 15,
        "block_id": 4,
        "block_title": "4. Cookie-файлы, веб-аналитика и трекинг",
        "title": "Политика использования файлов Cookie",
        "status": status_15,
        "risk_level": "medium" if status_15 == "warning" else ("high" if status_15 == "failed" else "passed"),
        "fine_info": "Штраф: до 700 000 ₽",
        "law_ref": "ч. 2 ст. 13.11 КоАП РФ",
        "details": details_15,
        "tilda_fix": fix_15
    })

    # 16. Кнопка явного согласия («Принять» / «Согласен»)
    passive_cookie = "оставаясь на сайте" in html_lower or "продолжая использовать" in html_lower
    if passive_cookie:
        status_16 = "failed"
        details_16 = "Найдена фраза 'Оставаясь на сайте...'. Пассивное согласие признано РКН недействительным!"
        fix_16 = "Замените текст на явную кнопку действия: 'Принять' или 'Согласен'."
    elif has_cookie_banner:
        status_16 = "passed"
        details_16 = "В баннере используется кнопка явного подтверждения."
        fix_16 = "Настройка корректна."
    else:
        status_16 = "warning"
        details_16 = "Cookie-баннер отсутствует, невозможно подтвердить наличие явной кнопки."
        fix_16 = "Добавьте блок T849 с кнопкой 'Согласен'."

    items.append({
        "id": 16,
        "block_id": 4,
        "block_title": "4. Cookie-файлы, веб-аналитика и трекинг",
        "title": "Кнопка явного согласия («Принять» / «Согласен»)",
        "status": status_16,
        "risk_level": "high" if status_16 == "failed" else ("medium" if status_16 == "warning" else "passed"),
        "fine_info": "Штраф: до 700 000 ₽",
        "law_ref": "ч. 2 ст. 13.11 КоАП РФ",
        "details": details_16,
        "tilda_fix": fix_16
    })

    # -------------------------------------------------------------
    # БЛОК 5: Локализация баз данных и удаление иностранного софта (ч. 8-9 ст. 13.11)
    # -------------------------------------------------------------
    # 17. Физическое расположение серверов и баз данных в РФ
    if site.is_ru_hosting is True:
        status_17 = "passed"
        details_17 = f"Сервер расположен в РФ (IP: {site.ip_address}, провайдер: {site.hosting_provider_guess})."
        fix_17 = "Сервер удовлетворяет закону о локализации баз данных."
    elif site.is_ru_hosting is False:
        status_17 = "failed"
        details_17 = f"Сервер расположен за пределами РФ (IP: {site.ip_address}, {site.hosting_provider_guess}). Прямой риск блокировки и штрафа!"
        fix_17 = "Перенесите сайт/БД на российские серверы (Timeweb, Selectel, Reg.ru, VK Cloud, Yandex Cloud) или отключите зарубежный прокси."
    else:
        status_17 = "warning"
        details_17 = f"Не удалось однозначно подтвердить гео-локацию сервера (IP: {site.ip_address or 'скрыт'})."
        fix_17 = "Убедитесь, что серверы и хранилище базы клиентов находятся в российском дата-центре."

    items.append({
        "id": 17,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Физическое расположение серверов и баз данных в РФ",
        "status": status_17,
        "risk_level": "critical" if status_17 == "failed" else ("medium" if status_17 == "warning" else "passed"),
        "fine_info": "Штраф: от 1 до 6 млн ₽ (повторный до 18 млн ₽)",
        "law_ref": "ч. 5 ст. 18 Закона № 152-ФЗ (ч. 8–9 ст. 13.11)",
        "details": details_17,
        "tilda_fix": fix_17
    })

    # 18. Полное удаление Google Analytics и Google Tag Manager
    has_ga = any(k in html_lower for k in ["googletagmanager.com", "google-analytics.com", "gtag(", "ga('create'", "_gaq.push"])
    if has_ga:
        status_18 = "failed"
        details_18 = "Обнаружены скрипты Google Analytics / Google Tag Manager. Передача трафика на серверы США запрещена!"
        fix_18 = "В Tilda удалите счетчик Google Analytics в Настройках сайта -> Аналитика. Оставьте только Яндекс Метрику."
    else:
        status_18 = "passed"
        details_18 = "Скрипты Google Analytics и Google Tag Manager в коде не обнаружены."
        fix_18 = "Зарубежные счетчики отсутствуют."

    items.append({
        "id": 18,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Полное удаление Google Analytics и Google Tag Manager",
        "status": status_18,
        "risk_level": "critical" if status_18 == "failed" else "passed",
        "fine_info": "Штраф: от 1 до 6 млн ₽ (ст. 13.11 ч. 8)",
        "law_ref": "ч. 5 ст. 18 Закона № 152-ФЗ, РКН",
        "details": details_18,
        "tilda_fix": fix_18
    })

    # 19. Очистка кода от скриптов Meta (Facebook / Instagram Pixel)
    has_meta = any(k in html_lower for k in ["connect.facebook.net", "fbq(", "fbevents.js", "facebook pixel"])
    if has_meta:
        status_19 = "failed"
        details_19 = "Обнаружен пиксель Meta (Facebook/Instagram). Meta признана экстремистской организацией в РФ!"
        fix_19 = "Немедленно удалите все коды Facebook Pixel из Tilda (Настройки сайта -> Аналитика и кастомный HTML)."
    else:
        status_19 = "passed"
        details_19 = "Скрипты и пиксели экстремистской организации Meta отсутствуют."
        fix_19 = "Код чист."

    items.append({
        "id": 19,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Очистка кода от скриптов Meta (Facebook / Instagram Pixel)",
        "status": status_19,
        "risk_level": "critical" if status_19 == "failed" else "passed",
        "fine_info": "Критический правовой риск (экстремизм)",
        "law_ref": "Решение Тверского суда г. Москвы от 21.03.2022",
        "details": details_19,
        "tilda_fix": fix_19
    })

    # 20. Замена Google reCAPTCHA и внешних шрифтовых CDN
    has_recaptcha = "google.com/recaptcha" in html_lower or "recaptcha" in html_lower
    has_external_fonts = "fonts.googleapis.com" in html_lower or "fonts.gstatic.com" in html_lower

    if has_recaptcha:
        status_20 = "failed"
        details_20 = "Обнаружена Google reCAPTCHA. Она передает профили пользователей за рубеж."
        fix_20 = "В Tilda в формах замените Google reCAPTCHA на отечественную Yandex SmartCaptcha."
    elif has_external_fonts:
        status_20 = "warning"
        details_20 = "Обнаружены внешние шрифты Google Fonts. Рекомендуется локализовать загрузку шрифтов."
        fix_20 = "В Tilda загрузите файлы шрифтов (WOFF2) напрямую в проект через 'Пользовательские шрифты'."
    else:
        status_20 = "passed"
        details_20 = "reCAPTCHA и прямые запросы к зарубежным шрифтовым CDN не обнаружены."
        fix_20 = "Внешние шрифты и капча в норме."

    items.append({
        "id": 20,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Замена Google reCAPTCHA и внешних шрифтовых CDN",
        "status": status_20,
        "risk_level": "high" if status_20 == "failed" else ("medium" if status_20 == "warning" else "passed"),
        "fine_info": "Штраф: до 6 000 000 ₽",
        "law_ref": "ч. 5 ст. 18 Закона № 152-ФЗ",
        "details": details_20,
        "tilda_fix": fix_20
    })

    # 21. Уведомление о трансграничной передаче
    status_21 = "warning"
    details_21 = "Если данные передаются иностранным сервисам, требуется подача предварительного уведомления в РКН."
    fix_21 = "Если сайт работает только с российскими сервисами (Яндекс, российские CRM/эквайринг), уведомление не требуется."

    items.append({
        "id": 21,
        "block_id": 5,
        "block_title": "5. Локализация баз данных и удаление иностранного софта",
        "title": "Уведомление о трансграничной передаче (если применимо)",
        "status": status_21,
        "risk_level": "medium",
        "fine_info": "Штраф: до 300 000 ₽",
        "law_ref": "ст. 12 Закона № 152-ФЗ",
        "details": details_21,
        "tilda_fix": fix_21
    })

    # -------------------------------------------------------------
    # БЛОК 6: Реестр операторов РКН и реагирование на утечки (ст. 13.11 КоАП)
    # -------------------------------------------------------------
    # 22. Подача уведомления и включение в Реестр операторов РКН
    if has_forms:
        status_22 = "warning"
        details_22 = "На сайте есть формы сбора данных. Вы обязаны состоять в Реестре операторов РКН (pd.rkn.gov.ru)."
        fix_22 = "Подайте электронное уведомление об обработке персональных данных через портал pd.rkn.gov.ru."
    else:
        status_22 = "passed"
        details_22 = "Формы сбора данных не найдены. Если сбор не ведется, уведомление не обязательно."
        fix_22 = "При добавлении форм обязательно зарегистрируйтесь в реестре."

    items.append({
        "id": 22,
        "block_id": 6,
        "block_title": "6. Реестр операторов РКН и реагирование на утечки",
        "title": "Подача уведомления и включение в Реестр операторов РКН",
        "status": status_22,
        "risk_level": "high" if status_22 == "warning" else "passed",
        "fine_info": "Штраф: 100 000 – 300 000 ₽ (ч. 10 ст. 13.11 КоАП)",
        "law_ref": "ч. 10 ст. 13.11 КоАП РФ",
        "details": details_22,
        "tilda_fix": fix_22
    })

    # 23. Актуальность данных в реестре РКН
    status_23 = "warning"
    details_23 = "Проверьте, чтобы в реестре РКН был указан именно этот домен и актуальный перечень собираемых полей."
    fix_23 = "При смене домена или добавления новых полей (например, паспорт) подайте уведомление об изменениях в течение 10 дней."

    items.append({
        "id": 23,
        "block_id": 6,
        "block_title": "6. Реестр операторов РКН и реагирование на утечки",
        "title": "Актуальность данных в реестре РКН",
        "status": status_23,
        "risk_level": "medium",
        "fine_info": "Штраф: до 300 000 ₽",
        "law_ref": "ст. 22 Закона № 152-ФЗ",
        "details": details_23,
        "tilda_fix": fix_23
    })

    # 24. Регламент уведомления об утечках: 24 и 72 часа
    status_24 = "warning"
    details_24 = "Убедитесь, что ответственный сотрудник знает регламент: 24 часа на первичное уведомление РКН об инциденте утечки."
    fix_24 = "Подготовьте внутренний приказ и регламент реагирования на утечки данных для защиты от оборотного штрафа до 3% выручки."

    items.append({
        "id": 24,
        "block_id": 6,
        "block_title": "6. Реестр операторов РКН и реагирование на утечки",
        "title": "Регламент уведомления об утечках: 24 и 72 часа",
        "status": status_24,
        "risk_level": "medium",
        "fine_info": "Штраф: до 3 000 000 ₽ + оборотный штраф до 3% выручки",
        "law_ref": "ч. 11–14 ст. 13.11 КоАП РФ",
        "details": details_24,
        "tilda_fix": fix_24
    })

    # -------------------------------------------------------------
    # БЛОК 7: Новые стандарты 2026 года: Русификация, Доступность и SSL
    # -------------------------------------------------------------
    # 25. Русификация сайта (ФЗ «О государственном языке РФ»)
    # Search for untranslated english buttons / headers
    raw_buttons = [b.get_text(strip=True).lower() for b in soup.find_all(["button", "a"]) if b.get_text(strip=True)]
    english_cta = [w for w in raw_buttons if w in ["buy", "order", "shop", "sale", "submit", "send", "contacts", "cart", "subscribe"]]

    if english_cta:
        status_25 = "failed"
        details_25 = f"Обнаружены нерусифицированные англоязычные элементы интерфейса: {', '.join(set(english_cta))}. С 1 марта 2026 г. это нарушение!"
        fix_25 = "В Tilda переведите все кнопки и меню на русский язык ('Купить' вместо 'Buy', 'Корзина' вместо 'Cart', 'Распродажа' вместо 'Sale')."
    else:
        status_25 = "passed"
        details_25 = "Ключевые элементы навигации и кнопки выполнены на русском языке."
        fix_25 = "Требования ФЗ 'О государственном языке РФ' соблюдены."

    items.append({
        "id": 25,
        "block_id": 7,
        "block_title": "7. Новые стандарты 2026 года: Русификация, Доступность и SSL",
        "title": "Русификация сайта (с 1 марта 2026 г.)",
        "status": status_25,
        "risk_level": "high" if status_25 == "failed" else "passed",
        "fine_info": "Предписания ФАС и Роскомнадзора",
        "law_ref": "ФЗ «О государственном языке РФ»",
        "details": details_25,
        "tilda_fix": fix_25
    })

    # 26. Доступность для слабовидящих людей (ГОСТ Р 52872-2019)
    images = soup.find_all("img")
    images_without_alt = [img for img in images if not img.get("alt")]
    missing_alt_ratio = len(images_without_alt) / len(images) if images else 0

    if images and missing_alt_ratio > 0.5:
        status_26 = "failed"
        details_26 = f"У {len(images_without_alt)} из {len(images)} изображений отсутствует атрибут alt. Нарушение ГОСТ Р 52872-2019."
        fix_26 = "В Tilda пропишите alt-описание ко всем смысловым картинкам в настройках изображения."
    elif images and missing_alt_ratio > 0.1:
        status_26 = "warning"
        details_26 = f"У части изображений ({len(images_without_alt)}) нет alt-тегов."
        fix_26 = "Добавьте alt-теги ко всем ключевым изображениям для скринридеров."
    else:
        status_26 = "passed"
        details_26 = "Изображения снабжены alt-тегами, верстка соответствует базовым нормам доступности."
        fix_26 = "Параметры доступности соблюдены."

    items.append({
        "id": 26,
        "block_id": 7,
        "block_title": "7. Новые стандарты 2026 года: Русификация, Доступность и SSL",
        "title": "Доступность для слабовидящих людей (ГОСТ Р 52872-2019)",
        "status": status_26,
        "risk_level": "medium" if status_26 in ["warning", "failed"] else "passed",
        "fine_info": "Предписание надзорных органов",
        "law_ref": "ГОСТ Р 52872-2019, Закон о социальной защите инвалидов",
        "details": details_26,
        "tilda_fix": fix_26
    })

    # 27. Активный SSL/HTTPS сертификат и резервное копирование
    if site.is_https:
        status_27 = "passed"
        details_27 = "Сайт открывается по защищенному протоколу HTTPS. SSL-сертификат активен."
        fix_27 = "Протокол HTTPS настроен корректно."
    else:
        status_27 = "failed"
        details_27 = "Сайт не использует HTTPS шифрование! Передача персданных в открытом виде строго запрещена."
        fix_27 = "В Tilda подключите бесплатный SSL-сертификат в Настройках сайта -> SEO -> Настройка HTTPS."

    items.append({
        "id": 27,
        "block_id": 7,
        "block_title": "7. Новые стандарты 2026 года: Русификация, Доступность и SSL",
        "title": "Активный SSL/HTTPS сертификат и резервное копирование",
        "status": status_27,
        "risk_level": "critical" if status_27 == "failed" else "passed",
        "fine_info": "Недопустимо для сбора ПДн (ст. 19 Закона 152-ФЗ)",
        "law_ref": "ст. 19 Закона № 152-ФЗ, Приказ ФСТЭК № 21",
        "details": details_27,
        "tilda_fix": fix_27
    })

    return items
