"""
Thin client for the Resident History API (services/history_service.py).

Kept deliberately simple -- the service itself has no injected failures
per its own docstring, but network calls can still time out or the
process can still be slow to come up, so calls are wrapped rather than
assumed to succeed.
"""
import json
import urllib.request
import urllib.error


class HistoryClientError(Exception):
    pass


class HistoryClient:
    def __init__(self, base_url="http://127.0.0.1:8083", timeout=5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path):
        url = f"{self.base_url}{path}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise HistoryClientError(f"HTTP {e.code} from {url}: {body}") from e
        except urllib.error.URLError as e:
            raise HistoryClientError(f"Could not reach {url}: {e.reason}") from e

    def health(self):
        return self._get("/health")

    def full_record(self, resident_ref):
        return self._get(f"/residents/{resident_ref}")

    def household(self, resident_ref):
        return self._get(f"/residents/{resident_ref}/household")

    def events(self, resident_ref):
        return self._get(f"/residents/{resident_ref}/events")
