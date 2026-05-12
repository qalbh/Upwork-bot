import asyncio
import random
import re
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup
from playwright.async_api import Page
from src.config_loader import get_settings, SearchConfig
from src.fetcher.session_manager import SessionManager
from src.models.job import Job
from src.utils.human_behavior import (
    random_delay,
    short_delay,
    scroll_naturally,
    idle_scroll,
    random_mouse_move,
    type_like_human,
)
from src.utils.logger import get_logger

log = get_logger()


class PlaywrightFetcher:
    def __init__(self):
        self.settings = get_settings()
        self.session = SessionManager()

    async def fetch_jobs(self, query: str) -> list[Job]:
        context = await self.session.start()
        page = await context.new_page()
        jobs = []

        try:
            await self.session.login_if_needed(page)
            await self._navigate_to_search(page, query)
            job_links = await self._collect_job_links(page)
            log.info("job_links_found", query=query, count=len(job_links))

            for url in job_links:
                try:
                    job = await self._fetch_job_detail(page, url)
                    if job:
                        jobs.append(job)
                    await random_delay(
                        self.settings.app.upwork.min_delay_seconds,
                        self.settings.app.upwork.max_delay_seconds,
                    )
                except Exception as e:
                    log.warning("job_detail_failed", url=url, error=str(e))
                    continue

        except Exception as e:
            log.error("fetch_session_failed", query=query, error=str(e))
        finally:
            await self.session.stop()

        return jobs

    async def _navigate_to_search(self, page: Page, query: str):
        upwork_home = self.settings.app.upwork.homepage
        log.info("navigating_homepage")

        await page.goto(upwork_home, wait_until="domcontentloaded")
        await random_delay(3, 6)
        await scroll_naturally(page)
        await idle_scroll(page)

        search_selectors = [
            'input[placeholder*="Search"]',
            'input[aria-label*="search"]',
            'input[name="q"]',
        ]
        search_box = None
        for selector in search_selectors:
            try:
                search_box = await page.wait_for_selector(selector, timeout=5000)
                if search_box:
                    break
            except Exception:
                continue

        if search_box:
            await random_mouse_move(page)
            await type_like_human(page, search_selectors[0], query)
            await short_delay()
            await page.keyboard.press("Enter")
        else:
            search_url = f"{upwork_home}/nx/search/jobs/?q={query.replace(' ', '+')}&sort=recency"
            await page.goto(search_url, wait_until="domcontentloaded")

        await random_delay(4, 8)
        await scroll_naturally(page)
        log.info("search_loaded", query=query)

    async def _collect_job_links(self, page: Page) -> list[str]:
        await idle_scroll(page)

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        links = []
        base = self.settings.app.upwork.homepage

        for tag in soup.select("a[href*='/jobs/']"):
            href = tag.get("href", "")
            if not href:
                continue
            if not href.startswith("http"):
                href = base + href
            if href not in links:
                links.append(href)

        max_jobs = self.settings.app.search.jobs_per_session
        selected = links[:max_jobs]

        if len(selected) < len(links):
            selected = random.sample(links, min(max_jobs, len(links)))

        return selected

    async def _fetch_job_detail(self, page: Page, url: str) -> Optional[Job]:
        log.info("fetching_job", url=url)
        await page.goto(url, wait_until="domcontentloaded")
        await random_delay(4, 8)
        await scroll_naturally(page)
        await idle_scroll(page)

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        job_id = self._extract_job_id(url)
        if not job_id:
            return None

        title = self._text(soup, [
            "h1[class*='title']",
            "h1",
        ])

        description = self._text(soup, [
            "[data-test='description']",
            ".job-description",
            "section p",
        ], long=True)

        budget_type, budget_amount = self._extract_budget(soup)
        skills = self._extract_skills(soup)
        duration = self._text(soup, ["[data-test='duration']", "[class*='duration']"])
        experience = self._text(soup, ["[data-test='experience-level']", "[class*='experience']"])
        client_location = self._text(soup, ["[data-test='client-location']", "[class*='location']"])
        client_rating = self._extract_rating(soup)
        client_hires = self._extract_hires(soup)

        return Job(
            job_id=job_id,
            title=title or "Unknown Title",
            url=url,
            budget_type=budget_type,
            budget_amount=budget_amount,
            duration=duration,
            experience_level=experience,
            skills=skills,
            client_location=client_location,
            client_rating=client_rating,
            client_hire_count=client_hires,
            description=description,
        )

    def _extract_job_id(self, url: str) -> Optional[str]:
        match = re.search(r"~([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        match = re.search(r"/jobs/([^/?]+)", url)
        return match.group(1) if match else None

    def _text(self, soup: BeautifulSoup, selectors: list[str], long: bool = False) -> str:
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator=" ", strip=True)
                if long:
                    return text[:2000]
                return text[:300]
        return ""

    def _extract_budget(self, soup: BeautifulSoup) -> Tuple[str, str]:
        text = self._text(soup, [
            "[data-test='budget']",
            "[class*='budget']",
            "[class*='rate']",
        ])
        if "/hr" in text.lower():
            return "hourly", text
        if "$" in text:
            return "fixed", text
        return "unknown", text

    def _extract_skills(self, soup: BeautifulSoup) -> list[str]:
        skills = []
        for el in soup.select("[data-test='skill'] , [class*='skill'] span"):
            t = el.get_text(strip=True)
            if t and t not in skills:
                skills.append(t)
        return skills[:15]

    def _extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        el = soup.select_one("[class*='rating'] , [data-test*='rating']")
        if el:
            try:
                return float(el.get_text(strip=True).split()[0])
            except Exception:
                pass
        return None

    def _extract_hires(self, soup: BeautifulSoup) -> Optional[int]:
        el = soup.select_one("[data-test*='hire'] , [class*='hire']")
        if el:
            match = re.search(r"\d+", el.get_text())
            if match:
                return int(match.group())
        return None
