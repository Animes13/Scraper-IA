# ia/rule_engine.py
# -*- coding: utf-8 -*-

from utils.storage import load_json, save_json
from ia.memory import update_score, get_best_rules

RULES_PATH = "rules/goyabu.json"


# ======================================
# 📥 Carrega regras atuais
# ======================================
def load_rules():
    return load_json(RULES_PATH, default={})


def decide_rules(context, current_rules, generated_rules):
    """
    Decide quais regras aceitar com base em score e histórico
    """
    trusted = get_trusted_rules(context)

    final = {}

    for k, v in generated_rules.items():
        # Se nunca existiu → aceita
        if k not in current_rules:
            final[k] = v
            continue

        # Se já existe e é confiável → mantém
        if k in trusted:
            final[k] = current_rules[k]
            continue

        # Se mudou → aceita tentativa
        if current_rules.get(k) != v:
            final[k] = v

    return final


# ======================================
# 🧠 Avalia novas regras
# ======================================
def evaluate_and_merge(context, new_rules, success=True):
    """
    Decide se novas regras devem substituir as atuais
    baseado em score e histórico
    """

    rules = load_rules()
    updated = False

    for key, value in new_rules.items():
        score_key = f"{context}:{key}"

        # Atualiza score
        update_score(score_key, success)

        # Se a regra não existe, entra
        if key not in rules:
            rules[key] = value
            updated = True
            continue

        # Se mudou o valor → comparar
        if rules[key] != value:
            rules[key] = value
            updated = True

    if updated:
        save_json(RULES_PATH, rules)

    return updated


# ======================================
# 🏆 Retorna regras confiáveis
# ======================================
def get_trusted_rules(context, min_score=1):
    """
    Retorna apenas regras que já funcionaram antes
    """
    best = get_best_rules(min_score)
    rules = load_rules()

    trusted = {}

    for k, v in rules.items():
        score_key = f"{context}:{k}"
        if score_key in best:
            trusted[k] = v

    return trusted
