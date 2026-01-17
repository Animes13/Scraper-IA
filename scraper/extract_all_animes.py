# extract_all_animes.py
import os
import re
import json
import requests
import base64
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://goyabu.io"
DATA_DIR = "data"
RULES_FILE = "rules/goyabu.json"
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; Kodi) AppleWebKit/537.36 Chrome/120.0"
}

# =============================
# FUNÇÕES DE DECODE
# =============================
def decrypt_blogger_url(encrypted):
    try:
        if not encrypted:
            return None
        encrypted = encrypted.strip()
        missing = len(encrypted) % 4
        if missing:
            encrypted += "=" * (4 - missing)
        decoded = base64.b64decode(encrypted).decode("utf-8", errors="ignore")
        url = decoded[::-1].strip()
        if not url.startswith("http"):
            return None
        return url
    except:
        return None

def extract_blogger_googlevideo(html):
    try:
        if not html:
            return None
        m = re.search(r'VIDEO_CONFIG\s*=\s*({.*?});', html, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            streams = data.get("streams", [])
            if streams:
                streams.sort(key=lambda x: int(x.get("format_id", 0)), reverse=True)
                return streams[0].get("play_url") or streams[0].get("url")
        m = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});', html, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            formats = (data.get("streamingData", {}).get("formats", []) +
                       data.get("streamingData", {}).get("adaptiveFormats", []))
            for f in formats:
                url = f.get("url")
                if url and "googlevideo.com" in url:
                    return url
        m = re.search(r'(https://[^"\']+googlevideo\.com/videoplayback[^"\']+)', html)
        if m:
            return m.group(1)
        return None
    except:
        return None

# =============================
# FETCH HTML
# =============================
def fetch_html(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.text

# =============================
# PEGAR TODOS OS ANIMES
# =============================
def get_all_animes():
    animes = []
    page = 1
    while True:
        url = f"{BASE_URL}/lista-de-animes/page/{page}?l=todos&pg={page}"
        r = fetch_html(url)
        soup = BeautifulSoup(r, "html.parser")
        cards = soup.select("article a[href]")
        if not cards:
            break
        for a in cards:
            link = urljoin(BASE_URL, a["href"])
            title = a.get_text(" ", strip=True)
            animes.append((title, link))
        page += 1
    return animes

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    final_json = {}
    animes = get_all_animes()
    print(f"[INFO] Total de animes: {len(animes)}")

    for title, link in animes:
        print(f"🌐 {title}: iniciando...")

        anime_html = fetch_html(link)
        m = re.search(r"const allEpisodes\s*=\s*(\[[\s\S]*?\]);", anime_html)
        if not m:
            print(f"[WARN] Nenhum episódio encontrado em {title}")
            continue
        eps = json.loads(m.group(1).replace("\\/", "/"))
        eps.sort(key=lambda e: int(e.get("episodio", 0)))

        ep_dict = {}
        for ep in eps:
            ep_url = f"{BASE_URL}/{ep['id']}"
            ep_html = fetch_html(ep_url)
            # Detectar Blogger
            blogger_url = None
            m_blogger = re.search(r'var\s+player_url\s*=\s*"([^"]+)"', ep_html)
            if m_blogger:
                blogger_url = decrypt_blogger_url(m_blogger.group(1))
            # Extrair Googlevideo
            final_url = extract_blogger_googlevideo(ep_html) or blogger_url
            ep_dict[f"📺 EP {int(ep['episodio'])}"] = final_url

        final_json[f"🌐 {title}"] = ep_dict
        print(f"🌐 {title}: 📺 Total: {len(ep_dict)} Resolvidos {len([v for v in ep_dict.values() if v])}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(DATA_DIR, f"animes_{timestamp}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] JSON final salvo em {filepath}")
