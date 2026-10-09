import { spawn } from 'node:child_process';
import assert from 'node:assert';

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const DEBUG_PORT = 9333;
const BASE_URL = 'http://localhost:8000/index.html';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function run() {
  console.log('🚀 Launching headless Edge on port', DEBUG_PORT);
  const browserProc = spawn(EDGE_PATH, [
    `--remote-debugging-port=${DEBUG_PORT}`,
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--user-data-dir=' + process.env.TEMP + '\\edge-test-profile-' + Date.now()
  ], { stdio: 'ignore' });

  try {
    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
      try {
        const res = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
        if (res.ok) {
          const data = await res.json();
          wsUrl = data.webSocketDebuggerUrl;
          break;
        }
      } catch (e) {}
      await sleep(200);
    }

    if (!wsUrl) throw new Error('Could not connect to Edge DevTools');
    console.log(' Connected to Edge DevTools WebSocket');

    const ws = new WebSocket(wsUrl);
    await new Promise(resolve => ws.onopen = resolve);

    let id = 1;
    const callbacks = new Map();
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && callbacks.has(msg.id)) {
        callbacks.get(msg.id)(msg);
        callbacks.delete(msg.id);
      }
    };

    function send(method, params = {}) {
      return new Promise((resolve) => {
        const reqId = id++;
        callbacks.set(reqId, resolve);
        ws.send(JSON.stringify({ id: reqId, method, params }));
      });
    }

    // Create target page
    const target = await send('Target.createTarget', { url: 'about:blank' });
    const pageTargetId = target.result.targetId;
    const session = await send('Target.attachToTarget', { targetId: pageTargetId, flatten: true });
    const sessionId = session.result.sessionId;

    function call(method, params = {}) {
      return new Promise((resolve) => {
        const reqId = id++;
        callbacks.set(reqId, resolve);
        ws.send(JSON.stringify({ id: reqId, sessionId, method, params }));
      });
    }

    await call('Page.enable');
    await call('Runtime.enable');

    async function evalScript(expression) {
      const res = await call('Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true
      });
      if (res.result?.exceptionDetails) {
        throw new Error('Eval error: ' + JSON.stringify(res.result.exceptionDetails));
      }
      return res.result?.result?.value;
    }

    async function navigate(url) {
      await call('Page.navigate', { url });
      // Wait for page load
      for (let i = 0; i < 20; i++) {
        await sleep(200);
        const state = await evalScript('document.readyState');
        if (state === 'complete') break;
      }
      await sleep(300);
    }

    console.log('\n--- TEST 1: Gating Check without ?edit=1 ---');
    await navigate(BASE_URL);
    const dockWithoutEdit = await evalScript("document.getElementById('cr-h') !== null");
    console.log('Dock exists without ?edit=1:', dockWithoutEdit);
    assert.strictEqual(dockWithoutEdit, false, 'Dock should NOT exist without ?edit=1');
    console.log('✅ TEST 1 PASSED: Dock is correctly hidden in production mode');

    console.log('\n--- TEST 2: Gating Check with ?edit=1 ---');
    await navigate(BASE_URL + '?edit=1');
    const dockWithEdit = await evalScript("document.getElementById('cr-h') !== null");
    console.log('Dock exists with ?edit=1:', dockWithEdit);
    assert.strictEqual(dockWithEdit, true, 'Dock MUST exist with ?edit=1');
    console.log('✅ TEST 2 PASSED: Dock renders when ?edit=1 is supplied');

    console.log('\n--- TEST 3: Independent Dual Font Dropdown Selection ---');
    await evalScript(`
      (() => {
        const hfSel = document.getElementById('cr-hf-sel');
        hfSel.value = 'Playfair Display';
        hfSel.dispatchEvent(new Event('change', { bubbles: true }));

        const bfSel = document.getElementById('cr-bf-sel');
        bfSel.value = 'Lora';
        bfSel.dispatchEvent(new Event('change', { bubbles: true }));
      })()
    `);
    await sleep(200);

    const fontTest = await evalScript(`
      (() => {
        const linkHf = document.getElementById('cr-dyn-font-hf');
        const linkBf = document.getElementById('cr-dyn-font-bf');
        const rootHeadingFont = document.documentElement.style.getPropertyValue('--heading-font');
        const rootBodyFont = document.documentElement.style.getPropertyValue('--body-font');
        const h1ComputedFont = window.getComputedStyle(document.querySelector('h1')).fontFamily;

        return {
          hfLinkHref: linkHf ? linkHf.href : null,
          bfLinkHref: linkBf ? linkBf.href : null,
          rootHeadingFont,
          rootBodyFont,
          h1ComputedFont
        };
      })()
    `);

    console.log('Heading font link:', fontTest.hfLinkHref);
    console.log('Body font link:', fontTest.bfLinkHref);
    console.log('Root heading font token:', fontTest.rootHeadingFont);
    console.log('Root body font token:', fontTest.rootBodyFont);
    console.log('h1 computed font-family:', fontTest.h1ComputedFont);

    assert(fontTest.hfLinkHref && fontTest.hfLinkHref.includes('Playfair+Display'), 'cr-dyn-font-hf must load Playfair Display');
    assert(fontTest.bfLinkHref && fontTest.bfLinkHref.includes('Lora'), 'cr-dyn-font-bf must load Lora');
    assert.strictEqual(fontTest.rootHeadingFont, "'Playfair Display', sans-serif");
    assert.strictEqual(fontTest.rootBodyFont, "'Lora', sans-serif");
    console.log('✅ TEST 3 PASSED: Both font slots load into independent <link> tags without collisions');

    console.log('\n--- TEST 4: Custom Font Type Mode & Slot Isolation ---');
    await evalScript(`
      (() => {
        // Toggle to custom input for heading font
        const tog = document.getElementById('cr-hf-tog');
        tog.click();
        const inp = document.getElementById('cr-hf-inp');
        inp.value = 'Cinzel';
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      })()
    `);
    await sleep(200);

    const customTest = await evalScript(`
      (() => {
        const linkHf = document.getElementById('cr-dyn-font-hf');
        const linkBf = document.getElementById('cr-dyn-font-bf');
        const rootHeadingFont = document.documentElement.style.getPropertyValue('--heading-font');
        const rootBodyFont = document.documentElement.style.getPropertyValue('--body-font');

        return {
          hfLinkHref: linkHf ? linkHf.href : null,
          bfLinkHref: linkBf ? linkBf.href : null,
          rootHeadingFont,
          rootBodyFont
        };
      })()
    `);

    console.log('Updated Heading font link:', customTest.hfLinkHref);
    console.log('Body font link remains:', customTest.bfLinkHref);
    assert(customTest.hfLinkHref && customTest.hfLinkHref.includes('Cinzel'), 'cr-dyn-font-hf must now load Cinzel');
    assert(customTest.bfLinkHref && customTest.bfLinkHref.includes('Lora'), 'cr-dyn-font-bf must remain Lora');
    assert.strictEqual(customTest.rootHeadingFont, "'Cinzel', sans-serif");
    assert.strictEqual(customTest.rootBodyFont, "'Lora', sans-serif");
    console.log('✅ TEST 4 PASSED: Custom text typing updates heading slot while preserving body slot');

    console.log('\n--- TEST 5: Persistence Across Reload ---');
    const storageData = await evalScript("localStorage.getItem('client_review_tokens')");
    console.log('Saved localStorage config:', storageData);
    assert(storageData.includes('Cinzel') && storageData.includes('Lora'), 'Config should store Cinzel and Lora');

    // Reload page
    await navigate(BASE_URL + '?edit=1');
    await sleep(300);

    const reloadTest = await evalScript(`
      (() => {
        const linkHf = document.getElementById('cr-dyn-font-hf');
        const linkBf = document.getElementById('cr-dyn-font-bf');
        const rootHeadingFont = document.documentElement.style.getPropertyValue('--heading-font');
        const rootBodyFont = document.documentElement.style.getPropertyValue('--body-font');

        return {
          hfLinkHref: linkHf ? linkHf.href : null,
          bfLinkHref: linkBf ? linkBf.href : null,
          rootHeadingFont,
          rootBodyFont
        };
      })()
    `);

    console.log('On reload heading link:', reloadTest.hfLinkHref);
    console.log('On reload body link:', reloadTest.bfLinkHref);
    console.log('On reload heading font token:', reloadTest.rootHeadingFont);
    console.log('On reload body font token:', reloadTest.rootBodyFont);

    assert(reloadTest.hfLinkHref && reloadTest.hfLinkHref.includes('Cinzel'), 'Heading font link must restore on load');
    assert(reloadTest.bfLinkHref && reloadTest.bfLinkHref.includes('Lora'), 'Body font link must restore on load');
    assert.strictEqual(reloadTest.rootHeadingFont, "'Cinzel', sans-serif");
    assert.strictEqual(reloadTest.rootBodyFont, "'Lora', sans-serif");
    console.log('✅ TEST 5 PASSED: Both font slots restore immediately on reload');

    console.log('\n🎉 ALL 5 END-TO-END TESTS PASSED SUCCESSFULLY!\n');
    ws.close();
  } finally {
    browserProc.kill();
  }
}

run().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
