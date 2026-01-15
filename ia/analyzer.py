# ia/analyzer.py
# -*- coding: utf-8 -*-

from ia.dom_brain import analyze_dom
from ia.js_brain import analyze_js
from ia.rule_engine import decide_rules
from ia.trainer import training_cycle
from utils.storage import load_json, save_json

RULES_PATH = "rules/goyabu.json"


def analyze_and_update_rules(html, context):
    print(f"[IA] Analisando contexto: {context}")

    current_rules = load_json(RULES_PATH, default={})
    generated_rules = {}

    # 🧠 DOM
    dom_rules = analyze_dom(html)
    generated_rules.update(dom_rules or {})

    # 🧠 JS
    js_rules = analyze_js(html)
    generated_rules.update(js_rules or {})

    if not generated_rules:
        print("[IA] Nenhuma regra candidata")
        training_cycle(context, html, current_rules, success=False)
        return False

    # 🧠 Decisão com validação real
    final_rules = decide_rules(
        context=context,
        current_rules=current_rules,
        generated_rules=generated_rules,
        html=html
    )

    if not final_rules:
        print("[IA] Regras rejeitadas")
        training_cycle(context, html, generated_rules, success=False)
        return False

    # 💾 Salva
    current_rules.update(final_rules)
    save_json(RULES_PATH, current_rules)

    # 🎓 Treina
    training_cycle(context, html, final_rules, success=True)

    print("[IA] Regras aplicadas:", final_rules)
    return True
