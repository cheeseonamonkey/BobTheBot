import json

from bobthebot.browser import BrowserController
from bobthebot.config import BotConfig


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


def test_websocket_url_prefers_page_endpoint_over_browser_endpoint(monkeypatch, tmp_path):
    calls = []

    def fake_urlopen(url, timeout):
        calls.append(url)
        if url.endswith("/json"):
            return FakeResponse(
                [
                    {"type": "service_worker", "webSocketDebuggerUrl": "ws://worker"},
                    {"type": "page", "webSocketDebuggerUrl": "ws://page"},
                ]
            )
        return FakeResponse({"webSocketDebuggerUrl": "ws://browser"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    url = BrowserController(BotConfig(root=tmp_path, browser_debug_port=9333)).websocket_url()

    assert url == "ws://page"
    assert calls == ["http://127.0.0.1:9333/json"]
