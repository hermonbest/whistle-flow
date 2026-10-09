---
name: client-site-customizer
description: Inspects any existing HTML/CSS website, extracts its current brand colors, fonts, and page sections, refactors rigid styles into responsive flow-based containers so elements never overlap, and injects a secret client review mode (?edit=true) with an interactive designer dock and 1-click code export to permanently lock in approved styles. Use whenever the user wants to make a website client-customizable, let a client preview and change colors/fonts/sections on a deployed site (e.g. Vercel/Netlify), add a client styling mode, or hand over design controls temporarily before locking them in.
---

# Client Site Customizer Skill

This skill transforms any static or deployed website into a **client-customizable review experience** without requiring paid SaaS builders or complex backend databases.

It extracts the site's existing design tokens (colors, fonts, sections), hardens the layout so elements can never overlap, and injects a hidden client editor activated via a secret query parameter (e.g. `?edit=true`).

---

## 4-Step Execution Workflow

```
[1. Inspect & Extract]  ──>  [2. Harden Layout & Tokens]  ──>  [3. Inject Review Dock]  ──>  [4. Lock In & Ship]
   Scan colors, fonts,        Convert hardcoded CSS to         Add hidden (?edit=true)       Paste approved CSS,
   and page sections          CSS vars & flex column flow      dock with live controls       remove script, deploy
```

---

## Phase 1: Inspect & Extract Existing Site Assets

Scan the target website files (`index.html`, `style.css`, or `<style>` blocks) to identify:

### 1. Extract Colors
Find the dominant color values in the codebase:
- **Primary / Accent Color:** Buttons, links, highlighted spans, badges, borders.
- **Background Color:** `body`, main container, sections (`#000`, `#0b0f19`, `#ffffff`, etc.).
- **Text Color:** Headings (`<h1>`-`<h3>`), paragraphs (`<p>`), nav links.
- **Surface / Card Color:** Cards, modals, glassmorphism overlays.

### 2. Extract Fonts
- Look for `<link href="...fonts.googleapis.com...">` or `@import` declarations.
- Check `font-family` declarations on `body`, `html`, or headings.
- Note the primary body font and heading font.

### 3. Extract Section Architecture
Identify all top-level sections in the page flow:
- Look for semantic tags: `<header>`, `<section>`, `<main>`, `<footer>`.
- Look for ID/class identifiers: `#hero`, `#about`, `#services`, `#pricing`, `#testimonials`, `#contact`, `#cta`.
- Note their natural order in the document.

---

## Phase 2: Layout Optimization & "Anti-Overlap" Hardening

Clients often break layouts when given freeform editing tools. To prevent broken layouts or overlapping sections, refactor the page using these two architectural rules:

### Rule A: Convert Hardcoded Styles to CSS Custom Properties (Design Tokens)
Add or update the `:root` block at the top of the stylesheet with the extracted values:

```css
:root {
  --primary-color: /* Extracted Primary Color */;
  --bg-color: /* Extracted Background Color */;
  --heading-color: /* Extracted Heading Color */;
  --body-color: /* Extracted Body Text Color */;
  --heading-font: /* Extracted Heading Font */, sans-serif;
  --body-font: /* Extracted Body Font */, sans-serif;
  --card-bg: rgba(255, 255, 255, 0.05);
  --card-border: rgba(255, 255, 255, 0.1);
}
```

Replace hardcoded instances:
- Change button backgrounds to `var(--primary-color)`.
- Change page background to `var(--bg-color)`.
- Change headings color and font to `var(--heading-color)` and `var(--heading-font)`.
- Change body text color and font to `var(--body-color)` and `var(--body-font)`.

#### Critical Specificity Rule (Utility Classes & Tailwind):
If the site uses Tailwind CSS or utility classes (`.text-white`, `.text-zinc-100`, `.text-zinc-400`), direct classes on child elements will silently override `body { color: var(--text-color); }`. 
Apply this global root-cause override to `<style>`:
```css
h1, h2, h3, h4, .text-white, .text-zinc-100, .text-zinc-200 {
  color: var(--heading-color) !important;
  font-family: var(--heading-font) !important;
}
p, .text-zinc-300, .text-zinc-400, .text-zinc-500 {
  color: var(--body-color) !important;
  font-family: var(--body-font);
}
.text-cyan-400, .text-cyan-300 {
  color: var(--primary-color) !important;
}
```

