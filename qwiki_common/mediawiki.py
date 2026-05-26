import json
import time
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "qwiki-eval/1.0"
REQUEST_DELAY = 0.1


class MediaWikiClient:
    def __init__(self):
        self._last_request_time = 0

    def _get(self, params):
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)

        url = f"{WIKIPEDIA_API_URL}?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        self._last_request_time = time.time()
        return data

    def search(self, query, limit=5):
        data = self._get({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        })
        results = data.get("query", {}).get("search", [])
        return [
            {"title": r["title"], "pageid": r["pageid"], "snippet": r.get("snippet", "")}
            for r in results
        ]

    def get_extract(self, title):
        data = self._get({
            "action": "query",
            "titles": title,
            "prop": "extracts|info",
            "explaintext": "true",
            "inprop": "url",
            "format": "json",
        })
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        return {
            "title": title,
            "extract": page.get("extract", ""),
            "url": page.get("fullurl", f"https://en.wikipedia.org/wiki/{quote(title)}"),
        }

    def page_exists(self, title):
        data = self._get({
            "action": "query",
            "titles": title,
            "format": "json",
        })
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        return "missing" not in page and int(page.get("pageid", -1)) > 0
