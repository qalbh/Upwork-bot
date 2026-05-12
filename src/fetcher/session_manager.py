import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page
from src.config_loader import get_settings
from src.utils.human_behavior import random_delay, short_delay
from src.utils.logger import get_logger

log = get_logger()



class SessionManager:
    def __init__(self):
        self.settings = get_settings()
        self._playwright = None
        self._context: BrowserContext = None

    async def start(self) -> BrowserContext:
        self._playwright = await async_playwright().start()

        # chrome_profile_path is e.g. ".../Chrome/Profile 5"
        # user_data_dir must be the parent Chrome folder e.g. ".../Chrome"
        # The profile name "Profile 5" is passed as --profile-directory argument
        full_profile_path = Path(self.settings.app.upwork.chrome_profile_path)
        user_data_dir = str(full_profile_path.parent)   # .../Google/Chrome
        profile_dir = full_profile_path.name             # Profile 5

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                f"--profile-directory={profile_dir}",
            ],
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )

        log.info("browser_started", user_data_dir=user_data_dir, profile=profile_dir)
        return self._context

    async def login_if_needed(self, page: Page):
        settings = self.settings

        # Check if already logged in
        await page.goto("https://www.upwork.com", wait_until="domcontentloaded")
        await random_delay(2, 4)

        if await self._is_logged_in(page):
            log.info("already_logged_in")
            return

        log.info("manual_login_required", message="=== Please log in to Upwork manually in the browser window. Bot will continue automatically once logged in. ===")

        # Wait up to 5 minutes for the user to log in manually
        await page.wait_for_url("**/nx/find-work**", timeout=300000)
        log.info("login_success")

    async def _is_logged_in(self, page: Page) -> bool:
        try:
            # If we can find the "Find Work" nav element, we're logged in
            await page.wait_for_selector(
                "[data-test='nav-find-work'], a[href*='find-work'], #nav-find-work",
                timeout=5000
            )
            return True
        except Exception:
            return False

    async def stop(self):
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
