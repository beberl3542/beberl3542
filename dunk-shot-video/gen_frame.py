"""Generate a still frame with Gemini image models. Usage: gen_frame.py MODEL OUT.png PROMPT [REF.png ...]"""
import base64, json, sys, requests
model, out, prompt, *refs = sys.argv[1:]
parts = [{"text": prompt}]
for r in refs:
    parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(open(r, "rb").read()).decode()}})
body = {"contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9", "imageSize": "2K"}}}
r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", json=body, timeout=300)
if not r.ok:
    sys.exit(f"HTTP {r.status_code}: {r.text[:800]}")
js = r.json()
for p in js["candidates"][0]["content"]["parts"]:
    if "inlineData" in p:
        open(out, "wb").write(base64.b64decode(p["inlineData"]["data"])); print("saved", out, p["inlineData"]["mimeType"]); break
else:
    sys.exit("no image in response: " + json.dumps(js)[:800])
