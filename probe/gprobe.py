import asyncio, json
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(locale="en-US")
        await pg.goto("https://www.google.com/maps/search/dentist+in+Yerevan?hl=en", wait_until="domcontentloaded", timeout=60000)
        await pg.wait_for_timeout(5000)
        print("URL", pg.url, "TITLE", await pg.title())
        feed = pg.locator('div[role="feed"]')
        print("feed", await feed.count())
        for _ in range(8):
            await pg.mouse.move(200, 400) if False else None
            if await feed.count(): await feed.evaluate("e => e.scrollBy(0, 5000)")
            await pg.wait_for_timeout(1500)
        links = await pg.eval_on_selector_all('a.hfpxzc', 'els => els.map(e => [e.getAttribute("aria-label"), e.href])')
        print("results", len(links))
        for name, href in links[:3]:
            await pg.goto(href, wait_until="domcontentloaded"); await pg.wait_for_timeout(2500)
            web = await pg.eval_on_selector_all('a[data-item-id="authority"]', 'els => els.map(e => e.href)')
            ph = await pg.eval_on_selector_all('button[data-item-id^="phone"]', 'els => els.map(e => e.getAttribute("data-item-id"))')
            addr = await pg.eval_on_selector_all('button[data-item-id="address"]', 'els => els.map(e => e.getAttribute("aria-label"))')
            cat = await pg.eval_on_selector_all('button.DkEaL', 'els => els.map(e => e.textContent)')
            print(name, web, ph, addr, cat)
        await pg.screenshot(path="probe/g.png")
        await b.close()
asyncio.run(main())