### Rule B: Enforce Flow-Based Auto-Stacking (The Anti-Overlap Engine)
Check all top-level sections for overlap hazards:
1. **Remove hardcoded heights:** Replace `height: 800px` or `height: 100vh` with `min-height: ...; height: auto;`.
2. **Remove absolute positioning on sections:** Sections must never have `position: absolute` or `position: fixed` (except sticky navbars/headers).
3. **Wrap sections in a flex-column flow container:**
   ```css
   #page-container, main {
     display: flex;
     flex-direction: column;
     width: 100%;
     min-height: 100vh;
   }
   ```
   *In a Flex Column layout, elements cannot physically overlap. If a section expands or moves, subsequent sections are automatically pushed down smoothly.*

---

## Phase 3: Inject the Secret Client Review Dock

Inject the client review script right before `</body>`.

### Characteristics:
- **Zero Dependencies:** Pure Vanilla JavaScript, under 4KB.
- **Hidden by Default:** Public visitors at `site.com` see the clean website. The editor ONLY renders when `?edit=true` is present in the URL.
- **Local Persistence:** Uses `localStorage` so the client's tweaks stay saved in their browser across reloads and tab closes.
- **1-Click Export:** Provides a "📋 Copy Final Approved Style" button that copies the clean CSS `:root` snippet to clipboard.

### The Standard Injection Script:

