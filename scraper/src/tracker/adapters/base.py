import asyncio
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


@dataclass
class Context:
    client: httpx.AsyncClient
    today: date
    cache_dir: Path
    ats_hints: dict = field(default_factory=dict)  # company id -> ATS seen on its rendered page
    browser_lock: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(3))
    _browser: object = None
    _pw: object = None

    async def browser(self):
        """Lazily start one shared headless Chromium."""
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                args=["--disable-blink-features=AutomationControlled", "--disable-http2"]
            )
        return self._browser

    async def new_page(self):
        browser = await self.browser()
        context = await browser.new_context(
            user_agent=UA, locale="en-AU", timezone_id="Australia/Sydney", viewport={"width": 1366, "height": 900}
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return await context.new_page()

    async def close(self):
        if self._browser is not None:
            await self._browser.close()
            await self._pw.stop()


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": UA, "Accept": "application/json, text/html;q=0.9"},
        follow_redirects=True,
        timeout=httpx.Timeout(30, connect=15),
        transport=httpx.AsyncHTTPTransport(retries=2),
    )


async def get_json(client: httpx.AsyncClient, url: str, **kw):
    r = await client.get(url, **kw)
    r.raise_for_status()
    return r.json()


def parse_date(value) -> date | None:
    """Parse ISO strings, epoch millis, or Workday-style 'Posted 3 Days Ago'."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 1e11 else value).date()
    s = str(value).strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%B %d, %Y", "%d %B %Y", "%d/%m/%Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    low = s.lower()
    today = date.today()
    if "today" in low:
        return today
    if "yesterday" in low:
        return today - timedelta(days=1)
    m = re.search(r"(\d+)\+?\s*days?\s*ago", low)
    if m:
        return today - timedelta(days=int(m.group(1)))
    return None
