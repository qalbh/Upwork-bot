from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page
from src.config_loader import get_settings
from src.utils.human_behavior import random_delay
from src.utils.stealth import STEALTH_SCRIPT
from src.utils.logger import get_logger

log = get_logger()

BOT_DATA_DIR = Path.home() / ".upwork-bot-data"
SESSION_FILE = Path(__file__).parent.parent.parent / "data" / "upwork_session.json"


class SessionManager:
    def __init__(self):
        self.settings = get_settings()
        self._playwright = None
        self._context: BrowserContext = None

    async def start(self) -> BrowserContext:
        self._playwright = await async_playwright().start()

        BOT_DATA_DIR.mkdir(exist_ok=True)
        SESSION_FILE.parent.mkdir(exist_ok=True)

        lock = BOT_DATA_DIR / "SingletonLock"
        if lock.exists():
            lock.unlink()

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(BOT_DATA_DIR),
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            storage_state=str(SESSION_FILE) if SESSION_FILE.exists() else None,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )

        await self._context.add_init_script(STEALTH_SCRIPT)
        log.info("browser_started")
        return self._context

    async def login_if_needed(self, page: Page):
        await page.goto("https://www.upwork.com", wait_until="domcontentloaded")
        await random_delay(2, 4)

        # Handle Cloudflare — save session immediately after passing
        # so future runs don't ask again
        if await self._handle_cloudflare(page):
            await self._save_session()

        if await self._is_logged_in(page):
            log.info("already_logged_in")
            return

        log.info("manual_login_required",
                 message="=== Please log in to Upwork manually in the browser window ===")

        await page.wait_for_url("**/nx/find-work**", timeout=300000)
        await self._save_session()
        log.info("login_success")

    async def _handle_cloudflare(self, page: Page) -> bool:
        try:
            await page.wait_for_selector("text=Verify you are human", timeout=5000)
            log.info("cloudflare_detected",
                     message="=== Click the Cloudflare checkbox in the browser ===")
            await page.wait_for_function(
                "() => !document.body.innerText.includes('Verify you are human')",
                timeout=120000,
            )
            await random_delay(2, 3)
            log.info("cloudflare_passed")
            return True
        except Exception:
            return False

    async def _is_logged_in(self, page: Page) -> bool:
        try:
            await page.wait_for_selector(
                "[data-test='nav-find-work'], a[href*='find-work'], #nav-find-work",
                timeout=5000,
            )
            return True
        except Exception:
            return False

    async def _save_session(self):
        await self._context.storage_state(path=str(SESSION_FILE))
        log.info("session_saved")

    async def stop(self):
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
