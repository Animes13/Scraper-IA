# ia/rule_engine.py
# -*- coding: utf-8 -*-

from utils.storage import load_json, save_json
from utils.validator import selector_has_results
from ia.memory import update_score, get_best_rules

RULES_PATH = "rules/goyabu.json"


def load_rules():
    return load_json(RULES_PATH, default={})


# ======================================
# 🧠 Decide regras com validação REAL
# ======================================
def decide_rules(context, current_rules, generated_rules, html):
    """
    Decide quais regras aceitar:
    - histórico
    - score
    - validação no HTML real
    """
    trusted = get_trusted_rules(context)
    final = {}

    for key, value in generated_rules.items():

        # 🔎 Validação de seletores CSS
        if key.endswith(("_card", "_button", "_iframe", "_link")):
            if not selector_has_results(html, value, min_results=1):
                continue  # regra inútil

        # 🆕 Regra nova
        if key not in current_rules:
            final[key] = value
            continue

        # ⭐ Regra confiável → mantém
        if key in trusted:
            final[key] = current_rules[key]
            continue

        # 🔁 Tentativa de melhoria
        if current_rules.get(key) != value:
            final[key] = value

    return final


# ======================================
# 📈 Avaliação por score
# ======================================
def evaluate_and_merge(context, new_rules, success=True):
    rules = load_rules()
    updated = False

    for key, value in new_rules.items():
        score_key = f"{context}:{key}"
        update_score(score_key, success)

        if rules.get(key) != value:
            rules[key] = value
            updated = True

    if updated:
        save_json(RULES_PATH, rules)

    return updated


# ======================================
# 🏆 Regras confiáveis
# ======================================
def get_trusted_rules(context, min_score=1):
    best = get_best_rules(min_score)
    rules = load_rules()

    trusted = {}
    for k, v in rules.items():
        if f"{context}:{k}" in best:
            trusted[k] = v

    return trusted
