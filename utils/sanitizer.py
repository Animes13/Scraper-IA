# utils/sanitizer.py
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup


def sanitize_html(html):
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    return soup.prettify()
