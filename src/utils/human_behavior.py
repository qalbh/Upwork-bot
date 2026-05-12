import asyncio
import random
import time
from playwright.async_api import Page


async def random_delay(min_sec: float = 5.0, max_sec: float = 15.0):
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def short_delay():
    await asyncio.sleep(random.uniform(1.0, 3.0))


async def type_like_human(page: Page, selector: str, text: str):
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def scroll_naturally(page: Page):
    scroll_distance = random.randint(300, 800)
    steps = random.randint(4, 10)
    per_step = scroll_distance // steps
    for _ in range(steps):
        await page.mouse.wheel(0, per_step)
        await asyncio.sleep(random.uniform(0.2, 0.6))


async def idle_scroll(page: Page):
    """Random long scroll session simulating a human reading the page."""
    if random.random() > 0.4:
        return

    duration = random.uniform(30, 90)
    end_time = time.time() + duration

    while time.time() < end_time:
        await page.mouse.wheel(0, random.randint(100, 400))
        await asyncio.sleep(random.uniform(1.5, 4.0))
        if random.random() < 0.3:
            await page.mouse.wheel(0, -random.randint(50, 200))
            await asyncio.sleep(random.uniform(1.0, 3.0))


async def random_mouse_move(page: Page):
    x = random.randint(200, 1000)
    y = random.randint(100, 700)
    await page.mouse.move(x, y)
    await asyncio.sleep(random.uniform(0.3, 0.8))
