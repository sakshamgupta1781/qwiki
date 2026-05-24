import json
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.anthropic.com/v1"
API_VERSION = "2023-06-01"
MAX_RETRIES = 3


class ClaudeClient:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def _headers(self):
        return {
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }

    def _request(self, method, path, body=None, timeout=60):
        url = f"{API_URL}{path}"
        data = json.dumps(body).encode() if body else None
        req = Request(url, data=data, headers=self._headers(), method=method)

        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                with urlopen(req, timeout=timeout) as resp:
                    return json.loads(resp.read())
            except HTTPError as e:
                if e.code == 429:
                    retry_after = int(e.headers.get("retry-after", 2 ** attempt))
                    last_err = e
                    time.sleep(retry_after)
                    continue
                body_text = e.read().decode(errors="replace")
                raise RuntimeError(f"Claude API {e.code}: {body_text[:300]}") from e
        raise RuntimeError(f"Rate limited after {MAX_RETRIES} retries") from last_err

    def list_models(self):
        data = self._request("GET", "/models")
        models = []
        for m in data.get("data", []):
            model_id = m.get("id", "")
            if "claude" in model_id:
                models.append(model_id)
        return sorted(models)

    def complete(self, system, user_message, max_tokens=4096):
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0,
            "system": system,
            "messages": [{"role": "user", "content": user_message}],
        }
        data = self._request("POST", "/messages", body)
        return data["content"][0]["text"]
