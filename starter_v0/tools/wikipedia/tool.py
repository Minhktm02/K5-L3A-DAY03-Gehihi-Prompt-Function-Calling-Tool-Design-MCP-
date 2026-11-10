from __future__ import annotations

from typing import Any
import requests

from tools._shared import TIMEOUT, err


def wikipedia_search(
    query: str = "",
    lang: str = "en",
    max_results: int = 3,
) -> dict[str, Any]:
    """Search Wikipedia for encyclopedic summaries and reference URLs."""
    clean_query = (query or "").strip()
    if not clean_query:
        return {"tool": "wikipedia", "query": query, "items": []}

    try:
        clean_lang = (lang or "en").lower().strip()
        limit = max(1, min(int(max_results or 3), 10))
        url = f"https://{clean_lang}.wikipedia.org/w/api.php"
        params = {
            "action": "opensearch",
            "search": clean_query,
            "limit": limit,
            "namespace": 0,
            "format": "json",
        }
        headers = {"User-Agent": "AI20k-Research-Agent/1.0 (educational lab)"}
        response = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # OpenSearch format: [search_term, [titles], [descriptions], [urls]]
        titles = data[1] if len(data) > 1 else []
        descriptions = data[2] if len(data) > 2 else []
        urls = data[3] if len(data) > 3 else []

        items = []
        for title, desc, link in zip(titles, descriptions, urls):
            items.append({
                "title": title,
                "summary": desc,
                "url": link,
                "source": f"{clean_lang}.wikipedia.org",
            })

        return {
            "tool": "wikipedia",
            "query": clean_query,
            "lang": clean_lang,
            "items": items,
        }
    except Exception as exc:
        return err("wikipedia", exc)

