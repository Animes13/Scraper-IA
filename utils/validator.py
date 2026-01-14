# utils/validator.py
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup


def selector_has_results(html, selector):
    soup = BeautifulSoup(html, "html.parser")
    return bool(soup.select(selector))
