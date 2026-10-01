const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const out = process.env.CELLULAR_FIELD_OUTPUT || require('node:fs').mkdtempSync(path.join(require('node:os').tmpdir(), 'cellular-field-'));
const url = process.env.CELLULAR_FIELD_URL || 'http://127.0.0.1:8000/';
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1360,height:1000}});
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    const requests=[];page.on('request',r=>requests.push(r.url()));
    await page.goto(url); await page.locator('#cellular-tab-btn').click();
    await page.waitForFunction(()=>document.querySelector('#cf-proof-control').textContent==='Origin digest recorded');
    assert.equal(await page.locator('#cf-time').innerText(),'0');
    assert.equal(await page.locator('#cf-difference').innerText(),'0');
    async function save(selector, name) {
      const wait=page.waitForEvent('download');await page.locator(selector).click();
      const download=await wait;const file=path.join(out,name);await download.saveAs(file);return JSON.parse(await fs.readFile(file,'utf8'));
    }
    const original=await save('#cf-save-control','original.json');
    await page.locator('#cf-evolve').click();
    await page.waitForFunction(()=>document.querySelector('#cf-time').textContent==='384');
    assert.equal(await page.locator('#cf-difference').innerText(),'0');
    const evolved=await save('#cf-save-control','evolved.json');
    assert.notEqual(evolved.cells,original.cells);
    assert(!('original' in evolved) && !('frames' in evolved));
    await page.locator('#cf-perturb').click();
    assert.equal(await page.locator('#cf-difference').innerText(),'1');
    await page.screenshot({path:path.join(out,'cellular-evolved-desktop.png'),fullPage:true,animations:"disabled"});
    await page.locator('#cf-return').click();
    await page.waitForFunction(()=>document.querySelector('#cf-proof-control').textContent==='SHA-256 matches origin');
    assert.equal(await page.locator('#cf-proof-twin').innerText(),'Differs from origin');
    assert(Number((await page.locator('#cf-difference').innerText()).replaceAll(',',''))>1);
    const returned=await save('#cf-save-control','returned.json');
    assert.equal(returned.cells,original.cells);
    // Fresh document has no original image; only exported state is loaded.
    await page.reload(); await page.locator('#cellular-tab-btn').click();
    await page.locator('#cf-file').setInputFiles(path.join(out,'evolved.json'));
    await page.waitForFunction(()=>document.querySelector('#cf-time').textContent==='384');
    await page.locator('#cf-return').click();
    await page.waitForFunction(()=>document.querySelector('#cf-proof-control').textContent==='SHA-256 matches origin');
    assert.equal((await save('#cf-save-control','fresh-returned.json')).cells,original.cells);
    // Bad state preserves current cells.
    await page.locator('#cf-file').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({...evolved,frames:[]}))});
    await page.waitForFunction(()=>document.querySelector('#cf-error').textContent.includes('Unrecognized'));
    assert.equal((await save('#cf-save-control','after-bad.json')).cells,original.cells);
    // Keyboard drawing has a complete path without a pointer.
    await page.locator('#cf-blank').click();await page.locator('#cf-control').press('ArrowRight');await page.locator('#cf-control').press('Space');
    await page.waitForFunction(()=>document.querySelector('#cf-proof-control').textContent==='Origin digest recorded');
    const drawn=await save('#cf-save-control','keyboard-drawn.json');
    assert.equal([...drawn.cells].reduce((n,c)=>n+parseInt(c,16).toString(2).replaceAll('0','').length,0),1);
    await page.locator('#cf-step-forward').click();assert.equal(await page.locator('#cf-time').innerText(),'1');
    await page.locator('#cf-step-back').click();assert.equal(await page.locator('#cf-time').innerText(),'0');
    // Evolving stops on navigation; core tabs retain their existing panels.
    await page.locator('#cf-evolve').click();await page.waitForTimeout(60);await page.locator('[data-tab="encode"]').click();
    const stopped=await page.locator('#cf-time').innerText();await page.waitForTimeout(100);assert.equal(await page.locator('#cf-time').innerText(),stopped);
    for(const tab of ['encode','decode','analyze','textlab','aiagent']) {
      await page.locator('.tab[data-tab="'+tab+'"]').click();assert(await page.locator('#'+tab+'-panel').isVisible());
    }
    await page.locator('#cellular-tab-btn').click();await page.locator('#cf-seed').fill('STILL HERE');await page.locator('#cf-new').click();
    for(const width of [1360,390,320]) {
      await page.setViewportSize({width,height:1000});
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
      assert.equal(overflow,false,'page overflow at '+width);
      const panelOverflow=await page.locator('#cellular-panel').evaluate(el=>el.scrollWidth>el.clientWidth+1);
      assert.equal(panelOverflow,false,'panel overflow at '+width);
      await page.screenshot({path:path.join(out,'cellular-'+width+'.png'),fullPage:true,animations:"disabled"});
    }
    assert.deepEqual(errors,[]);
    assert(requests.every(u=>u.startsWith(url)||u.startsWith('blob:')||u.startsWith('data:')),'unexpected network request');
    const result={pass:true,checks:['exact return','one-bit divergence','fresh-document import reversal','invalid-import preservation','keyboard drawing','single steps','pause on tab change','existing tab navigation','1360/390/320px fit','no page errors','no external requests'],errors};
    await fs.writeFile(path.join(out,'browser-results.json'),JSON.stringify(result,null,2));console.log(result);
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
