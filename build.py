#!/usr/bin/env python3
"""
CKOS Hub — build step.

Regenerates Mission Control from live CKOS state, then encrypts the rendered
page into data/hub.enc.json with AES-256-GCM.

Why encrypted: GitHub Pages on the free tier only serves PUBLIC repos. This
page carries net worth, VA disability income, tax posture, family, and the
clearance decision. Ciphertext ships to the public repo; plaintext exists only
in Chase's browser after he enters the passcode.

This is the personal hub. It is deliberately NOT the team's tkg-hub repo and
NOT the team passcode.

Usage:
    python3 build.py                        # prompts, or reads .passcode
    CKOS_HUB_PASSCODE='...' python3 build.py
    python3 build.py --no-render            # encrypt whatever is on disk
"""

import base64
import getpass
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "tools"))
from ckos_paths import TOOLS, SYSTEM_REPORTS   # noqa: E402
# Each entry: renderer script, rendered page, encrypted output, payload title.
# Mission Control is the state of everything; the Library is every deliverable
# CKOS has produced, indexed by topic so nothing needs a file path to find.
PAGES = [
    (TOOLS / "mission_control.py",
     SYSTEM_REPORTS / "mission-control.html",
     ROOT / "data" / "hub.enc.json",
     "CKOS Mission Control"),
    (TOOLS / "library.py",
     SYSTEM_REPORTS / "library.html",
     ROOT / "data" / "library.enc.json",
     "CKOS Library"),
]

PBKDF2_ITERATIONS = 250_000


def encrypt(payload_bytes, passcode):
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", passcode.encode(), salt, PBKDF2_ITERATIONS, 32)
    iv = os.urandom(12)
    ct = AESGCM(key).encrypt(iv, payload_bytes, None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {
        "v": 1,
        "kdf": {"name": "PBKDF2-SHA256", "iterations": PBKDF2_ITERATIONS, "salt": b64(salt)},
        "cipher": "AES-256-GCM",
        "iv": b64(iv),
        "ct": b64(ct),
    }


def resolve_passcode():
    pc = os.environ.get("CKOS_HUB_PASSCODE")
    if pc:
        return pc.strip()
    local = ROOT / ".passcode"
    if local.exists():
        return local.read_text().strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return getpass.getpass("CKOS hub passcode: ")


def main():
    passcode = resolve_passcode()
    if len(passcode) < 8:
        sys.exit("Passcode must be at least 8 characters.")

    for renderer, page, out, title in PAGES:
        if "--no-render" not in sys.argv:
            # Always rebuild from live state so the deployed page is never stale.
            subprocess.run([sys.executable, str(renderer)], check=True)

        if not page.exists():
            sys.exit(f"Missing {page}. Run {renderer.name} first.")

        payload = {
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "title": title,
            "html": page.read_text(),
        }
        blob = json.dumps(payload, separators=(",", ":")).encode()

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(encrypt(blob, passcode), indent=2))

        print(f"Wrote {out.relative_to(ROOT)}")
        print(f"  {len(blob):,} bytes plaintext -> {out.stat().st_size:,} bytes ciphertext")


if __name__ == "__main__":
    main()
