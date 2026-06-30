import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print('Navigating...')
        await page.goto('https://www.google.com/maps', wait_until='networkidle')
        await page.fill('input[name="q"]', 'Architects in Gurugram')
        await page.press('input[name="q"]', 'Enter')
        print('Waiting 10s...')
        await page.wait_for_timeout(10000)
        await page.screenshot(path='test_results.png')
        print('Screenshot saved.')
        
        results = page.locator('[role="article"]')
        count = await results.count()
        if count > 0:
            print(f'Found {count} results. Clicking first...')
            await results.first.click()
            await page.wait_for_timeout(5000)
            await page.screenshot(path='test_detail.png')
            
            print('Clicking back button...')
            clicked = await page.evaluate(
                """
                () => {
                    const buttons = Array.from(document.querySelectorAll('button[jsaction*="pane.place.backToList"], button[aria-label="Back"], button[aria-label="Close"]'));
                    for (const btn of buttons) {
                        const isVisible = !!(btn.offsetWidth || btn.offsetHeight || btn.getClientRects().length);
                        if (isVisible) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
                """
            )
            print(f'Clicked? {clicked}')
            await page.wait_for_timeout(5000)
            await page.screenshot(path='test_back.png')
            
            # Check if we are back at the results
            results_panel = page.locator('div[role="feed"]').first
            is_visible = await results_panel.is_visible()
            print(f"Results panel visible after back? {is_visible}")
            
        await browser.close()

asyncio.run(main())
