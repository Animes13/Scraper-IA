# utils/sanitizer.py
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup


def sanitize_html(html: str) -> str:
    """
    Limpa HTML para análise da IA (remove ruído)
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    return soup.prettify()
