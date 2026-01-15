# ia/memory.py
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime


BASE_DIR = "memory"

FILES = {
    "success": "success.json",
    "failures": "failures.json",
    "scores": "scores.json"
}


def _path(name):
    os.makedirs(BASE_DIR, exist_ok=True)
    return os.path.join(BASE_DIR, FILES[name])


def _load(name):
    path = _path(name)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(name, data):
    path = _path(name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ===============================
# 📈 SUCESSO
# ===============================
def register_success(context, rules):
    data = _load("success")
    key = context

    entry = data.get(key, {
        "count": 0,
        "rules": {},
        "last_success": None
    })

    entry["count"] += 1
    entry["last_success"] = datetime.utcnow().isoformat()

    for k, v in rules.items():
        entry["rules"][k] = v

    data[key] = entry
    _save("success", data)


# ===============================
# 📉 FALHA
# ===============================
def register_failure(context, reason="unknown"):
    data = _load("failures")
    key = context

    entry = data.get(key, {
        "count": 0,
        "last_failure": None,
        "reasons": {}
    })

    entry["count"] += 1
    entry["last_failure"] = datetime.utcnow().isoformat()
    entry["reasons"][reason] = entry["reasons"].get(reason, 0) + 1

    data[key] = entry
    _save("failures", data)


# ===============================
# 🧠 SCORE DAS REGRAS
# ===============================
def update_score(rule_key, success=True):
    scores = _load("scores")

    score = scores.get(rule_key, 0)
    score += 1 if success else -1

    scores[rule_key] = score
    _save("scores", scores)


def get_best_rules(min_score=1):
    scores = _load("scores")
    return {
        k: v for k, v in scores.items()
        if v >= min_score
    }
