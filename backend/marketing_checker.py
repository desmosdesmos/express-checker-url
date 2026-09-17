import re
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from .crawler import SiteData


def run_marketing_audit(site: SiteData) -> Dict[str, Any]:
    """Evaluates marketing, conversion factors and UX of the website, specifically for Tilda sites."""
    html = site.html
    html_lower = html.lower()
    soup = site.soup or BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True).lower()
    all_links = soup.find_all("a", href=True)

    checks: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # 1. Первый экран и УТП (Уникальное торговое предложение)
    # -------------------------------------------------------------
    h1_tags = soup.find_all("h1")
    h1_count = len(h1_tags)
    h1_text = h1_tags[0].get_text(strip=True) if h1_count > 0 else ""

    weak_h1_words = ["главная", "добро пожаловать", "о нас", "компания", "услуги", "каталог", "home", "welcome"]
    is_weak_h1 = any(h1_text.lower() == w or h1_text.lower().startswith(w) for w in weak_h1_words)

    if h1_count == 1 and len(h1_text) >= 15 and not is_weak_h1:
        status_h1 = "passed"
        details_h1 = f"Заголовок H1 настроен идеально: «{h1_text[:60]}...»"
        fix_h1 = "Оффер на первом экране сформулирован четко."
    elif h1_count == 0:
        status_h1 = "failed"
        details_h1 = "На странице полностью отсутствует главный заголовок <h1>! Посетитель за 3 секунды не понимает, куда попал."
        fix_h1 = "В Tilda в первом Zero Block или стандартном блоке задайте главному заголовку тег H1 с понятной выгодой для клиента."
    elif h1_count > 1:
        status_h1 = "warning"
        details_h1 = f"На странице обнаружено несколько заголовков <h1> ({h1_count} шт.). Это размывает фокус внимания и вредит SEO."
        fix_h1 = "Оставьте только один тег <h1> на первом экране, остальным заголовкам блоков назначьте <h2>."
    else:
        status_h1 = "warning"
        details_h1 = f"Заголовок <h1> слишком короткий или абстрактный: «{h1_text}». Нет четкого позиционирования."
        fix_h1 = "Сформулируйте УТП по формуле: 'Что делаем + Для кого + Какая выгода или гарантия'."

    checks.append({
        "category": "Первый экран и оффер",
        "title": "Главный оффер и заголовок первого экрана (H1)",
        "status": status_h1,
        "impact": "Критично для конверсии",
        "details": details_h1,
        "tilda_fix": fix_h1
    })

    # -------------------------------------------------------------
    # 2. Призыв к действию (CTA - Call To Action)
    # -------------------------------------------------------------
    action_words = [
        "получить", "заказать", "рассчитать", "записаться", "купить", "узнать стоимость",
        "оставить заявку", "забронировать", "попробовать", "начать", "скачать"
    ]
    buttons = soup.find_all(["button", "a"])
    cta_buttons = []
    for b in buttons:
        txt = b.get_text(strip=True).lower()
        if any(act in txt for act in action_words):
            cta_buttons.append(b.get_text(strip=True))

    weak_cta_words = ["подробнее", "читать далее", "дальше", "узнать больше", "more"]
    weak_buttons = [b.get_text(strip=True) for b in buttons if b.get_text(strip=True).lower() in weak_cta_words]

    if len(cta_buttons) >= 2:
        status_cta = "passed"
        details_cta = f"Найдено {len(cta_buttons)} активных кнопок с понятным глаголом действия («{cta_buttons[0]}» и др.)."
        fix_cta = "Призывы к действию направляют клиента к целевому шагу."
    elif len(cta_buttons) == 1:
        status_cta = "warning"
        details_cta = f"Найдена всего 1 конверсионная кнопка («{cta_buttons[0]}»). На длинном лендинге этого мало."
        fix_cta = "В Tilda дублируйте целевые кнопки после каждого ключевого смыслового блока (цены, отзывы, преимущества)."
    elif weak_buttons:
        status_cta = "failed"
        details_cta = f"Кнопки используют пассивные фразы без мотивации («{weak_buttons[0]}»). Конверсия теряется."
        fix_cta = "Замените размытое 'Подробнее' на действие с конкретной выгодой: 'Рассчитать стоимость за 1 минуту', 'Получить расчет'."
    else:
        status_cta = "failed"
        details_cta = "На сайте не найдено явных кнопок с призывом к действию (CTA). Посетитель не понимает следующий шаг."
        fix_cta = "Добавьте яркую контрастную кнопку захвата на первом экране и в шапке сайта."

    checks.append({
        "category": "Лидогенерация",
        "title": "Призывы к действию (CTA) и логика целевого действия",
        "status": status_cta,
        "impact": "Влияет на заявки напрямую",
        "details": details_cta,
        "tilda_fix": fix_cta
    })

    # -------------------------------------------------------------
    # 3. Быстрая связь через мессенджеры (Telegram, WhatsApp)
    # -------------------------------------------------------------
    has_telegram = any("t.me/" in a.get("href", "") or "telegram" in a.get("href", "").lower() for a in all_links)
    has_whatsapp = any("wa.me/" in a.get("href", "") or "whatsapp" in a.get("href", "").lower() or "api.whatsapp.com" in a.get("href", "") for a in all_links)
    has_phone = any(a.get("href", "").startswith("tel:") for a in all_links)

    if (has_telegram or has_whatsapp) and has_phone:
        status_contacts = "passed"
        details_contacts = "Подключены и кликабельный телефон, и мессенджеры для быстрой связи. Клиенту удобно писать в 1 клик."
        fix_contacts = "Каналы связи настроены отлично."
    elif has_telegram or has_whatsapp:
        status_contacts = "passed"
        details_contacts = "Есть прямая ссылка на мессенджер (Telegram / WhatsApp). 70% клиентов предпочитают переписку звонкам."
        fix_contacts = "Рекомендуется также добавить кликабельный телефон `tel:` в шапку."
    elif has_phone:
        status_contacts = "warning"
        details_contacts = "Указан только телефон. Нет возможности написать в мессенджер (Telegram / WhatsApp). Вы теряете аудиторию интровертов!"
        fix_contacts = "В Tilda подключите виджет быстрых кнопок мессенджеров или блок контактов с кнопкой Telegram."
    else:
        status_contacts = "failed"
        details_contacts = "На сайте нет кликабельных телефонов (`tel:`) и прямых ссылок на мессенджеры."
        fix_contacts = "Сделайте номер телефона ссылкой вида `tel:+79991234567` и добавьте кнопку Telegram."

    checks.append({
        "category": "Лидогенерация",
        "title": "Точки контакта и мессенджеры (Telegram, WhatsApp)",
        "status": status_contacts,
        "impact": "Увеличивает обращения на 30-40%",
        "details": details_contacts,
        "tilda_fix": fix_contacts
    })

    # -------------------------------------------------------------
    # 4. Социальные доказательства (Trust & Proofs)
    # -------------------------------------------------------------
    trust_keywords = ["отзыв", "кейс", "клиент", "портфолио", "гаранти", "сертификат", "наши работы", "результат", "до и после"]
    found_trust = [k for k in trust_keywords if k in page_text]

    if len(found_trust) >= 2:
        status_trust = "passed"
        details_trust = f"Обнаружены блоки социального доверия ({', '.join(found_trust[:3])}). Это снимает страх перед покупкой."
        fix_trust = "Факторы доверия присутствуют."
    elif len(found_trust) == 1:
        status_trust = "warning"
        details_trust = f"Найдено упоминание доверия ({found_trust[0]}), но блоков мало для убеждения холодного трафика."
        fix_trust = "Добавьте в Tilda блок отзывов с реальными ссылками на клиентов, видео-отзывами или кейсами 'было/стало'."
    else:
        status_trust = "failed"
        details_trust = "Не найдены отзывы, кейсы, сертификаты или гарантии. Неизвестному сайту сложно доверять деньги."
        fix_trust = "Внедрите блок с социальными доказательствами: реальные отзывы, логотипы клиентов, лицензии."

    checks.append({
        "category": "Доверие и конверсия",
        "title": "Социальные доказательства (Отзывы, кейсы, гарантии)",
        "status": status_trust,
        "impact": "Снимает возражения",
        "details": details_trust,
        "tilda_fix": fix_trust
    })

    # -------------------------------------------------------------
    # 5. Сниппет в Telegram и соцсетях (OpenGraph & Favicon)
    # -------------------------------------------------------------
    og_title = soup.find("meta", property="og:title")
    og_image = soup.find("meta", property="og:image")
    og_desc = soup.find("meta", property="og:description")
    favicon = soup.find("link", rel=lambda x: x and ("icon" in x.lower() or "shortcut" in x.lower()))

    og_complete = bool(og_title and og_image)

    if og_complete and favicon:
        status_og = "passed"
        details_og = "Настроены OpenGraph (красивое превью ссылки в Telegram/VK) и персональная фавиконка."
        fix_og = "Сниппет сайта в соцсетях и мессенджерах привлекателен."
    elif not og_image:
        status_og = "warning"
        details_og = "Отсутствует картинка для превью (`og:image`). При отправке ссылки в Telegram/WhatsApp будет серая ссылка без картинки."
        fix_og = "В Tilda в Настройках страницы -> Бейджик (Facebook/VK/TG) загрузите привлекательное изображение 1200x630 px."
    elif not favicon:
        status_og = "warning"
        details_og = "Не найдена иконка сайта (Favicon). В поисковой выдаче Яндекса сайт выглядит как безымянная страница."
        fix_og = "В Tilda в Настройках сайта загрузите Favicon в формате .ico или .png."
    else:
        status_og = "warning"
        details_og = "Мета-теги OpenGraph настроены частично."
        fix_og = "Проверьте заполнение заголовка, описания и изображения в бейджике страницы Tilda."

    checks.append({
        "category": "Упаковка и виральность",
        "title": "Бейджик в Telegram/соцсетях (OpenGraph) и Фавиконка",
        "status": status_og,
        "impact": "Определяет кликабельность ссылки",
        "details": details_og,
        "tilda_fix": fix_og
    })

    # -------------------------------------------------------------
    # 6. SEO-база (Title & Description)
    # -------------------------------------------------------------
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc_text = meta_desc.get("content", "").strip() if meta_desc else ""

    is_bad_title = any(b in title_text.lower() for b in ["главная", "home", "tilda", "заголовок страницы"]) or len(title_text) < 10

    if len(title_text) >= 15 and not is_bad_title and len(desc_text) >= 30:
        status_seo = "passed"
        details_seo = f"Title («{title_text[:40]}...») и Description заполнены информативно."
        fix_seo = "Базовая поисковая оптимизация в норме."
    elif is_bad_title or not title_text:
        status_seo = "failed"
        details_seo = f"Заголовок вкладки Title пустой или шаблонный («{title_text or 'Не найден'}»). Потеря бесплатного трафика из поиска."
        fix_seo = "В Tilda в Настройках страницы укажите понятный Title: 'Услуга в Городе — Выгода / Бренд'."
    elif not desc_text:
        status_seo = "warning"
        details_seo = "Метатег Description не заполнен. Яндекс сам выберет случайный кусок текста для сниппета."
        fix_seo = "Заполните Description (140-160 символов) с кратким описанием преимуществ и контактом."
    else:
        status_seo = "passed"
        details_seo = "Теги Title и Description заданы."
        fix_seo = "Оптимизация выполнена."

    checks.append({
        "category": "Упаковка и виральность",
        "title": "Поисковый сниппет (Title и Description)",
        "status": status_seo,
        "impact": "Привлекает бесплатный SEO-трафик",
        "details": details_seo,
        "tilda_fix": fix_seo
    })

    # -------------------------------------------------------------
    # 7. Скорость и вес страницы (Tilda Performance)
    # -------------------------------------------------------------
    # Check response time and page size
    resp_time = site.response_time_ms
    page_size = site.page_size_kb

    if resp_time < 1200 and page_size < 3500:
        status_speed = "passed"
        details_speed = f"Быстрый ответ сервера ({resp_time} мс), размер HTML в пределах нормы ({page_size} КБ)."
        fix_speed = "Сайт загружается комфортно."
    elif resp_time >= 2500:
        status_speed = "failed"
        details_speed = f"Медленный ответ сервера ({resp_time} мс). До 40% пользователей со смартфонов уходят, не дождавшись загрузки."
        fix_speed = "В Tilda проверьте количество тяжелых скриптов, отключите неиспользуемые блоки и оптимизируйте изображения."
    else:
        status_speed = "warning"
        details_speed = f"Время ответа: {resp_time} мс. На мобильном 4G сайте может открываться с задержкой."
        fix_speed = "Сжимайте изображения в WebP и избегайте перегрузки страницы сложной пошаговой анимацией в Zero Block."

    checks.append({
        "category": "Технический маркетинг",
        "title": "Скорость загрузки и оптимизация страницы",
        "status": status_speed,
        "impact": "Снижает процент отказов (Bounce Rate)",
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
