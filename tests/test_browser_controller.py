from bobthebot.browser import BrowserController
from bobthebot.config import BotConfig

from conftest import FakeResponseCtx


def test_websocket_url_prefers_page_endpoint_over_browser_endpoint(monkeypatch, tmp_path):
    calls = []

    def fake_urlopen(url, timeout):
        calls.append(url)
        if url.endswith("/json"):
            return FakeResponseCtx.json(
                [
                    {"type": "service_worker", "webSocketDebuggerUrl": "ws://worker"},
                    {"type": "page", "webSocketDebuggerUrl": "ws://page"},
                ]
            )
        return FakeResponseCtx.json({"webSocketDebuggerUrl": "ws://browser"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    url = BrowserController(BotConfig(root=tmp_path, browser_debug_port=9333)).websocket_url()

    assert url == "ws://page"
    assert calls == ["http://127.0.0.1:9333/json"]
