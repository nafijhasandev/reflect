"""Record a light-mode UI preview without calling a hosted model.

Optional tools: pip install playwright pillow. Uses an installed Chrome browser.
Run while the local web app is serving at http://127.0.0.1:8000.
"""

import asyncio
import io
import json
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "reflect-demo.gif"
QUESTION = "How does habit stacking work?"
ANSWER = (
    "Habit stacking links a new action to a habit you already do. Choose a reliable "
    "cue: after your current habit, do the new action. For example, after making "
    "coffee, write one sentence in a journal (Chapter 5, p.66)."
)
SOURCE = {
    "book": "atomic_habits",
    "chunk_id": "73ecc043d783",
    "metadata": {
        "chapter": "Chapter 5: The Best Way to Start a New Habit",
        "section": "HABIT STACKING: A SIMPLE PLAN TO OVERHAUL YOUR HABITS",
        "page_start": 66,
        "page_end": 66,
    },
    "text_preview": (
        "Habit stacking pairs a new habit with a current habit. "
        "The existing routine becomes an obvious cue for the new action."
    ),
}


async def main() -> None:
    events = [
        {"type": "book_selected", "book": "atomic_habits"},
        {"type": "metadata", "query_type": "factual"},
        {"type": "chunk", "content": ANSWER},
        {"type": "sources", "sources": [SOURCE]},
        {"type": "done", "answer": ANSWER, "timing": {"total": 0.2}},
    ]
    sse = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
    frames: list[Image.Image] = []
    durations: list[int] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )
        page = await browser.new_page(viewport={"width": 1050, "height": 640}, device_scale_factor=1)
        async def mock_query(route) -> None:
            await route.fulfill(
                status=200,
                headers={"content-type": "text/event-stream", "cache-control": "no-cache"},
                body=sse,
            )

        await page.route("**/api/query", mock_query)
        await page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        await page.locator("#themeToggle").click()
        await page.wait_for_function("document.documentElement.dataset.theme === 'light'")

        async def capture(duration: int) -> None:
            png = await page.screenshot(type="png")
            image = Image.open(io.BytesIO(png)).convert("RGB")
            frames.append(image)
            durations.append(duration)

        await capture(850)
        for text in ("How does", "How does habit", "How does habit stacking", QUESTION):
            await page.locator("#queryInput").fill(text)
            await capture(260)
        await page.locator("#sendBtn").click()
        await page.locator(".answer-content").wait_for()
        await page.locator(".sources summary").click()
        await page.locator(".source-item").wait_for()
        for _ in range(4):
            await capture(650)
        await browser.close()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    palette = frames[0].quantize(colors=192, method=Image.Quantize.MEDIANCUT)
    gif_frames = [frame.quantize(palette=palette) for frame in frames]
    gif_frames[0].save(
        OUTPUT, save_all=True, append_images=gif_frames[1:], duration=durations,
        loop=0, optimize=True, disposal=2,
    )
    print(f"Saved {OUTPUT} ({OUTPUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    asyncio.run(main())
