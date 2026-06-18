#!/usr/bin/env python3
"""
Client-side page lock. Encrypts a rendered HTML page with a password (AES-256-GCM,
key via PBKDF2-SHA256) and wraps it in a tiny prompt page that decrypts in the
browser with the Web Crypto API. The password is NEVER written into the output;
only ciphertext is. The plaintext password is supplied at build time from an env
var and used only to encrypt. View-source of the published page reveals only the
ciphertext, so protection is as strong as the password.

Not a server auth system (these are static pages), but unlike a JS "hide" gate the
content is genuinely encrypted, not merely hidden.
"""
import base64, hashlib, json, os

PBKDF2_ITERS = 200_000


def _b64(b):
    return base64.b64encode(b).decode("ascii")


def lock_page(inner_html, password, title="Locked", iters=PBKDF2_ITERS):
    """Return a standalone HTML page that decrypts `inner_html` given `password`."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, nonce = os.urandom(16), os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters, 32)
    ct = AESGCM(key).encrypt(nonce, inner_html.encode("utf-8"), None)  # ct||tag
    blob = json.dumps({"s": _b64(salt), "iv": _b64(nonce), "ct": _b64(ct), "it": iters})
    return _TEMPLATE.replace("__TITLE__", title).replace("__BLOB__", blob)


_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="https://crownoak.github.io/wdeve/common.css"></head>
<body>
<div class="gate"><div class="card">
  <h1>__TITLE__</h1>
  <p>Protected. Enter the password.</p>
  <input id="pw" type="password" autofocus autocomplete="current-password" placeholder="password">
  <button id="go">Unlock</button>
  <div class="err" id="err"></div>
</div></div>
<script>
const B = __BLOB__;
const dec = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
async function decrypt(pw) {
  const km = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey(
    {name:"PBKDF2", salt:dec(B.s), iterations:B.it, hash:"SHA-256"},
    km, {name:"AES-GCM", length:256}, false, ["decrypt"]);
  const pt = await crypto.subtle.decrypt({name:"AES-GCM", iv:dec(B.iv)}, key, dec(B.ct));
  return new TextDecoder().decode(pt);
}
async function tryUnlock(pw, save) {
  try {
    const html = await decrypt(pw);
    if (save) sessionStorage.setItem("eve_k", pw);
    document.open(); document.write(html); document.close();
  } catch (e) {
    sessionStorage.removeItem("eve_k");
    const el = document.getElementById("err"); if (el) el.textContent = "Wrong password.";
  }
}
document.getElementById("go").onclick = () => tryUnlock(document.getElementById("pw").value, true);
document.getElementById("pw").addEventListener("keydown", e => { if (e.key === "Enter") document.getElementById("go").click(); });
const saved = sessionStorage.getItem("eve_k");
if (saved) tryUnlock(saved, false);   // re-decrypt silently after a meta-refresh within the session
</script>
</body></html>"""