```html
<!-- ================= CLIENT REVIEW & CUSTOMIZER ENGINE ================= -->
<script>
(function() {
  const urlParams = new URLSearchParams(window.location.search);
  const isEditMode = urlParams.get('edit') === 'true';

  const STORAGE_KEY = 'site_customizer_config';
  const savedConfig = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  const root = document.documentElement;

  // Dynamic Google Font Loader (Loads chosen fonts into dedicated slot links)
  function loadGoogleFont(font, slot) {
    if (!font || font.includes('system-ui')) return;
    const linkId = 'cr-dyn-font-' + (slot || 'default');
    let link = document.getElementById(linkId);
    if (!link) {
      link = document.createElement('link');
      link.id = linkId;
      link.rel = 'stylesheet';
      document.head.appendChild(link);
    }
    link.href = 'https://fonts.googleapis.com/css2?family=' + encodeURIComponent(font).replace(/%20/g, '+') + ':wght@400;600;700;800&display=swap';
  }

  // Apply saved values immediately on load
  if (savedConfig.primary) root.style.setProperty('--primary-color', savedConfig.primary);
  if (savedConfig.bg) root.style.setProperty('--bg-color', savedConfig.bg);
  if (savedConfig.heading) root.style.setProperty('--heading-color', savedConfig.heading);
  if (savedConfig.body) root.style.setProperty('--body-color', savedConfig.body);
  if (savedConfig.hf) {
    loadGoogleFont(savedConfig.hf, 'hf');
    root.style.setProperty('--heading-font', `'${savedConfig.hf}', sans-serif`);
  }
  if (savedConfig.bf) {
    loadGoogleFont(savedConfig.bf, 'bf');
    root.style.setProperty('--body-font', `'${savedConfig.bf}', sans-serif`);
  }

  // Stop execution for public visitors
  if (!isEditMode) return;

  function fontFieldHtml(label, id) {
    return `
      <div style="margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
          <label style="font-size: 10px; opacity: 0.8;">${label}</label>
          <button id="${id}-tog" type="button" style="background: none; border: none; color: #22d3ee; cursor: pointer; font-size: 10px; padding: 0; text-decoration: underline;">+ Custom</button>
        </div>
        <select id="${id}-sel" style="width: 100%; box-sizing: border-box; padding: 5px; background: #1f2937; color: #fff; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; font-size: 11px;">
          <option value="Geist">Geist (Modern Tech)</option>
          <option value="Inter">Inter (Standard SaaS)</option>
          <option value="Plus Jakarta Sans">Plus Jakarta Sans (Clean)</option>
          <option value="Outfit">Outfit (Geometric)</option>
          <option value="Space Grotesk">Space Grotesk (Neo-Brutal)</option>
          <option value="Syne">Syne (Artistic Display)</option>
          <option value="Playfair Display">Playfair Display (Editorial)</option>
          <option value="Cinzel">Cinzel (Roman Luxury)</option>
          <option value="Lora">Lora (Modern Serif)</option>
          <option value="JetBrains Mono">JetBrains Mono (Monospace)</option>
        </select>
        <input type="text" id="${id}-inp" placeholder="Type Google font name..." style="display: none; width: 100%; box-sizing: border-box; padding: 5px; background: #1f2937; color: #fff; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; font-size: 11px;">
      </div>
    `;
  }

  // Build the Client Review UI Dock
  const dock = document.createElement('div');
  dock.id = 'client-customizer-dock';
  dock.style.cssText = `
    position: fixed; bottom: 20px; right: 20px; z-index: 999999;
    background: #111827; color: #f9fafb; border: 1px solid rgba(255,255,255,0.2);
    border-radius: 16px; padding: 18px; width: 270px; box-shadow: 0 16px 40px rgba(0,0,0,0.6);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 13px;
  `;

  dock.innerHTML = `
    <div style="font-weight: 700; font-size: 14px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">
      <span>🎨 Customize Brand Style</span>
      <span style="font-size: 11px; color: #10b981; background: rgba(16,185,129,0.15); padding: 2px 6px; border-radius: 4px; font-weight: 600;">Client Review</span>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px;">
      <div>
        <label style="font-size: 10px; opacity: 0.8; display: block; margin-bottom: 4px;">Headings Color</label>
        <input type="color" id="rev-heading" value="${savedConfig.heading || '#f4f4f5'}" style="width: 100%; height: 26px; border: none; cursor: pointer; background: none;">
      </div>
      <div>
        <label style="font-size: 10px; opacity: 0.8; display: block; margin-bottom: 4px;">Body Color</label>
        <input type="color" id="rev-body" value="${savedConfig.body || '#a1a1aa'}" style="width: 100%; height: 26px; border: none; cursor: pointer; background: none;">
      </div>
      <div>
        <label style="font-size: 10px; opacity: 0.8; display: block; margin-bottom: 4px;">Accent</label>
        <input type="color" id="rev-primary" value="${savedConfig.primary || '#6366f1'}" style="width: 100%; height: 26px; border: none; cursor: pointer; background: none;">
      </div>
      <div>
        <label style="font-size: 10px; opacity: 0.8; display: block; margin-bottom: 4px;">Background</label>
        <input type="color" id="rev-bg" value="${savedConfig.bg || '#0b0f19'}" style="width: 100%; height: 26px; border: none; cursor: pointer; background: none;">
      </div>
    </div>

    ${fontFieldHtml('Headings Font', 'rev-hf')}
    ${fontFieldHtml('Body Text Font', 'rev-bf')}

    <button id="rev-copy-btn" style="width: 100%; background: var(--primary-color, #6366f1); color: #fff; font-weight: 700; border: none; border-radius: 8px; padding: 9px; cursor: pointer; font-size: 12px; transition: filter 0.2s; margin-top: 4px;">
      📋 Copy Final Approved Style
    </button>
  `;

  document.body.appendChild(dock);

  const hInput = document.getElementById('rev-heading');
  const bInput = document.getElementById('rev-body');
  const pInput = document.getElementById('rev-primary');
  const bgInput = document.getElementById('rev-bg');

  function wireFont(id, savedVal) {
    const sel = document.getElementById(`${id}-sel`), inp = document.getElementById(`${id}-inp`), tog = document.getElementById(`${id}-tog`);
    let isCustom = false;
    if (savedVal) {
      if ([...sel.options].some(o => o.value === savedVal)) {
        sel.value = savedVal;
      } else {
        isCustom = true;
        sel.style.display = 'none';
        inp.style.display = 'block';
        inp.value = savedVal;
        tog.innerText = '← List';
      }
    }
    tog.onclick = function() {
      isCustom = !isCustom;
      sel.style.display = isCustom ? 'none' : 'block';
      inp.style.display = isCustom ? 'block' : 'none';
      tog.innerText = isCustom ? '← List' : '+ Custom';
      if (isCustom) inp.focus();
      updateTokens();
    };
    sel.addEventListener('change', updateTokens);
    inp.addEventListener('input', updateTokens);
    return () => (isCustom ? inp.value : sel.value).trim();
  }

  const getHf = wireFont('rev-hf', savedConfig.hf || 'Geist');
  const getBf = wireFont('rev-bf', savedConfig.bf || 'Geist');

  function updateTokens() {
    const hf = getHf(), bf = getBf();
    if (hf) loadGoogleFont(hf, 'hf');
    if (bf) loadGoogleFont(bf, 'bf');
    const config = {
      heading: hInput.value,
      body: bInput.value,
      primary: pInput.value,
      bg: bgInput.value,
      hf,
      bf
    };
    root.style.setProperty('--heading-color', config.heading);
    root.style.setProperty('--body-color', config.body);
    root.style.setProperty('--primary-color', config.primary);
    root.style.setProperty('--bg-color', config.bg);
    if (hf) root.style.setProperty('--heading-font', `'${hf}', sans-serif`);
    if (bf) root.style.setProperty('--body-font', `'${bf}', sans-serif`);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  }

  [hInput, bInput, pInput, bgInput].forEach(el => el.addEventListener('input', updateTokens));

  document.getElementById('rev-copy-btn').addEventListener('click', function() {
    const hf = getHf(), bf = getBf();
    const cssSnippet = `/* Final Approved Client Brand Tokens */\n:root {\n  --heading-color: ${hInput.value};\n  --body-color: ${bInput.value};\n  --primary-color: ${pInput.value};\n  --bg-color: ${bgInput.value};\n  --heading-font: '${hf}', sans-serif;\n  --body-font: '${bf}', sans-serif;\n}`;
    navigator.clipboard.writeText(cssSnippet).then(() => {
      const origText = this.innerText;
      this.innerText = '✅ Copied to Clipboard!';
      setTimeout(() => { this.innerText = origText; }, 2500);
      alert('Approved styles copied to clipboard! Send this code to the developer to lock it in permanently.');
    });
  });
})();
</script>
<!-- ================= END CLIENT REVIEW ENGINE ================= -->
```

