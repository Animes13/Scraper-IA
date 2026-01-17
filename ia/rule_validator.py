# rule_validator.py
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# =============================
# UTILIDADES
# =============================

def unique_list(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def looks_like_episode(text):
    """
    Detecta se o texto parece um episódio válido.
    Ignora filmes, especiais, trailers etc.
    """
    text = text.lower()
    blacklist = ["filme", "movie", "especial", "ova", "trailer", "pv"]
    if any(b in text for b in blacklist):
        return False
    return True


# =============================
# VALIDADORES
# =============================

def validate_anime_list_page(html, rules, base_url=None):
    soup = BeautifulSoup(html, "html.parser")
    score = 0
    result = {
        "anime_links": [],
        "score": 0,
        "valid": False,
        "reason": []
    }

    container_sel = rules.get("container")
    card_sel = rules.get("anime_card")
    link_sel = rules.get("anime_link")

    if container_sel:
        container = soup.select_one(container_sel)
        if container:
            score += 20
        else:
            result["reason"].append("container_not_found")

    cards = soup.select(card_sel) if card_sel else []
    if cards:
        score += 20
    else:
        result["reason"].append("no_cards_found")

    links = []
    if link_sel:
        for a in soup.select(link_sel):
            href = a.get("href")
            if href:
                full = urljoin(base_url, href) if base_url else href
                links.append(full)

    links = unique_list(links)

    if len(links) >= 10:
        score += 40
    else:
        result["reason"].append("few_anime_links")

    result["anime_links"] = links
    result["score"] = score
    result["valid"] = score >= 70

    return result


def validate_anime_page(html, rules, base_url=None):
    soup = BeautifulSoup(html, "html.parser")
    score = 0
    result = {
        "episode_links": [],
        "score": 0,
        "valid": False,
        "reason": []
    }

    container_sel = rules.get("episodes_container")
    link_sel = rules.get("episode_link")

    container = soup.select_one(container_sel) if container_sel else None
    if container:
        score += 25
    else:
        result["reason"].append("episodes_container_not_found")
        container = soup  # fallback genérico

    links = []
    if link_sel:
        for a in container.select(link_sel):
            href = a.get("href")
            text = a.get_text(strip=True)

            if not href or not looks_like_episode(text):
                continue

            full = urljoin(base_url, href) if base_url else href
            links.append(full)

    links = unique_list(links)

    if len(links) >= 3:
        score += 40
    else:
        result["reason"].append("few_episode_links")

    # ordem (heurística simples)
    if links == sorted(links):
        score += 15

    result["episode_links"] = links
    result["score"] = score
    result["valid"] = score >= 80

    return result


def validate_episode_page(html, rules):
    soup = BeautifulSoup(html, "html.parser")
    score = 0
    result = {
        "player_found": False,
        "iframe_src": None,
        "score": 0,
        "valid": False,
        "reason": []
    }

    iframe_sel = rules.get("player_iframe")
    encrypted_attr = rules.get("encrypted_attribute")

    iframe = soup.select_one(iframe_sel) if iframe_sel else None

    if iframe:
        src = iframe.get("src")
        if src:
            score += 60
            result["iframe_src"] = src
        else:
            result["reason"].append("iframe_without_src")
    else:
        result["reason"].append("iframe_not_found")

    # atributo criptografado (fallback)
    if not iframe and encrypted_attr:
        tag = soup.find(attrs={encrypted_attr: True})
        if tag:
            score += 40

    result["player_found"] = score >= 60
    result["score"] = score
    result["valid"] = score >= 80

    return result


# =============================
# DISPATCHER GENÉRICO
# =============================

def validate(page_type, html, rules, base_url=None):
    if page_type == "anime_list_page":
        return validate_anime_list_page(html, rules, base_url)

    if page_type == "anime_page":
        return validate_anime_page(html, rules, base_url)

    if page_type == "episode_page":
        return validate_episode_page(html, rules)

    raise ValueError("Tipo de página inválido")