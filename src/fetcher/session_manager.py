import shutil
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page
from src.config_loader import get_settings
from src.utils.human_behavior import random_delay
from src.utils.stealth import STEALTH_SCRIPT
from src.utils.logger import get_logger

log = get_logger()

BOT_PROFILE_DIR = Path.home() / ".upwork-bot-profile"


class SessionManager:
    def __init__(self):
        self.settings = get_settings()
        self._playwright = None
        self._context: BrowserContext = None

    def _prepare_profile(self) -> str:
        source = Path(self.settings.app.upwork.chrome_profile_path)
        dest = BOT_PROFILE_DIR / "Default"
        if not dest.exists():
            log.info("copying_profile", source=str(source))
            shutil.copytree(str(source), str(dest))
            log.info("profile_copied")
        return str(BOT_PROFILE_DIR)

    async def start(self) -> BrowserContext:
        self._playwright = await async_playwright().start()

        user_data_dir = self._prepare_profile()

        lock_file = BOT_PROFILE_DIR / "SingletonLock"
        if lock_file.exists():
            lock_file.unlink()

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            # Remove flags that expose automation
            ignore_default_args=[
                "--enable-automation",
                "--no-sandbox",
                "--disable-extensions",
            ],
            args=[
                # Core stealth
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                # Realistic browser behaviour
                "--no-first-run",
                "--no-default-browser-check",
                "--no-service-autorun",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-ipc-flooding-protection",
                # Match a real Mac user setup
                "--lang=en-US",
                "--start-maximized",
            ],
            viewport=None,      # Let --start-maximized control the size
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Inject stealth script into every page/frame before any JS runs
        await self._context.add_init_script(STEALTH_SCRIPT)

        log.info("browser_started", profile=user_data_dir)
        return self._context

    async def login_if_needed(self, page: Page):
        await page.goto("https://www.upwork.com", wait_until="domcontentloaded")
        await random_delay(2, 4)

        if await self._is_logged_in(page):
            log.info("already_logged_in")
            return

        log.info("manual_login_required",
                 message="=== Please log in to Upwork manually in the browser. Bot continues automatically once logged in. ===")
        await page.wait_for_url("**/nx/find-work**", timeout=300000)
        log.info("login_success")

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
        if self._playwright:
            await self._playwright.stop()
