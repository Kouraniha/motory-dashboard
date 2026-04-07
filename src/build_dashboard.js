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

const REPO_ROOT  = path.dirname(__dirname);
const SRC_DIR    = __dirname;
const DASHBOARD_PASSWORD = 'Motory@2026';

// Read source dashboard
const dashboardPath = path.join(SRC_DIR, 'Motory_Dashboard.html');
const dashboardContent = fs.readFileSync(dashboardPath, 'utf8');

// ─── AES-GCM Encryption ───────────────────────────────────────────────────────
async function encrypt(text, password) {
  const salt = crypto.getRandomValues(new Uint8Array(32));
  const iv   = crypto.getRandomValues(new Uint8Array(12));

  const keyMaterial = await crypto.webcrypto.subtle.importKey(
    'raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveKey']
  );
  const key = await crypto.webcrypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt']
  );

  const encrypted = await crypto.webcrypto.subtle.encrypt(
    { name: 'AES-GCM', iv, tagLength: 128 },
    key,
    new TextEncoder().encode(text)
  );

  const encArr = new Uint8Array(encrypted);
  const data   = encArr.slice(0, encArr.length - 16);
  const tag    = encArr.slice(encArr.length - 16);

  return {
    salt: Buffer.from(salt).toString('base64'),
    iv:   Buffer.from(iv).toString('base64'),
    tag:  Buffer.from(tag).toString('base64'),
    data: Buffer.from(data).toString('base64'),
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
</style>
</head>`;
  const outPath = path.join(REPO_ROOT, 'index.html');
  fs.writeFileSync(outPath, loginHTML);
  console.log('Done!');
})();
