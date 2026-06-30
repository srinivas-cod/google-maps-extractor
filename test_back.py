import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print('Navigating...')
        await page.goto('https://www.google.com/maps', wait_until='domcontentloaded')
        await page.fill('input[name="q"]', 'Architects in Gurugram')
        await page.press('input[name="q"]', 'Enter')
        print('Waiting 10s...')
        await page.wait_for_timeout(10000)
        
        results = page.locator('[role="article"]')
        count = await results.count()
        if count > 0:
            print(f'Found {count} results. Clicking first...')
            await results.first.click()
            await page.wait_for_timeout(5000)
            
            print('Dumping all buttons in the detail panel...')
            buttons = await page.locator('div[role="main"] button[aria-label]').all()
            for btn in buttons:
                try:
                    label = await btn.get_attribute('aria-label')
                    jsaction = await btn.get_attribute('jsaction')
                    is_visible = await btn.is_visible()
                    print(f'Button: aria-label="{label}" jsaction="{jsaction}" visible={is_visible}')
                except:
                    pass
        await browser.close()

asyncio.run(main())
