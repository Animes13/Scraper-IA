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
    if not selector:
        return False
    try:
        return bool(soup.select(selector))
    except Exception:
        return False


def attr_exists(soup, attr):
    """
    Aceita:
    - nome de atributo: data-player
    - seletor CSS completo: div[data-player], .btn[data-src]
    """
    if not attr:
        return False

    # Se parecer seletor CSS completo
    if any(c in attr for c in [" ", ".", "[", ">", "#", ":"]):
        try:
            return bool(soup.select(attr))
        except Exception:
            return False

    # Caso seja apenas nome de atributo
    try:
        return bool(soup.select(f"[{attr}]"))
    except Exception:
        return False


def regex_exists(html, pattern):
    if not pattern:
        return False
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
        ok = css_exists(soup, selector)
        if ok:
            score += weight
        details[field] = ok

    return score, details


def validate_anime_page(html, rules, context):
    soup = BeautifulSoup(html, "html.parser")
    score = 0
    details = {}

    # container de episódios
    sel = rules.get("episodes_container")
    ok_container = css_exists(soup, sel)
    if ok_container:
        score += WEIGHTS["anime_page"]["episodes_container"]
    details["episodes_container"] = ok_container

    # links de episódios
    sel = rules.get("episode_link")
    ok_links = css_exists(soup, sel)
    if ok_links:
        score += WEIGHTS["anime_page"]["episode_link"]
    details["episode_link"] = ok_links

    # alerta de JS
    if context.get("anime_page", {}).get("has_js_episodes"):
        if not ok_links:
            details["js_warning"] = "Episódios parecem carregados via JavaScript"

    return score, details


def validate_episode_page(html, rules, context):
    soup = BeautifulSoup(html, "html.parser")
    score = 0
    details = {}

    # iframe do player
    sel = rules.get("player_iframe")
    ok_iframe = css_exists(soup, sel)
    if ok_iframe:
        score += WEIGHTS["episode_page"]["player_iframe"]
    details["player_iframe"] = ok_iframe

    # atributo criptografado ou seletor equivalente
    attr = rules.get("encrypted_attribute")
    ok_attr = attr_exists(soup, attr)
    if ok_attr:
        score += WEIGHTS["episode_page"]["encrypted_attribute"]
    details["encrypted_attribute"] = ok_attr

    # padrão blogger / googlevideo
    pattern = rules.get("blogger_pattern")
    ok_blog = regex_exists(html, pattern)
    if ok_blog:
        score += WEIGHTS["episode_page"]["blogger_pattern"]
    details["blogger_pattern"] = ok_blog

    # hint contextual
    if context.get("episode_page", {}).get("has_blogger"):
        if not ok_blog:
            details["blogger_hint"] = "Indícios de Blogger/GoogleVideo detectados"

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