# ia/analyzer.py
# -*- coding: utf-8 -*-

from ia.dom_brain import analyze_dom
from ia.js_brain import analyze_js
from ia.rule_engine import decide_rules
from ia.trainer import training_cycle
from utils.storage import load_json, save_json

RULES_PATH = "rules/goyabu.json"


def analyze_and_update_rules(html, context):
    """
    Orquestrador da IA própria
    context: episode_list | stream | anime_list
    """
    print(f"[IA] Analisando contexto: {context}")

    current_rules = load_json(RULES_PATH, default={})
    generated_rules = {}

    # 🧠 1. Analisa DOM
    dom_rules = analyze_dom(html, context)
    if dom_rules:
        generated_rules.update(dom_rules)

    # 🧠 2. Analisa JavaScript
    js_rules = analyze_js(html, context)
    if js_rules:
        generated_rules.update(js_rules)

    if not generated_rules:
        print("[IA] Nenhuma regra candidata encontrada")
        training_cycle(context, html, current_rules, success=False)
        return False

    # 🧠 3. Decide se as regras são boas
    final_rules = decide_rules(context, current_rules, generated_rules)

    if not final_rules:
        print("[IA] Regras rejeitadas pelo motor de decisão")
        training_cycle(context, html, generated_rules, success=False)
        return False

    # 💾 4. Salva regras
    current_rules.update(final_rules)
    save_json(RULES_PATH, current_rules)

    # 🎓 5. Treina por sucesso
    training_cycle(context, html, final_rules, success=True)

    print("[IA] Regras atualizadas com sucesso:", final_rules)
    return True
