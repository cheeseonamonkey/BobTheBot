from urllib.parse import parse_qs, urlparse

from bobthebot.backends.dreambot import DreamBotBridgeBackend
from bobthebot.models import EntityRef


def test_dreambot_interact_url_encoding(monkeypatch):
    seen = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(url, timeout):
        seen["url"] = url
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    backend = DreamBotBridgeBackend("http://127.0.0.1:19132", timeout=4)
    result = backend.interact(EntityRef(kind="object", name="Copper rock", action="Mine", radius=12))
    assert result.ok is True

    parsed = urlparse(seen["url"])
    query = parse_qs(parsed.query)
    assert parsed.path == "/api/interact"
    assert query["type"] == ["object"]
    assert query["name"] == ["Copper rock"]
    assert query["action"] == ["Mine"]
    assert query["radius"] == ["12"]
    assert seen["timeout"] == 4


def test_dreambot_inventory_and_skills_models(monkeypatch):
    responses = {
        "/api/inventory": {"items": [{"name": "Tin ore", "id": 438, "amount": 2, "slot": 4}]},
        "/api/skills": {"mining": {"level": 5, "xp": 388, "boosted": 6}},
    }

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            import json

            return json.dumps(self.payload).encode()

    def fake_urlopen(url, timeout):
        from urllib.parse import urlparse

        return FakeResponse(responses[urlparse(url).path])

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    backend = DreamBotBridgeBackend()

    assert backend.inventory().to_dict()["items"][0]["name"] == "Tin ore"
    assert backend.skills().to_dict()["mining"]["boosted"] == 6


def test_dreambot_models_tolerate_malformed_numbers(monkeypatch):
    responses = {
        "/api/inventory": {"items": [{"name": None, "id": None, "amount": "bad", "slot": "3"}]},
        "/api/skills": {"mining": {"level": None, "xp": "bad", "boosted": "7"}},
    }

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            import json

            return json.dumps(self.payload).encode()

    def fake_urlopen(url, timeout):
        from urllib.parse import urlparse

        return FakeResponse(responses[urlparse(url).path])

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    backend = DreamBotBridgeBackend()

    item = backend.inventory().to_dict()["items"][0]
    skill = backend.skills().to_dict()["mining"]
    assert item["item_id"] == -1
    assert item["amount"] == 1
    assert item["slot"] == 3
    assert skill["level"] == 0
    assert skill["xp"] == 0
    assert skill["boosted"] == 7
