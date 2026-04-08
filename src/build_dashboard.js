/**
 * Motory Dashboard Encryption — GitHub Actions version
 * Reads src/Motory_Dashboard.html, encrypts with AES-GCM 256-bit,
 * outputs index.html (repo root) with an inline password-protected login page.
 *
 * Usage: node src/build_dashboard.js
 */
const crypto = require('crypto');
const fs     = require('fs');
const path   = require('path');

const REPO_ROOT          = path.dirname(__dirname);
const SRC_DIR            = __dirname;
const DASHBOARD_PASSWORD = 'Motory@2026';

// Read source dashboard
const dashboardPath    = path.join(SRC_DIR, 'Motory_Dashboard.html');
const dashboardContent = fs.readFileSync(dashboardPath, 'utf8');

async function encrypt(text, password) {
  const salt        = crypto.getRandomValues(new Uint8Array(32));
  const iv          = crypto.getRandomValues(new Uint8Array(12));
  const keyMaterial = await crypto.webcrypto.subtle.importKey(
    'raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveKey']
  );
  const key = await crypto.webcrypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
    keyMaterial,
    { name: 'AES-GCM', length: 256 }, false, ['encrypt']
  );
  const encrypted = await crypto.webcrypto.subtle.encrypt(
    { name: 'AES-GCM', iv, tagLength: 128 }, key,
    new TextEncoder().encode(text)
  );
  const encArr = new Uint8Array(encrypted);
  const data   = encArr.slice(0, encArr.length - 16);
  const tag    = encArr.slice(encArr.length - 16);
  return {
    salt: Buffer.from(salt).toString('base64'),
    iv:   Buffer.from(iv).toString('base64'),
    tag:  Buffer.from(tag).toString('base64'),
    data: Buffer.from(data).toString('base64')
  };
}

(async () => {
  console.log('Encrypting dashboard...');
  const ep    = await encrypt(dashboardContent, DASHBOARD_PASSWORD);
  const epStr = JSON.stringify(ep);

  const loginHTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Motory Shop - Dashboard Access</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #0a1628 0%, #1b2a4a 50%, #0066cc 100%);
      font-family: 'Segoe UI', Arial, sans-serif;
    }
    .card {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 16px;
      padding: 48px 40px;
      width: 100%;
      max-width: 420px;
      text-align: center;
      backdrop-filter: blur(12px);
      box-shadow: 0 24px 64px rgba(0,0,0,0.4);
    }
    .logo { font-size: 36px; margin-bottom: 8px; }
    h1 { color: #fff; font-size: 22px; font-weight: 700; margin-bottom: 4px; }
    .subtitle { color: rgba(255,255,255,0.55); font-size: 13px; margin-bottom: 32px; }
    input[type=password] {
      width: 100%;
      padding: 14px 18px;
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.2);
      background: rgba(255,255,255,0.08);
      color: #fff;
      font-size: 15px;
      outline: none;
      margin-bottom: 14px;
      transition: border 0.2s;
    }
    input[type=password]:focus { border-color: #0099ff; }
    button {
      width: 100%;
      padding: 14px;
      border-radius: 10px;
      border: none;
      background: linear-gradient(90deg, #0066cc, #0099ff);
      color: #fff;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    button:hover { opacity: 0.88; }
    #msg { margin-top: 14px; font-size: 13px; min-height: 20px; color: #ff6b6b; }
    #msg.ok { color: #52c41a; }
    .lock { font-size: 48px; margin-bottom: 16px; }
    .confidential {
      margin-top: 28px;
      font-size: 11px;
      color: rgba(255,255,255,0.3);
      letter-spacing: 1px;
      text-transform: uppercase;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="lock">🔐</div>
    <h1>Motory Shop</h1>
    <div class="subtitle">Competitive Intelligence Dashboard</div>
    <input type="password" id="pw" placeholder="Enter access password" autocomplete="current-password">
    <button onclick="unlock()">Access Dashboard</button>
    <div id="msg"></div>
    <div class="confidential">Confidential · C-Level &amp; Shareholders</div>
  </div>

  <script>
    const EP = ${JSON.stringify(epStr)};

    async function unlock() {
      const pw  = document.getElementById('pw').value;
      const msg = document.getElementById('msg');
      if (!pw) { msg.textContent = 'Please enter the password.'; return; }
      msg.className = '';
      msg.textContent = 'Decrypting…';
      try {
        const ep = JSON.parse(EP);
        const salt = Uint8Array.from(atob(ep.salt), c => c.charCodeAt(0));
        const iv   = Uint8Array.from(atob(ep.iv),   c => c.charCodeAt(0));
        const tag  = Uint8Array.from(atob(ep.tag),  c => c.charCodeAt(0));
        const data = Uint8Array.from(atob(ep.data),  c => c.charCodeAt(0));
        const combined = new Uint8Array(data.length + tag.length);
        combined.set(data); combined.set(tag, data.length);
        const keyMat = await crypto.subtle.importKey(
          'raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']
        );
        const key = await crypto.subtle.deriveKey(
          { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
          keyMat, { name: 'AES-GCM', length: 256 }, false, ['decrypt']
        );
        const dec = await crypto.subtle.decrypt(
          { name: 'AES-GCM', iv, tagLength: 128 }, key, combined
        );
        const html = new TextDecoder().decode(dec);
        document.open(); document.write(html); document.close();
      } catch(e) {
        msg.textContent = 'Wrong password. Please try again.';
      }
    }

    document.getElementById('pw').addEventListener('keydown', e => {
      if (e.key === 'Enter') unlock();
    });
  </script>
</body>
</html>`;

  const outPath = path.join(REPO_ROOT, 'index.html');
  fs.writeFileSync(outPath, loginHTML);
  console.log('Done!', loginHTML.length, 'bytes');
})();
