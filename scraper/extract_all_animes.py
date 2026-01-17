# -*- coding: utf-8 -*-
import os
import re
import json
import unicodedata
import requests
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# ==================================================
# CONFIGURAÇÕES DE DIRETÓRIOS
# ==================================================
BASE = "https://goyabu.io"
HTML_DIR = "HTML"
JSON_DIR = "data"
RULES_DIR = "rules"
os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(RULES_DIR, exist_ok=True)

# ==================================================
# NORMALIZAÇÃO DE TÍTULOS
# ==================================================
def normalize_title(title):
    if not title:
        return ""
    title = unicodedata.normalize("NFKD", title)
    title = title.encode("ascii", "ignore").decode("ascii")
    title = title.lower()
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"[–\-:]", " ", title)
    title = re.sub(r"\b(part|cour|season|temporada|filme|movie|episodio|ep)\b.*", "", title)
    title = re.sub(r"\s+\d+$", "", title)
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip()

# ==================================================
# SALVA HTML LOCAL
# ==================================================
def save_html(html, name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(HTML_DIR, f"{name}_{timestamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

# ==================================================
# SALVA JSON FINAL
# ==================================================
def save_json(data, filename="all_animes.json"):
    filepath = os.path.join(JSON_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[✅] JSON final salvo em {filepath}")

# ==================================================
# EXTRAI GOOGLEVIDEO DO HTML DO BLOGGER
# ==================================================
def extract_blogger_googlevideo(html):
    try:
        m = re.search(r'(https://[^"\']+googlevideo\.com/videoplayback[^"\']+)', html)
        if m:
            return m.group(1)
        return None
    except Exception:
        return None

# ==================================================
# CLASSE HINATA PARA PEGAR EPISÓDIOS
# ==================================================
class Hinata:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Kodi) AppleWebKit/537.36 Chrome/120.0"
        }

    def soup(self, html):
        return BeautifulSoup(html, "html.parser")

    def episodios(self, url):
        """
        Retorna lista de episódios:
        [(titulo, link), ...]
        """
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            r.raise_for_status()
            html = r.text

            m = re.search(r"const allEpisodes\s*=\s*(\[[\s\S]*?\]);", html)
            if not m:
                return [], False, None

            eps = json.loads(m.group(1).replace("\\/", "/"))
            eps.sort(key=lambda e: int(e.get("episodio", 0)))

            result = []
            for ep in eps:
                ep_title = f"Episódio {int(ep['episodio']):02d} - {ep.get('audio', '')}"
                ep_id = str(ep.get("id", ""))  # garante string
                link = urljoin(BASE, ep_id)
                result.append((ep_title, link))

            return result, False, None
        except Exception as e:
            print(f"[❌ Hinata] Erro ao pegar episódios: {e}")
            return [], False, None

    def resolver(self, url):
        """
        Resolve link final do episódio (Blogger → GoogleVideo)
        """
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            r.raise_for_status()
            html = r.text
            link = extract_blogger_googlevideo(html)
            if link:
                return link
            return None
        except Exception as e:
            print(f"[❌ Hinata] Erro ao resolver episódio: {e}")
            return None

# ==================================================
# CARREGA REGRAS DO JSON
# ==================================================
def load_rules():
    path = os.path.join(RULES_DIR, "goyabu.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ==================================================
# PEGA LISTA DE ANIMES
# ==================================================
def get_anime_list(page=1):
    rules = load_rules()
    url = f"{BASE}/lista-de-animes/page/{page}?l=todos&pg={page}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        html = r.text
    except Exception as e:
        print(f"[🌐 LIST] Erro ao buscar página {page}: {e}")
        return []

    if len(html) < 500:
        print(f"[🌐 LIST] HTML inválido na página {page}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    card_selector = rules.get("anime_card", "article")
    link_selector = rules.get("anime_link", "a[href]")

    cards = soup.select(card_selector)
    animes = []
    seen_urls = set()

    for card in cards:
        a = card.select_one(link_selector)
        if not a or not a.get("href"):
            continue

        name = a.get_text(" ", strip=True)
        link = urljoin(BASE, a["href"])
        if len(name) < 2 or link in seen_urls:
            continue

        seen_urls.add(link)
        animes.append({
            "name": f"🌐 {name}",
            "url": link,
            "normalized_name": normalize_title(name)
        })

    print(f"🌐 [LIST] Página {page}: {len(animes)} animes encontrados")
    return animes

# ==================================================
# PROCESSA TODOS OS ANIMES E EPISÓDIOS
# ==================================================
def process_animes():
    scraper = Hinata()
    final_result = {}
    page = 1

    while True:
        anime_list = get_anime_list(page)
        if not anime_list:
            print(f"🌐 [LIST] Nenhum anime encontrado na página {page}, finalizando scraping.")
            break

        for anime in anime_list:
            anime_name = anime["name"]
            final_result[anime_name] = {}
            print(f"\n🌐 Iniciando coleta do anime: {anime_name}")

            try:
                eps, _, _ = scraper.episodios(anime["url"])
                total_eps = len(eps)
                resolved_eps = 0

                for ep in eps:
                    ep_title = ep[0]
                    ep_url = ep[1]

                    try:
                        r = requests.get(ep_url, timeout=15)
                        r.raise_for_status()
                        html = r.text

                        save_html(html, f"{anime_name}_{ep_title}")

                        link = scraper.resolver(ep_url)
                        if not link:
                            link = extract_blogger_googlevideo(html)
                        if not link:
                            link = "Link não encontrado"

                        clean_title = normalize_title(ep_title)
                        final_result[anime_name][f"📺 {ep_title}"] = {
                            "url": link,
                            "normalized_title": f"{anime_name} {clean_title}"
                        }

                        resolved_eps += 1
                        print(
                            f"{anime_name} | 📺 {ep_title} | "
                            f"✅ Resolvidos: {resolved_eps}/{total_eps} | "
                            f"⚡ Progresso: {resolved_eps/total_eps*100:.1f}%"
                        )

                    except Exception as e:
                        print(f"[❌ ERRO] {anime_name} | 📺 {ep_title} | {e}")
                        final_result[anime_name][f"📺 {ep_title}"] = {"url": None, "error": str(e)}

            except Exception as e:
                print(f"[❌ ERRO] Falha ao coletar episódios de {anime_name}: {e}")

        page += 1  # passa para a próxima página

    save_json(final_result)

# ==================================================
# EXECUÇÃO PRINCIPAL
# ==================================================
if __name__ == "__main__":
    process_animes()