"""Browser headers for the static site, including its existing inline scripts."""

import base64
import hashlib
import re
from pathlib import Path

from starlette.datastructures import MutableHeaders


class SecurityHeaders:
    def __init__(self, app, *, site_dir: Path):
        self.app = app
        hashes = set()
        for page in site_dir.glob("*.html"):
            for script in re.findall(r"<script\b[^>]*>(.*?)</script>", page.read_text(), re.S | re.I):
                digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
                hashes.add(f"'sha256-{digest}'")
        scripts = " ".join(["'self'", *sorted(hashes)])
        self.policy = (
            f"default-src 'self'; script-src {scripts}; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self' wss://the-cabin-api.fly.dev ws://127.0.0.1:8080; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Content-Security-Policy"] = self.policy
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["X-Frame-Options"] = "DENY"
            await send(message)

        await self.app(scope, receive, send_headers)
