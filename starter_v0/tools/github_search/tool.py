from __future__ import annotations

from typing import Any

import requests

from tools._shared import TIMEOUT, err


def search_github_issues(query: str = "", max_results: int = 5) -> dict[str, Any]:
    try:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 10:
            raise ValueError("max_results must be an integer from 1 to 10")

        response = requests.get(
            "https://api.github.com/search/issues",
            params={"q": query.strip(), "per_page": max_results},
            headers={"Accept": "application/vnd.github+json"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        items = [{
            "title": item.get("title") or "(untitled)",
            "url": item.get("html_url") or "",
            "source": "github.com",
            "summary": (item.get("body") or "").strip()[:1000],
            "state": item.get("state"),
        } for item in data.get("items", [])[:max_results]]
        return {
            "tool": "github_search",
            "query": query.strip(),
            "total_count": data.get("total_count", len(items)),
            "items": items,
        }
    except Exception as exc:
        return err("github_search", exc)