# rule_validator.py
from bs4 import BeautifulSoup
import re

# =============================
# CONFIG
# =============================
PASS_SCORE = 70

WEIGHTS = {
    "anime_list_page": {
        "container": 20,
        "anime_card": 40,
        "anime_link": 40,
    },
    "anime_page": {
        "episodes_container": 50,
        "episode_link": 50,
    },
    "episode_page": {
        "player_iframe": 60,
        "encrypted_attribute": 20,
        "blogger_pattern": 20,
    },
}

# =============================
# HELPERS
# =============================
def css_exists(soup, selector):
    try:
        return bool(soup.select(selector))
    except Exception:
        return False


def attr_exists(soup, attr):
    return bool(soup.select(f"[{attr}]"))


def regex_exists(html, pattern):
    try:
        return bool(re.search(pattern, html))
    except Exception:
        return False


# =============================
# VALIDADORES POR PÁGINA
# =============================
def validate_anime_list(html, rules):
    soup = BeautifulSoup(html, "html.parser")
    score = 0
    details = {}

    for field, weight in WEIGHTS["anime_list_page"].items():
        selector = rules.get(field)
        ok = selector and css_exists(soup, selector)
        if ok:
            score += weight
        details[field] = ok

    return score, details


def validate_anime_page(html, rules, context):
    soup = BeautifulSoup(html, "html.parser")
    score = 0
    details = {}

    # container
    sel = rules.get("episodes_container")
    ok = sel and css_exists(soup, sel)
    if ok:
        score += WEIGHTS["anime_page"]["episodes_container"]
    details["episodes_container"] = ok

    # links
    sel = rules.get("episode_link")
    ok = sel and css_exists(soup, sel)
    if ok:
        score += WEIGHTS["anime_page"]["episode_link"]
    details["episode_link"] = ok

    # contexto JS
    if context.get("anime_page", {}).get("has_js_episodes"):
        if not ok:
            details["js_warning"] = "Página parece JS, links HTML não detectados"

    return score, details


def validate_episode_page(html, rules, context):
    soup = BeautifulSoup(html, "html.parser")
    score = 0
    details = {}

    # iframe
    sel = rules.get("player_iframe")
    ok = sel and css_exists(soup, sel)
    if ok:
        score += WEIGHTS["episode_page"]["player_iframe"]
    details["player_iframe"] = ok

    # atributo criptografado
    attr = rules.get("encrypted_attribute")
    ok = attr and attr_exists(soup, attr)
    if ok:
        score += WEIGHTS["episode_page"]["encrypted_attribute"]
    details["encrypted_attribute"] = ok

    # blogger
    pattern = rules.get("blogger_pattern")
    ok = pattern and regex_exists(html, pattern)
    if ok:
        score += WEIGHTS["episode_page"]["blogger_pattern"]
    details["blogger_pattern"] = ok

    # contexto
    if context.get("episode_page", {}).get("has_blogger"):
        if not ok:
            details["blogger_hint"] = "Indícios de Blogger detectados no HTML"

    return score, details


# =============================
# ENTRYPOINT
# =============================
def validate(page_type, html, rules, context=None, base_url=None):
    context = context or {}

    if page_type == "anime_list_page":
        score, details = validate_anime_list(html, rules)

    elif page_type == "anime_page":
        score, details = validate_anime_page(html, rules, context)

    elif page_type == "episode_page":
        score, details = validate_episode_page(html, rules, context)

    else:
        return {
            "valid": False,
            "score": 0,
            "error": "Tipo de página desconhecido"
        }

    return {
        "valid": score >= PASS_SCORE,
        "score": score,
        "details": details
    }