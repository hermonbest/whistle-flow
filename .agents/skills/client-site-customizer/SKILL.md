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
  --text-color: /* Extracted Text Color */;
  --font-family: /* Extracted Primary Font */, sans-serif;
  --card-bg: rgba(255, 255, 255, 0.05);
  --card-border: rgba(255, 255, 255, 0.1);
}
```

Replace hardcoded instances:
- Change button backgrounds to `var(--primary-color)`.
- Change page background to `var(--bg-color)`.
- Change heading and paragraph colors to `var(--text-color)`.
- Change font-family rules to `var(--font-family)`.

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

  // Apply saved values immediately on load
  if (savedConfig.primary) root.style.setProperty('--primary-color', savedConfig.primary);
  if (savedConfig.bg) root.style.setProperty('--bg-color', savedConfig.bg);
  if (savedConfig.text) root.style.setProperty('--text-color', savedConfig.text);
  if (savedConfig.font) root.style.setProperty('--font-family', `'${savedConfig.font}', sans-serif`);

  // Stop execution for public visitors
  if (!isEditMode) return;

  // Build the Client Review UI Dock
  const dock = document.createElement('div');
  dock.id = 'client-customizer-dock';
  dock.style.cssText = `
    position: fixed; bottom: 20px; right: 20px; z-index: 999999;
    background: #111827; color: #f9fafb; border: 1px solid rgba(255,255,255,0.2);
    border-radius: 16px; padding: 18px; width: 330px; box-shadow: 0 16px 40px rgba(0,0,0,0.6);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 13px;
  `;

  dock.innerHTML = `
    <div style="font-weight: 700; font-size: 14px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">
      <span>🎨 Customize Brand Style</span>
      <span style="font-size: 11px; color: #10b981; background: rgba(16,185,129,0.15); padding: 2px 6px; border-radius: 4px; font-weight: 600;">Client Review</span>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px;">
      <div>
        <label style="font-size: 11px; opacity: 0.8; display: block; margin-bottom: 4px;">Primary</label>
        <input type="color" id="rev-primary" value="${savedConfig.primary || getComputedStyle(root).getPropertyValue('--primary-color').trim() || '#6366f1'}" style="width: 100%; height: 32px; border: none; cursor: pointer; background: none;">
      </div>
      <div>
        <label style="font-size: 11px; opacity: 0.8; display: block; margin-bottom: 4px;">Background</label>
        <input type="color" id="rev-bg" value="${savedConfig.bg || getComputedStyle(root).getPropertyValue('--bg-color').trim() || '#0b0f19'}" style="width: 100%; height: 32px; border: none; cursor: pointer; background: none;">
      </div>
      <div>
        <label style="font-size: 11px; opacity: 0.8; display: block; margin-bottom: 4px;">Text Color</label>
        <input type="color" id="rev-text" value="${savedConfig.text || getComputedStyle(root).getPropertyValue('--text-color').trim() || '#f3f4f6'}" style="width: 100%; height: 32px; border: none; cursor: pointer; background: none;">
      </div>
    </div>

    <div style="margin-bottom: 14px;">
      <label style="font-size: 11px; opacity: 0.8; display: block; margin-bottom: 4px;">Font Style</label>
      <select id="rev-font" style="width: 100%; padding: 7px; background: #1f2937; color: #fff; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; font-size: 12px;">
        <option value="Plus Jakarta Sans">Plus Jakarta Sans (Modern Clean)</option>
        <option value="Inter">Inter (Standard SaaS)</option>
        <option value="Playfair Display">Playfair Display (Luxury Editorial)</option>
        <option value="Space Grotesk">Space Grotesk (Tech Brutalist)</option>
      </select>
    </div>

    <button id="rev-copy-btn" style="width: 100%; background: var(--primary-color, #6366f1); color: #fff; font-weight: 700; border: none; border-radius: 8px; padding: 10px; cursor: pointer; font-size: 12px; transition: filter 0.2s;">
      📋 Copy Final Approved Style
    </button>
  `;

  document.body.appendChild(dock);

  const pInput = document.getElementById('rev-primary');
  const bInput = document.getElementById('rev-bg');
  const tInput = document.getElementById('rev-text');
  const fInput = document.getElementById('rev-font');

  if (savedConfig.font) fInput.value = savedConfig.font;

  function updateTokens() {
    const config = {
      primary: pInput.value,
      bg: bInput.value,
      text: tInput.value,
      font: fInput.value
    };
    root.style.setProperty('--primary-color', config.primary);
    root.style.setProperty('--bg-color', config.bg);
    root.style.setProperty('--text-color', config.text);
    root.style.setProperty('--font-family', `'${config.font}', sans-serif`);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  }

  pInput.addEventListener('input', updateTokens);
  bInput.addEventListener('input', updateTokens);
  tInput.addEventListener('input', updateTokens);
  fInput.addEventListener('change', updateTokens);

  document.getElementById('rev-copy-btn').addEventListener('click', function() {
    const cssSnippet = `/* Final Approved Client Brand Tokens */\n:root {\n  --primary-color: ${pInput.value};\n  --bg-color: ${bInput.value};\n  --text-color: ${tInput.value};\n  --font-family: '${fInput.value}', sans-serif;\n}`;
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
   The client clicks **"📋 Copy Final Approved Style"** and sends the 5-line CSS block to the developer.
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
