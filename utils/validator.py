# utils/validator.py
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup


def selector_has_results(html: str, selector: str, min_results: int = 1) -> bool:
    """
    Verifica se um seletor CSS retorna resultados suficientes
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        return len(soup.select(selector)) >= min_results
    except Exception:
        return False
