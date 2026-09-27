#!/usr/bin/env python3
"""Generate the dunk-shot clip from prompt.json via a video-generation API.

Supported providers (pick with --provider or auto-detect from env):
  veo     Google Gemini API (Veo)         env: GEMINI_API_KEY
  runway  Runway Gen-4 (image-to-video)   env: RUNWAYML_API_SECRET  (needs --image)
  fal     fal.ai hosted Kling             env: FAL_KEY

Credentials may also be injected by the Claude Code environment proxy
("API credentials" in the environment settings). In that case no env var is
set: pass --provider explicitly (or set VIDEO_PROVIDER) and the script sends
requests without an auth header; the proxy adds it for the allowed host.
  veo    : allowed website generativelanguage.googleapis.com, header x-goog-api-key: <key>
  runway : allowed website api.dev.runwayml.com,            header Authorization: Bearer <key>
  fal    : allowed website queue.fal.run,                   header Authorization: Key <key>

Usage:
  python3 generate.py                       # auto-detect provider from env
  python3 generate.py --provider veo -o raw.mp4
  python3 generate.py --provider runway --image gym_empty.png

Output: a raw MP4 (native resolution / fps). Run postprocess.sh afterwards
to get 3840x2160 @ 60fps, 4 seconds.
"""
import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent


