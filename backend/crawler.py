import asyncio
import socket
import ssl
import time
import urllib.parse
from typing import Any, Dict, List, Optional
import httpx
from bs4 import BeautifulSoup


# Known Russian hosting ASN / IP keywords and reverse DNS patterns
RU_HOSTING_PATTERNS = [
    "timeweb", "selectel", "beget", "reg.ru", "regru", "yandex", "vk cloud", "mail.ru",
    "rostelecom", "sbercloud", "cloud.ru", "masterhost", "nic.ru", "spaceweb",
    "mchost", "firstvds", "ispsystem", "infobox", "vscale", "tilda"
]

# Known foreign infrastructure
FOREIGN_HOSTING_PATTERNS = [
    "cloudflare", "amazon", "aws", "digitalocean", "hetzner", "ovh", "google",
    "linode", "akamai", "fastly", "azure", "microsoft", "oracle", "vultr"
]


class SiteData:
    def __init__(self):
        self.raw_url: str = ""
        self.final_url: str = ""
        self.domain: str = ""
        self.is_https: bool = False
        self.status_code: int = 0
        self.response_time_ms: int = 0
        self.ip_address: Optional[str] = None
        self.reverse_dns: Optional[str] = None
        self.server_header: Optional[str] = None
        self.is_ru_hosting: Optional[bool] = None
        self.hosting_provider_guess: str = "Не определен"
        self.html: str = ""
        self.soup: Optional[BeautifulSoup] = None
        self.is_tilda: bool = False
        self.error: Optional[str] = None
        self.page_size_kb: float = 0.0
        self.subpages_checked: Dict[str, int] = {}  # url -> status_code


async def inspect_server_ip(domain: str) -> tuple[Optional[str], Optional[str], Optional[bool], str]:
    """Resolves DNS and performs reverse lookup to check Russian hosting status."""
    loop = asyncio.get_running_loop()
    ip = None
    rdns = None
    is_ru = None
    provider = "Не определен"

    try:
        addr_info = await loop.getaddrinfo(domain, 443, proto=socket.IPPROTO_TCP)
        if addr_info:
            ip = addr_info[0][4][0]
    except Exception:
        try:
            addr_info = await loop.getaddrinfo(domain, 80, proto=socket.IPPROTO_TCP)
            if addr_info:
                ip = addr_info[0][4][0]
        except Exception:
            pass

    if ip:
        try:
            rdns_entry = await loop.getnameinfo((ip, 0), 0)
            if rdns_entry:
                rdns = rdns_entry[0].lower()
        except Exception:
            pass

        # Also make a quick async IP-API query with short timeout for country/org check
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                res = await client.get(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,isp,org,as")
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "success":
                        country_code = data.get("countryCode", "")
                        isp = (data.get("isp", "") + " " + data.get("org", "") + " " + data.get("as", "")).lower()
                        provider = data.get("isp") or data.get("org") or "Не определен"
                        if country_code == "RU":
                            is_ru = True
                        else:
                            is_ru = False
                            # If Cloudflare is proxying, mention it
                            if "cloudflare" in isp:
                                provider = "Cloudflare (Проксирование трафика за рубеж)"
        except Exception:
            # Fallback to reverse DNS heuristic
            if rdns:
                for pat in RU_HOSTING_PATTERNS:
                    if pat in rdns:
                        is_ru = True
                        provider = pat.capitalize()
                        break
                if is_ru is None:
                    for pat in FOREIGN_HOSTING_PATTERNS:
                        if pat in rdns:
                            is_ru = False
                            provider = pat.capitalize()
                            break

    return ip, rdns, is_ru, provider


async def crawl_website(url: str) -> SiteData:
    data = SiteData()
    data.raw_url = url.strip()

    # Normalize protocol
    if not data.raw_url.startswith(("http://", "https://")):
        target_url = "https://" + data.raw_url
    else:
        target_url = data.raw_url

    parsed = urllib.parse.urlparse(target_url)
    data.domain = parsed.netloc or parsed.path.split("/")[0]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    start_time = time.time()
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=12.0, verify=False) as client:
            # Attempt HTTPS first
            try:
                response = await client.get(target_url)
            except Exception:
                if target_url.startswith("https://"):
                    target_url = "http://" + target_url[8:]
                    response = await client.get(target_url)
                else:
                    raise

            data.response_time_ms = int((time.time() - start_time) * 1000)
            data.status_code = response.status_code
            data.final_url = str(response.url)
            data.is_https = data.final_url.startswith("https://")
            data.server_header = response.headers.get("server")
            data.html = response.text
            data.page_size_kb = round(len(response.content) / 1024.0, 1)

            # Parse DOM
            data.soup = BeautifulSoup(data.html, "html.parser")

            # Check if site is built on Tilda
            html_lower = data.html.lower()
            if (
                "tilda" in html_lower
                or "t-records" in html_lower
                or "static.tildacdn.com" in html_lower
                or "tildacdn" in html_lower
            ):
                data.is_tilda = True

            # Domain & server IP check
            parsed_final = urllib.parse.urlparse(data.final_url)
            clean_host = parsed_final.hostname or data.domain
            ip, rdns, is_ru, provider = await inspect_server_ip(clean_host)
            data.ip_address = ip
            data.reverse_dns = rdns
            data.is_ru_hosting = is_ru
            data.hosting_provider_guess = provider

    except httpx.RequestError as e:
        data.error = f"Не удалось подключиться к сайту: {str(e)}"
    except Exception as e:
        data.error = f"Ошибка при сканировании: {str(e)}"

    return data
