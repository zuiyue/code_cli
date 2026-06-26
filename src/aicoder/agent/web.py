"""Web search and fetch tool for the agent."""

import urllib.request
import urllib.error
import json


def web_search(query: str, num_results: int = 3) -> str:
    """Search the web using DuckDuckGo and return results."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={"User-Agent": "aicoder/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        results = []
        for topic in data.get("RelatedTopics", [])[:num_results]:
            text = topic.get("Text", "")
            url = topic.get("FirstURL", "")
            if text:
                results.append(f"- {text} ({url})")
        if not results and data.get("AbstractText"):
            results.append(f"- {data['AbstractText']} ({data.get('AbstractURL', '')})")
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search failed: {e}"


def web_fetch(url: str, max_chars: int = 5000) -> str:
    """Fetch a web page and return its text content."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "aicoder/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Simple HTML to text — strip tags
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        return f"Fetch failed: {e}"