def load_prompt(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_text(p: dict) -> str:
    cam = p["camera"]
    loc = p["location"]
    sub = p["subject"]
    parts = [
        f"Photorealistic {p['duration_seconds']}-second live-action style video, {loc['type']}.",
        " ".join(s[0].upper() + s[1:] + "." for s in loc["details"]),
        (
            f"Camera: {cam['type']}, {cam['position']}, lens height {cam['height_cm']} cm, "
            f"{cam['tilt']}, {cam['movement']}. {cam['lens']}, natural undistorted perspective. "
            "The rim and backboard sit in the upper center of the frame, fully visible."
        ),
        (
            f"Subject: one {sub['description']}, {sub['height_cm']} cm tall, {sub['facing']}. "
            + " ".join(a[0].upper() + a[1:] + "." for a in p["action"])
        ),
        "Wardrobe: " + ", ".join(sub["wardrobe"]) + ".",
        "Look: " + ", ".join(p["look"]) + ".",
    ]
    return "\n".join(parts)


def build_negative(p: dict) -> str:
    return ", ".join(p["negative"])


def download(url: str, out: Path, headers=None):
    with requests.get(url, headers=headers, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    print(f"saved {out} ({out.stat().st_size / 1e6:.1f} MB)")


# --------------------------------------------------------------------------- veo
def auth_headers(env: str, header: str, prefix: str = "") -> dict:
    """Return the auth header if the key is in env, else {} (proxy-injected)."""
    key = os.environ.get(env)
    if not key:
        print(f"{env} not set; assuming the environment proxy injects '{header}'")
        return {}
    return {header: f"{prefix}{key}"}


def gen_veo(text: str, negative: str, out: Path, duration: int, model: str):
    base = "https://generativelanguage.googleapis.com/v1beta"
    auth = auth_headers("GEMINI_API_KEY", "x-goog-api-key")
    h = {**auth, "Content-Type": "application/json"}
    body = {
        "instances": [{"prompt": text}],
        "parameters": {
            "aspectRatio": "16:9",
            "negativePrompt": negative,
            "durationSeconds": max(duration, 5),  # Veo minimum is 5 s; trim in post
            "personGeneration": "allow_adult",
            "resolution": "1080p",
        },
    }
    r = requests.post(f"{base}/models/{model}:predictLongRunning", headers=h, json=body, timeout=60)
    r.raise_for_status()
    op = r.json()["name"]
    print("veo operation:", op)
    while True:
        time.sleep(10)
        s = requests.get(f"{base}/{op}", headers=h, timeout=60)
        s.raise_for_status()
        js = s.json()
        if js.get("done"):
            break
        print("  ...generating")
    if "error" in js:
        sys.exit(f"veo error: {js['error']}")
    vids = js["response"]["generateVideoResponse"]["generatedSamples"]
    uri = vids[0]["video"]["uri"]
    download(uri, out, headers=auth)


# ------------------------------------------------------------------------ runway
def gen_runway(text: str, out: Path, duration: int, image: Path, model: str):
    if not image:
        sys.exit("runway image-to-video needs --image (a still of the empty gym from the camera position)")
    b64 = base64.b64encode(image.read_bytes()).decode()
    mime = "image/png" if image.suffix.lower() == ".png" else "image/jpeg"
    h = {
        **auth_headers("RUNWAYML_API_SECRET", "Authorization", "Bearer "),
        "X-Runway-Version": "2024-11-06",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "promptImage": f"data:{mime};base64,{b64}",
        "promptText": text[:1000],
        "ratio": "1280:720",
        "duration": 5 if duration <= 5 else 10,
    }
    r = requests.post("https://api.dev.runwayml.com/v1/image_to_video", headers=h, json=body, timeout=60)
    r.raise_for_status()
    tid = r.json()["id"]
    print("runway task:", tid)
    while True:
        time.sleep(8)
        s = requests.get(f"https://api.dev.runwayml.com/v1/tasks/{tid}", headers=h, timeout=60)
        s.raise_for_status()
        js = s.json()
        st = js["status"]
        if st == "SUCCEEDED":
            break
        if st in ("FAILED", "CANCELLED"):
            sys.exit(f"runway {st}: {js.get('failure')}")
        print("  ...", st)
    download(js["output"][0], out)


# --------------------------------------------------------------------------- fal
def gen_fal(text: str, negative: str, out: Path, duration: int, model: str):
    h = {**auth_headers("FAL_KEY", "Authorization", "Key "), "Content-Type": "application/json"}
    body = {
        "prompt": text,
        "negative_prompt": negative,
        "duration": "5" if duration <= 5 else "10",
        "aspect_ratio": "16:9",
    }
    r = requests.post(f"https://queue.fal.run/{model}", headers=h, json=body, timeout=60)
    r.raise_for_status()
    js = r.json()
    status_url, response_url = js["status_url"], js["response_url"]
    print("fal request:", js.get("request_id"))
    while True:
        time.sleep(8)
        s = requests.get(status_url, headers=h, timeout=60)
        s.raise_for_status()
        st = s.json()["status"]
        if st == "COMPLETED":
            break
        print("  ...", st)
    res = requests.get(response_url, headers=h, timeout=60)
    res.raise_for_status()
    download(res.json()["video"]["url"], out)


# -------------------------------------------------------------------------- main
def detect_provider() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return "veo"
    if os.environ.get("RUNWAYML_API_SECRET"):
        return "runway"
    if os.environ.get("FAL_KEY"):
        return "fal"
    if os.environ.get("VIDEO_PROVIDER"):
        return os.environ["VIDEO_PROVIDER"]
    sys.exit(
        "No provider key found. Set GEMINI_API_KEY, RUNWAYML_API_SECRET or FAL_KEY, "
        "or pass --provider when the credential is injected by the environment proxy."
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=["veo", "runway", "fal"])
    ap.add_argument("--prompt", type=Path, default=HERE / "prompt.json")
    ap.add_argument("-o", "--out", type=Path, default=HERE / "out" / "raw.mp4")
    ap.add_argument("--image", type=Path, help="reference still (runway only)")
    ap.add_argument("--model", help="override provider model id")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt and exit")
    a = ap.parse_args()

    p = load_prompt(a.prompt)
    text, negative = build_text(p), build_negative(p)
    duration = int(p.get("duration_seconds", 4))

    if a.dry_run:
        print("=== PROMPT ===\n" + text + "\n\n=== NEGATIVE ===\n" + negative)
        return

    provider = a.provider or detect_provider()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    print(f"provider={provider} out={a.out}")

    if provider == "veo":
        gen_veo(text, negative, a.out, duration, a.model or "veo-3.0-generate-001")
    elif provider == "runway":
        gen_runway(text, a.out, duration, a.image, a.model or "gen4_turbo")
    else:
        gen_fal(text, negative, a.out, duration, a.model or "fal-ai/kling-video/v2.1/master/text-to-video")

    print("\nnext: ./postprocess.sh", a.out)


if __name__ == "__main__":
    main()