---

## Phase 4: Lock-In & Hand-off Protocol

When the client is satisfied with their adjustments:

1. **Client Action:**  
   The client clicks **"📋 Copy Final Approved Style"** and sends the 6-line CSS block to the developer.
2. **Developer Lock-In:**  
   - Open the project’s CSS file.
   - Paste the values into `:root`.
   - Delete the `<script>` tag from `index.html`.
3. **Deploy:**  
   - Commit and push to Git (`git commit -m "Lock in approved client styles"`).
   - Vercel/Netlify automatically builds and redeploys.
4. **Verification:**  
   - Visit `site.vercel.app?edit=true`.
   - Verify that the customizer dock is completely gone and the approved style is permanently live.

---

## Phase 5: Verification & End-to-End Testing Protocol

Whenever injecting or updating the customizer, the agent must verify all 5 acceptance gates:

1. **Dual Font Slot Independence:**
   - Verify that `<link id="cr-dyn-font-hf">` and `<link id="cr-dyn-font-bf">` exist independently in `<head>`.
   - Changing the heading font must NOT cancel or overwrite the body font stylesheet.
   - Inspect computed styles on `h1..h3` to confirm `font-family` matches `--heading-font`, and `p`/`body` matches `--body-font`.
2. **Color Specificity Check:**
   - Confirm heading text (`h1`, `h2`, `h3`, `.text-white`) displays `var(--heading-color)`.
   - Confirm body paragraphs (`p`, `.text-zinc-400`) display `var(--body-color)`.
   - Confirm accent buttons/badges display `var(--primary-color)`.
3. **Responsive Non-Overlap Flow:**
   - Confirm `#page-container` or `main` has flex column flow (`display: flex; flex-direction: column`).
   - Confirm no section has a hardcoded fixed height or absolute positioning that causes overlap when fonts resize.
4. **LocalStorage Persistence:**
   - Modify colors and fonts, reload the page with `?edit=1` or `?edit=true`, and verify all customized styles persist immediately on load.
5. **Gating & Clean Production State:**
   - Without `?edit=1`/`?edit=true`, the dock element must never exist in the DOM for regular visitors.
