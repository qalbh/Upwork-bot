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

        profile_path = self.settings.app.upwork.chrome_profile_path
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )

        log.info("browser_started", profile=profile_path)
        return self._context

    async def login_if_needed(self, page: Page):
        settings = self.settings

        # Check if already logged in
        await page.goto("https://www.upwork.com", wait_until="domcontentloaded")
        await random_delay(2, 4)

        if await self._is_logged_in(page):
            log.info("already_logged_in")
            return

        log.info("login_start")
        await page.goto("https://www.upwork.com/ab/account-security/login", wait_until="domcontentloaded")
        await random_delay(2, 4)

        # Step 1 — email field (Cloudflare may appear first — click manually)
        log.info("waiting_for_email_field", message="Click Cloudflare checkbox if it appears")
        await page.wait_for_selector("#login_username", state="visible", timeout=120000)
        log.info("email_field_ready")

        await page.fill("#login_username", settings.upwork_email)
        await short_delay()
        await page.keyboard.press("Tab")
        await short_delay()
        await page.click("#login_password_continue")
        await random_delay(2, 4)

        # Step 2 — password field (Cloudflare may appear again — click manually)
        log.info("waiting_for_password_field", message="Click Cloudflare checkbox if it appears again")

        # Wait for password field to exist in DOM (it's hidden via CSS transition)
        await page.wait_for_selector("input[type='password']", state="attached", timeout=120000)
        await random_delay(2, 3)  # Let the CSS transition finish

        # Use JavaScript to fill — bypasses Playwright's visibility requirement
        await page.evaluate("""
            const input = document.querySelector("input[type='password']");
            if (input) {
                input.removeAttribute('disabled');
                input.style.display = 'block';
                input.style.visibility = 'visible';
                input.style.opacity = '1';
            }
        """)
        await short_delay()

        await page.fill("input[type='password']", settings.upwork_password)
        await short_delay()
        await page.keyboard.press("Enter")

        # Wait for dashboard
        log.info("waiting_for_dashboard")
        await page.wait_for_url("**/nx/find-work**", timeout=60000)
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
