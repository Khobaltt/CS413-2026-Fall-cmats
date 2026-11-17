/* Optional real-browser smoke test; start app.py first */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
  try {
    const page = await browser.newPage({viewport:{width:1100,height:900}});
    await page.goto(process.env.QUEENS_URL || 'http://127.0.0.1:8000');
    await page.selectOption('#size','4');
    await page.click('#start');
    await page.waitForFunction(()=>!document.querySelector('#step').disabled);
    assert.equal(await page.locator('.cell').count(),16);
    await page.click('#step');
    await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('try'));
    assert.equal(await page.locator('.cell.try').count(),1);
    await page.locator('#speed').evaluate(el=>{el.value='0';el.dispatchEvent(new Event('input',{bubbles:true}));});
    await page.click('#next');
    await page.waitForFunction(()=>document.querySelector('#count').textContent==='1');
    assert.equal(await page.locator('#board.solution').count(),1);
    await page.click('#play');
    await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Search complete'));
    assert.equal(await page.locator('#count').textContent(),'2');
    await page.click('#reset');
    await page.waitForFunction(()=>document.querySelector('#count').textContent==='0');
    await page.click('#start');
    await page.waitForFunction(()=>!document.querySelector('#step').disabled);
    await page.locator('#speed').evaluate(el=>{el.value='1000';el.dispatchEvent(new Event('input',{bubbles:true}));});
    await page.click('#play');
    await page.waitForFunction(()=>document.querySelector('#play').textContent==='Pause');
    await page.click('#play');
    await page.waitForFunction(()=>document.querySelector('#play').textContent==='Play');
    await page.route('**/rpc',route=>route.abort());
    await page.click('#step');
    await page.waitForFunction(()=>!document.querySelector('#error').hidden);
    assert.match(await page.locator('#error').textContent(),/restart/);
    await page.unroute('**/rpc');
    await page.click('#start');
    await page.waitForFunction(()=>!document.querySelector('#step').disabled);
    assert.equal(await page.locator('#error').isVisible(),false);
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    console.log('PASS: real browser start, step, next solution, play/pause, completion, reset, network failure, restart, mobile width');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
