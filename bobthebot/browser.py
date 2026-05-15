from __future__ import annotations

import asyncio
import base64
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

import websockets

from .config import BotConfig


class CdpClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._next_id = 0
        self._ws = None
        self.events: list[dict[str, Any]] = []

    async def __aenter__(self):
        self._ws = await websockets.connect(self.ws_url)
        return self

    async def __aexit__(self, *args):
        if self._ws is not None:
            await self._ws.close()

    async def send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("CDP client is not connected")
        self._next_id += 1
        msg_id = self._next_id
        await self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            frame = json.loads(await self._ws.recv())
            if frame.get("id") == msg_id:
                if "error" in frame:
                    raise RuntimeError(frame["error"].get("message", str(frame["error"])))
                return frame.get("result", {})
            self.events.append(frame)


class BrowserController:
    def __init__(self, config: BotConfig):
        self.config = config

    def websocket_url(self) -> str | None:
        for endpoint in self._devtools_endpoints():
            if ws_url := self._websocket_from_endpoint(endpoint):
                return ws_url
        return None

    def _devtools_endpoints(self) -> list[str]:
        base = f"http://127.0.0.1:{self.config.browser_debug_port}"
        return [f"{base}/json", f"{base}/json/version"]

    def _websocket_from_endpoint(self, endpoint: str) -> str | None:
        try:
            with urllib.request.urlopen(endpoint, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
        except OSError:
            return None
        if isinstance(data, dict):
            return self._websocket_from_page(data)
        if isinstance(data, list):
            pages = sorted(data, key=lambda page: page.get("type") != "page")
            for page in pages:
                if ws_url := self._websocket_from_page(page):
                    return ws_url
        return None

    def _websocket_from_page(self, page: dict[str, Any]) -> str | None:
        ws_url = page.get("webSocketDebuggerUrl")
        return str(ws_url) if ws_url else None

    def wait_for_websocket_url(self, timeout: float = 10.0) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if ws_url := self.websocket_url():
                return ws_url
            time.sleep(0.25)
        raise RuntimeError("Browser DevTools websocket is not available")

    async def navigate(self, url: str) -> dict[str, Any]:
        async with CdpClient(self.wait_for_websocket_url()) as cdp:
            await cdp.send("Page.enable")
            await cdp.send("Page.navigate", {"url": url})
            await asyncio.sleep(1.0)
            return await self.page_snapshot(cdp)

    async def page_snapshot(self, cdp: CdpClient | None = None) -> dict[str, Any]:
        owns_client = cdp is None
        if cdp is None:
            cdp = CdpClient(self.wait_for_websocket_url())
            await cdp.__aenter__()
        try:
            title = await self.evaluate("document.title", cdp=cdp)
            url = await self.evaluate("location.href", cdp=cdp)
            text = await self.evaluate("document.body ? document.body.innerText : ''", cdp=cdp)
            return {"title": title, "url": url, "text": text}
        finally:
            if owns_client:
                await cdp.__aexit__(None, None, None)

    async def evaluate(self, expression: str, cdp: CdpClient | None = None) -> Any:
        owns_client = cdp is None
        if cdp is None:
            cdp = CdpClient(self.wait_for_websocket_url())
            await cdp.__aenter__()
        try:
            result = await cdp.send("Runtime.evaluate", {"expression": expression, "returnByValue": True})
            value = result.get("result", {})
            return value.get("value")
        finally:
            if owns_client:
                await cdp.__aexit__(None, None, None)

    async def fill_first(self, selectors: list[str], text: str) -> bool:
        expression = """
        (() => {
          const selectors = %s;
          const text = %s;
          for (const selector of selectors) {
            const el = document.querySelector(selector);
            if (!el) continue;
            el.focus();
            el.value = text;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            return true;
          }
          return false;
        })()
        """ % (json.dumps(selectors), json.dumps(text))
        return bool(await self.evaluate(expression))

    async def click_first(self, selectors: list[str]) -> bool:
        expression = """
        (() => {
          const selectors = %s;
          for (const selector of selectors) {
            const el = document.querySelector(selector);
            if (!el) continue;
            el.click();
            return true;
          }
          return false;
        })()
        """ % json.dumps(selectors)
        return bool(await self.evaluate(expression))

    async def screenshot(self, path: Path) -> Path:
        async with CdpClient(self.wait_for_websocket_url()) as cdp:
            result = await cdp.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(result["data"]))
        return path
