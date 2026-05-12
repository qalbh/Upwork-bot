import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.config_loader import get_settings
from src.utils.human_behavior import random_delay
from src.utils.stealth import STEALTH_SCRIPT
from src.utils.logger import get_logger

log = get_logger()

SESSION_FILE = Path(__file__).parent.parent.parent / "data" / "upwork_session.json"


class SessionManager:
    def __init__(self):
        self.settings = get_settings()
        self._playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None

    async def start(self) -> BrowserContext:
        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            channel="chrome",
            headless=False,
            ignore_default_args=["--enable-automation"],
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-service-autorun",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-ipc-flooding-protection",
                "--lang=en-US",
                "--start-maximized",
            ],
        )

        context_args = {
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "viewport": None,
        }

        # Load saved session if it exists — skips login on every run after first
        if SESSION_FILE.exists():
            context_args["storage_state"] = str(SESSION_FILE)
            log.info("session_loaded", file=str(SESSION_FILE))
        else:
            log.info("no_session_found", message="Will prompt for manual login")

        self._context = await self._browser.new_context(**context_args)
        await self._context.add_init_script(STEALTH_SCRIPT)

        log.info("browser_started")
        return self._context

    async def login_if_needed(self, page: Page):
        await page.goto("https://www.upwork.com", wait_until="domcontentloaded")
        await random_delay(2, 4)

        # Handle Cloudflare challenge if it appears
        await self._handle_cloudflare(page)

        if await self._is_logged_in(page):
            log.info("already_logged_in")
            return

        log.info("manual_login_required",
                 message="=== Please log in to Upwork manually in the browser. Bot continues automatically once logged in. ===")

        # Wait for user to log in (up to 5 minutes)
        await page.wait_for_url("**/nx/find-work**", timeout=300000)

        # Save session so next run is automatic
        SESSION_FILE.parent.mkdir(exist_ok=True)
        await self._context.storage_state(path=str(SESSION_FILE))
        log.info("session_saved", file=str(SESSION_FILE))

    async def _handle_cloudflare(self, page: Page):
        try:
            cf = await page.wait_for_selector(
                "text=Verify you are human",
                timeout=4000,
            )
            if cf:
                log.info("cloudflare_detected",
                         message="=== Cloudflare challenge detected. Please click the checkbox in the browser. ===")
                # Wait up to 2 minutes for user to solve it
                await page.wait_for_function(
                    "() => !document.body.innerText.includes('Verify you are human')",
                    timeout=120000,
                )
                log.info("cloudflare_passed")
                await random_delay(2, 3)
        except Exception:
            pass  # No Cloudflare challenge — continue normally

    async def _is_logged_in(self, page: Page) -> bool:
        try:
            await page.wait_for_selector(
                "[data-test='nav-find-work'], a[href*='find-work'], #nav-find-work",
                timeout=5000,
            )
            return True
        except Exception:
            return False

    async def stop(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
