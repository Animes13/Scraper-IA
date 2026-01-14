# main.py
# -*- coding: utf-8 -*-

from scraper.anime_list import get_anime_list
from scraper.episode_list import get_episodes
from scraper.stream_resolver import StreamResolver

from utils.storage import save_json, load_json
from utils.sanitizer import sanitize_html

from scraper.fetch import fetch_html
from ia.analyzer import analyze_and_update_rules

RULES_PATH = "rules/goyabu.json"
DATA_PATH = "data/goyabu_animes.json"


def main():
    resolver = StreamResolver()
    final_data = {}

    # 🔒 Proteção anti-loop da IA
    ia_used = {
        "episode_list": False,
        "stream": False
    }

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

            # ===============================
            # EPISÓDIOS
            # ===============================
            try:
                episodes = get_episodes(url)
            except Exception:
                episodes = []

            if not episodes and not ia_used["episode_list"]:
                print("    ❌ Episódios não encontrados → acionando IA")

                old_rules = load_json(RULES_PATH, default={})

                html = fetch_html(url)
                clean = sanitize_html(html)

                ok = analyze_and_update_rules(
                    html=clean,
                    context="episode_list"
                )

                ia_used["episode_list"] = True

                if ok:
                    episodes = get_episodes(url)

                # ❌ IA não resolveu → rollback
                if not episodes:
                    print("    ⛔ IA falhou → revertendo regras")
                    save_json(RULES_PATH, old_rules)

            if not episodes:
                continue

            anime_entry = {
                "url": url,
                "episodes": {}
            }

            # ===============================
            # STREAMS
            # ===============================
            for ep in episodes:
                ep_num = str(ep["episode"])
                ep_url = ep["url"]

                print(f"    🎬 EP {ep_num}")

                stream = resolver.resolve(ep_url)

                if not stream and not ia_used["stream"]:
                    print("      ❌ Stream falhou → acionando IA")

                    old_rules = load_json(RULES_PATH, default={})

                    html = fetch_html(ep_url)
                    clean = sanitize_html(html)

                    ok = analyze_and_update_rules(
                        html=clean,
                        context="stream"
                    )

                    ia_used["stream"] = True

                    if ok:
                        stream = resolver.resolve(ep_url)

                    # ❌ IA não resolveu → rollback
                    if not stream:
                        print("      ⛔ IA falhou → revertendo regras")
                        save_json(RULES_PATH, old_rules)

                if stream:
                    anime_entry["episodes"][ep_num] = stream

            if anime_entry["episodes"]:
                final_data[name] = anime_entry

        page += 1

    save_json(DATA_PATH, final_data)
    print(f"[MAIN] Finalizado. {len(final_data)} animes salvos.")


if __name__ == "__main__":
    main()
