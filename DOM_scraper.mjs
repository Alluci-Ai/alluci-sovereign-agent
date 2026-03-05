import puppeteer from 'puppeteer';

(async () => {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto('http://localhost:3000');
    await new Promise(r => setTimeout(r, 4000));

    const buttons = await page.$$('button');
    for (const btn of buttons) {
        const text = await page.evaluate(el => el.textContent, btn);
        if (text && text.includes('Bridges')) {
            await btn.click();
            break;
        }
    }
    await new Promise(r => setTimeout(r, 2000));

    // Check if Bridge cards are in DOM
    const cardCount = await page.$$eval('.glass-btn', els => els.length);
    console.log('Number of glass-btn:', cardCount);

    const bridgeCardCount = await page.$$eval('.glass-panel', els => els.length);
    console.log('Number of glass-panel:', bridgeCardCount);

    const text = await page.evaluate(() => document.body.innerText);
    console.log('Contains APPLE ECOSYSTEM:', text.includes('APPLE ECOSYSTEM'));
    console.log('Contains SOCIAL MANIFOLD:', text.includes('SOCIAL MANIFOLD'));
    console.log('Contains VERUS IDENT:', text.includes('VERUS ID'));
    console.log('Contains NO CONNECTION:', text.includes('NO_CONNECTION_HANDSHAKES_INITIALIZED'));
    console.log('Preview:', text.substring(0, 300).replace(/\n/g, ' '));
    await browser.close();
})();
