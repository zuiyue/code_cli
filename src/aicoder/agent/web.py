"""Web fetch tool — fetches web pages. Search is model-knowledge or fetch-based."""

import urllib.request
import urllib.error
import re


def web_fetch(url: str, max_chars: int = 5000) -> str:
    """Fetch a web page and return text content."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        return f"Fetch failed: {e}"


def web_search(query: str, num_results: int = 3) -> str:
    """Search the web — delegates to DuckDuckGo or returns search URL."""
    # Try instant answer API first
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&no_redirect=1"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            import json
            data = json.loads(resp.read())
        results = []
        if data.get("AbstractText"):
            results.append(f"**{data.get('Heading', query)}**: {data['AbstractText']}")
        for topic in data.get("RelatedTopics", [])[:num_results]:
            text = topic.get("Text", "")
            if text:
                results.append(f"- {text}")
        if results:
            return "\n\n".join(results)
    except Exception:
        pass

    # Fallback: tell user how to search
    q = urllib.parse.quote(query)
    return (
        f"Search URL: https://www.google.com/search?q={q}\n"
        f"Use /fetch <url> to load a specific page, or check these sources:\n"
        f"- Python docs: https://docs.python.org/3/search.html?q={q}\n"
    )