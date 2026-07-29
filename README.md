# CKOS Hub

Chase's personal Mission Control, on a URL. One bookmark, phone or laptop,
always current. Business and life on one page.

This is **not** the team hub. `tkg-hub` is the team's transaction dashboard
with the team passcode. This repo carries net worth, VA disability income,
tax posture, the clearance decision, and family. Different repo, different
passcode, audience of one.

---

## Security

GitHub Pages on the free tier only serves **public** repositories. So the
page is never published as readable HTML.

`data/hub.enc.json` is the rendered dashboard encrypted with **AES-256-GCM**,
keyed from the passcode through **PBKDF2-SHA256 at 250,000 iterations**. What
ships to GitHub is ciphertext. The passcode is typed into the browser, never
sent anywhere, and decryption happens client-side in WebCrypto. GCM
authenticates, so a wrong passcode fails loudly rather than returning garbage.

Protects against: the URL leaking, or someone finding the repo.
Does not protect against: someone who has the passcode.

**The passcode is never committed.** It lives only in the gitignored
`.passcode` file. `deploy.sh` hard-refuses to push if `.passcode` or a
plaintext render is ever tracked.

"Stay unlocked on this device" saves the passcode to that browser's
localStorage so the phone never asks twice. The **Lock** chip in the
bottom-right corner of the page clears it.

---

## Refreshing

```bash
./deploy.sh
```

Rebuilds Mission Control from live CKOS state, encrypts it, pushes. Safe to
re-run.

A launchd job (`com.ckos.hub-deploy`) runs this nightly, so the page is
current every morning without anyone asking for it. Logs:
`~/Library/Logs/ckos-hub-deploy.log`.

To rebuild without deploying:

```bash
python3 build.py
```

---

## What renders

| Source | Becomes |
|---|---|
| `CKOS/state/hub.json` | The one thing, week, workstreams, triggers, conflicts, parked |
| `CKOS/threads/*.md` | The "Where we left off" cards |
| `CKOS/decisions/log.md` | Locked decisions |

Edit those, not the HTML. `CKOS/tools/mission_control.py` renders it.
