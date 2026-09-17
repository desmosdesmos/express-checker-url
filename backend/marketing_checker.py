from typing import Any, Dict, List
from bs4 import BeautifulSoup
from .crawler import SiteData


def run_marketing_audit(site: SiteData) -> Dict[str, Any]:
    """Evaluates conversion factors, UX and marketing elements in plain, understandable language."""
    html = site.html
    html_lower = html.lower()
    soup = site.soup or BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True).lower()
    all_links = soup.find_all("a", href=True)

    checks: List[Dict[str, Any]] = []

    # 1. Первый экран и оффер (H1)
    h1_tags = soup.find_all("h1")
    h1_count = len(h1_tags)
    h1_text = h1_tags[0].get_text(strip=True) if h1_count > 0 else ""

    weak_h1_words = ["главная", "добро пожаловать", "о нас", "компания", "услуги", "каталог", "home", "welcome"]
    is_weak = any(h1_text.lower() == w or h1_text.lower().startswith(w) for w in weak_h1_words)

    if h1_count == 1 and len(h1_text) >= 15 and not is_weak:
        status_h1 = "passed"
        details_h1 = f"Главный заголовок сформулирован отлично: «{h1_text[:60]}...»"
        fix_h1 = "Посетитель сразу понимает суть предложения за первые 3 секунды."
    elif h1_count == 0:
        status_h1 = "failed"
        details_h1 = "На странице нет главного заголовка H1. Человек открывает сайт и не видит конкретного ответа: что вы предлагаете и какую проблему решаете."
        fix_h1 = "Добавьте на первом экране четкий заголовок: 'Что предлагаем + Для кого + Главная выгода'."
    elif h1_count > 1:
        status_h1 = "warning"
        details_h1 = f"На странице найдено несколько тегов H1 ({h1_count} шт.). Это размывает фокус внимания клиента и мешает продвижению в Яндексе."
        fix_h1 = "Оставьте только один H1 на первом экране, остальным разделам задайте H2."
    else:
        status_h1 = "warning"
        details_h1 = f"Заголовок слишком абстрактный («{h1_text}»). В нем нет конкретной пользы или позиционирования."
        fix_h1 = "Замените общее словосочетание на понятный оффер с измеримым результатом для клиента."

    checks.append({
        "category": "Первый экран",
        "title": "Главный заголовок и предложение (H1)",
        "status": status_h1,
        "impact": "Определяет, останется ли клиент на сайте",
        "details": details_h1,
        "tilda_fix": fix_h1
    })

    # 2. Кнопка действия (CTA)
    action_words = [
        "получить", "заказать", "рассчитать", "записаться", "купить", "узнать стоимость",
        "оставить заявку", "забронировать", "позвонить", "написать", "связаться"
    ]
    buttons = soup.find_all(["button", "a"])
    cta_buttons = []
    for b in buttons:
        txt = b.get_text(strip=True).lower()
        if any(act in txt for act in action_words):
            cta_buttons.append(b.get_text(strip=True))

    if len(cta_buttons) >= 1:
        status_cta = "passed"
        details_cta = f"Найдено {len(cta_buttons)} кнопок действия («{cta_buttons[0]}» и др.). Клиенту понятно, какой шаг сделать."
        fix_cta = "Кнопка призыва к действию ведет к целевому контакту."
    else:
        status_cta = "failed"
        details_cta = "На сайте нет явной кнопки с призывом к действию. Посетителю не предложен четкий следующий шаг."
        fix_cta = "Добавьте яркую кнопку: 'Записаться', 'Рассчитать стоимость' или 'Написать в Telegram'."

    checks.append({
        "category": "Захват клиентов",
        "title": "Призыв к действию (Кнопка целевого действия)",
        "status": status_cta,
        "impact": "Влияет на число звонков и заявок",
        "details": details_cta,
        "tilda_fix": fix_cta
    })

    # 3. Быстрая связь (Telegram, WhatsApp, Телефон)
    has_telegram = any("t.me/" in a.get("href", "") or "telegram" in a.get("href", "").lower() for a in all_links)
    has_whatsapp = any("wa.me/" in a.get("href", "") or "whatsapp" in a.get("href", "").lower() for a in all_links)
    has_phone = any(a.get("href", "").startswith("tel:") for a in all_links)

    if (has_telegram or has_whatsapp) and has_phone:
        status_comm = "passed"
        details_comm = "Подключены и телефон по клику, и мессенджеры (Telegram/WhatsApp). Клиенту удобно связаться в 1 клик с телефона."
        fix_comm = "Каналы связи настроены идеально."
    elif has_telegram or has_whatsapp:
        status_comm = "passed"
        details_comm = "Есть прямая ссылка на мессенджер (Telegram / WhatsApp) — более 70% клиентов предпочитают писать, а не звонить."
        fix_comm = "Рекомендуется также сделать номер телефона ссылкой tel:."
    elif has_phone:
        status_comm = "warning"
        details_comm = "Указан только телефон, но нет быстрой кнопки мессенджера (Telegram или WhatsApp). Часть клиентов уходит без звонка, так как не любит разговаривать голосом."
        fix_comm = "Добавьте прямую кнопку 'Написать в Telegram' или 'Написать в WhatsApp'."
    else:
        status_comm = "failed"
        details_comm = "На сайте нет кликабельного телефона (tel:) и нет мессенджеров. Связаться с вами сложно."
        fix_comm = "Сделайте телефон кликабельным (href='tel:+7...') и добавьте кнопку Telegram."

    checks.append({
        "category": "Каналы связи",
        "title": "Мессенджеры (Telegram, WhatsApp) и телефон в 1 клик",
        "status": status_comm,
        "impact": "Увеличивает число обращений на 30-40%",
        "details": details_comm,
        "tilda_fix": fix_comm
    })

    # 4. Социальные доказательства (Отзывы, работы, гарантии)
    trust_keywords = ["отзыв", "кейс", "клиент", "портфолио", "гаранти", "наши работы", "до и после", "сертификат"]
    found_trust = [k for k in trust_keywords if k in page_text]

    if len(found_trust) >= 1:
        status_trust = "passed"
        details_trust = f"Обнаружены элементы доверия ({', '.join(found_trust[:3])}). Это снимает сомнения перед обращением."
        fix_trust = "Блоки доверия присутствуют."
    else:
        status_trust = "warning"
        details_trust = "Не найдены блоки с отзывами или примерами выполненных работ. Новому клиенту сложно оценить качество услуг."
        fix_trust = "Добавьте живые фотографии работ 'было/стало' и реальные отзывы с ссылками на клиентов."

    checks.append({
        "category": "Доверие",
        "title": "Социальные доказательства (Примеры работ, отзывы)",
        "status": status_trust,
        "impact": "Снимает страх перед покупкой",
        "details": details_trust,
        "tilda_fix": fix_trust
    })

    # 5. Превью в мессенджерах (Open Graph)
    og_title = soup.find("meta", property="og:title")
    og_image = soup.find("meta", property="og:image")
    og_desc = soup.find("meta", property="og:description")
    favicon = soup.find("link", rel=lambda x: x and ("icon" in x.lower() or "shortcut" in x.lower()))

    if og_image and favicon:
        status_og = "passed"
        details_og = "При отправке ссылки в Telegram или WhatsApp создается красивая карточка с картинкой и описанием. Иконка сайта (фавиконка) настроена."
        fix_og = "Отображение ссылки в мессенджерах и браузере настроено отлично."
    elif not og_image:
        status_og = "warning"
        details_og = "Отсутствует картинка для превью (тег og:image). Когда вы или клиент пересылаете ссылку в Telegram или WhatsApp, сообщение выглядит серой строкой без картинки."
        fix_og = "В настройках страницы загрузите картинку бейджика (1200х630 px), чтобы ссылка в Telegram выглядела привлекательно."
    elif not favicon:
        status_og = "warning"
        details_og = "Не найдена фавиконка (значок на вкладке браузера и в поиске Яндекса). Сайт выглядит безлико."
        fix_og = "Загрузите иконку сайта (favicon.ico или favicon.png)."
    else:
        status_og = "passed"
        details_og = "Мета-теги отображения настроены."
        fix_og = "Параметры в норме."

    checks.append({
        "category": "Вид ссылки в Telegram",
        "title": "Превью сайта в Telegram / WhatsApp (Open Graph) и Фавиконка",
        "status": status_og,
        "impact": "Определяет, кликнут ли по вашей ссылке в мессенджере",
        "details": details_og,
        "tilda_fix": fix_og
    })

    # 6. Скорость ответа
    resp_time = site.response_time_ms
    if resp_time < 1500:
        status_speed = "passed"
        details_speed = f"Быстрый отклик сервера ({resp_time} мс). Страница открывается без раздражающих задержек."
        fix_speed = "Скорость в норме."
    else:
        status_speed = "warning"
        details_speed = f"Время ответа сервера составляет {resp_time} мс. На мобильном интернете сайт может подгружаться дольше обычного."
        fix_speed = "Оптимизируйте размер загружаемых картинок (сжимайте в формат WebP)."

    checks.append({
        "category": "Скорость",
        "title": "Скорость открытия сайта",
        "status": status_speed,
        "impact": "Предотвращает уход посетителей при загрузке",
        "details": details_speed,
        "tilda_fix": fix_speed
    })

    passed_count = sum(1 for c in checks if c["status"] == "passed")
    total_count = len(checks)
    marketing_score = int(round((passed_count / total_count) * 100))

    return {
        "score": marketing_score,
        "passed_count": passed_count,
        "total_count": total_count,
        "checks": checks
    }
