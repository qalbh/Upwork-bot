import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.config_loader import get_settings
from src.utils.human_behavior import random_delay, short_delay, type_like_human
from src.utils.logger import get_logger

log = get_logger()

STATE_PATH = Path(__file__).parent.parent.parent / "data" / "browser_state.json"


class SessionManager:
    def __init__(self):
        self.settings = get_settings()
        self._playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None

    async def start(self) -> BrowserContext:
        self._playwright = await async_playwright().start()

        launch_args = {
            "headless": False,
            "channel": "chrome",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        }

        self._browser = await self._playwright.chromium.launch(**launch_args)

        context_args = {
            "viewport": {"width": 1280, "height": 800},
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

        if STATE_PATH.exists():
            context_args["storage_state"] = str(STATE_PATH)
            log.info("session_restored", path=str(STATE_PATH))
        else:
            log.info("session_fresh", reason="no saved state found")

        self._context = await self._browser.new_context(**context_args)

        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)

        return self._context

    async def login_if_needed(self, page: Page):
        if STATE_PATH.exists():
            return

        log.info("login_start")
        settings = self.settings

        await page.goto(settings.app.upwork.homepage)
        await random_delay(3, 6)

        await page.click('a[href*="login"]')
        await random_delay(2, 4)

        await type_like_human(page, 'input[name="login[username]"]', settings.upwork_email)
        await short_delay()
        await page.keyboard.press("Enter")
        await random_delay(2, 4)

        await type_like_human(page, 'input[name="login[password]"]', settings.upwork_password)
        await short_delay()
        await page.keyboard.press("Enter")

        await page.wait_for_url("**/nx/find-work**", timeout=30000)
        await self.save_state()
        log.info("login_success")

    async def save_state(self):
        STATE_PATH.parent.mkdir(exist_ok=True)
        await self._context.storage_state(path=str(STATE_PATH))
        log.info("session_saved", path=str(STATE_PATH))

    async def stop(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
