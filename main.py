# main.py
# -*- coding: utf-8 -*-

from scraper.anime_list import get_anime_list
from scraper.episode_list import get_episodes
from scraper.stream_resolver import StreamResolver

from utils.storage import save_json, load_json
from utils.validator import selector_has_results
from utils.sanitizer import sanitize_html

from scraper.fetch import fetch_html
from ia.analyzer import analyze_and_update_rules

RULES_PATH = "rules/goyabu.json"
DATA_PATH = "data/goyabu_animes.json"

BASE_LIST_URL = "https://goyabu.io/lista-de-animes"


def main():
    rules = load_json(RULES_PATH, default={})
    resolver = StreamResolver()

    final_data = {}

    page = 1
    while True:
        print(f"[MAIN] Página {page}")
        animes = get_anime_list(page)

        if not animes:
            break

        for anime in animes:
            name = anime["name"]
            url = anime["url"]

            print(f"  ▶ Anime: {name}")

            try:
                episodes = get_episodes(url)
            except Exception:
                episodes = []

            if not episodes:
                print("    ❌ Episódios não encontrados → acionando IA")

                html = fetch_html(url)
                clean = sanitize_html(html)

                analyze_and_update_rules(
                    html=clean,
                    context="episode_list"
                )

                episodes = get_episodes(url)

            anime_entry = {
                "url": url,
                "episodes": {}
            }

            for ep in episodes:
                ep_num = str(ep["episode"])
                ep_url = ep["url"]

                print(f"    🎬 EP {ep_num}")

                stream = resolver.resolve(ep_url)

                if not stream:
                    print("      ❌ Stream falhou → IA")

                    html = fetch_html(ep_url)
                    clean = sanitize_html(html)

                    analyze_and_update_rules(
                        html=clean,
                        context="stream"
                    )

                    stream = resolver.resolve(ep_url)

                if stream:
                    anime_entry["episodes"][ep_num] = stream

            if anime_entry["episodes"]:
                final_data[name] = anime_entry

        page += 1

    save_json(DATA_PATH, final_data)
    print(f"[MAIN] Finalizado. {len(final_data)} animes salvos.")


if __name__ == "__main__":
    main()
