import json
import time
import requests
import websockets
import asyncio
import subprocess
from config import *

class OSBCAuth:
    def __init__(self, host="127.0.0.1", port=9222):
        self.host = host
        self.port = port
        self._msg_id = 0

    def _get_ws_url(self):
        try:
            resp = requests.get(f"http://{self.host}:{self.port}/json")
            pages = resp.json()
            # Prefer the first 'page' type target
            for page in pages:
                if page.get("type") == "page":
                    return page["webSocketDebuggerUrl"]
            if pages:
                return pages[0]["webSocketDebuggerUrl"]
        except Exception as e:
            print(f"Error connecting to browser: {e}")
        return None

    async def _send_cmd(self, ws, method, params=None):
        self._msg_id += 1
        payload = {"id": self._msg_id, "method": method, "params": params or {}}
        await ws.send(json.dumps(payload))
        resp = await ws.recv()
        return json.loads(resp)

    async def navigate(self, url):
        url_ws = self._get_ws_url()
        if not url_ws: return False
        async with websockets.connect(url_ws) as ws:
            print(f"Navigating to {url}...")
            await self._send_cmd(ws, "Page.navigate", {"url": url})
            await asyncio.sleep(5) # Allow some load time
            return True

    async def wait_for_selector(self, selector, timeout=20):
        """Wait for an element to appear in the DOM."""
        url_ws = self._get_ws_url()
        if not url_ws: return False
        start_time = time.time()
        async with websockets.connect(url_ws) as ws:
            while time.time() - start_time < timeout:
                js = f'document.querySelector("{selector}") !== null'
                resp = await self._send_cmd(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True})
                if resp.get("result", {}).get("result", {}).get("value") is True:
                    return True
                await asyncio.sleep(1)
        return False

    async def click(self, selector):
        url_ws = self._get_ws_url()
        async with websockets.connect(url_ws) as ws:
            js = f'document.querySelector("{selector}").click()'
            await self._send_cmd(ws, "Runtime.evaluate", {"expression": js})

    async def type(self, selector, text):
        url_ws = self._get_ws_url()
        async with websockets.connect(url_ws) as ws:
            # Use value property for reliability in forms
            js = f'let el = document.querySelector("{selector}"); el.value = "{text}"; el.dispatchEvent(new Event("input", {{ bubbles: true }})); el.dispatchEvent(new Event("change", {{ bubbles: true }}));'
            await self._send_cmd(ws, "Runtime.evaluate", {"expression": js})

    async def screenshot(self, path):
        """Take a screenshot of the current page via CDP."""
        url_ws = self._get_ws_url()
        if not url_ws: 
            print("No WS URL found for screenshot.")
            return False
        try:
            async with websockets.connect(url_ws) as ws:
                print(f"Taking screenshot via CDP to {path}...")
                resp = await self._send_cmd(ws, "Page.captureScreenshot")
                if "error" in resp:
                    print(f"CDP Screenshot Error: {resp['error']}")
                    return False
                data = resp.get("result", {}).get("data")
                if data:
                    import base64
                    with open(path, "wb") as f:
                        f.write(base64.b64decode(data))
                    print(f"Screenshot saved to {path}")
                    return True
                else:
                    print(f"No screenshot data in response: {resp}")
        except Exception as e:
            print(f"Exception taking screenshot: {e}")
        return False

    async def run_registration_flow(self, email, password):
        """Automate the initial steps of OSRS registration."""
        reg_url = "https://secure.runescape.com/m=account-creation/create_account"
        if await self.navigate(reg_url):
            print("Page loaded, waiting for email field...")
            if await self.wait_for_selector("#email"):
                await self.type("#email", email)
                await self.type("#password", password)
                # Note: Captcha and 'Create' button click usually requires manual intervention or advanced solver
                print("Email and Password filled. Please check terminal view for Captcha.")
                return True
        return False

if __name__ == "__main__":
    # Quick test
    auth = OSBCAuth()
    # asyncio.run(auth.run_registration_flow("test@example.com", "Password123!"))
