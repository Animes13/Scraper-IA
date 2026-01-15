# ia/trainer.py
# -*- coding: utf-8 -*-

from ia.memory import log_success, log_failure
from ia.rule_engine import evaluate_and_merge


# ======================================
# 🎓 Treino por sucesso
# ======================================
def train_success(context, rules_used):
    """
    Chamar quando o scraper FUNCIONAR
    """
    log_success(context, rules_used)

    # Aumenta score das regras usadas
    evaluate_and_merge(
        context=context,
        new_rules=rules_used,
        success=True
    )


# ======================================
# 🧪 Treino por falha
# ======================================
def train_failure(context, html, attempted_rules):
    """
    Chamar quando o scraper FALHAR
    """
    log_failure(context, html, attempted_rules)

    # Penaliza regras ruins
    evaluate_and_merge(
        context=context,
        new_rules=attempted_rules,
        success=False
    )


# ======================================
# 🔁 Ciclo completo de treino
# ======================================
def training_cycle(context, html, rules_used, success):
    """
    Função universal de treino
    """
    if success:
        train_success(context, rules_used)
    else:
        train_failure(context, html, rules_used)
