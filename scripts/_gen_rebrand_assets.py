import base64, os, sys, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("PIAPI_API_KEY")
if not api_key:
    sys.exit("falta PIAPI_API_KEY")

OUT = Path("assets/mindcheckpoint_rebrand")
OUT.mkdir(parents=True, exist_ok=True)

STYLE_SUFFIX = (
    " Flat vector illustration, bold clean outlines, dramatic teal-and-charcoal "
    "palette with one accent of gold/amber light. No text, no watermark, no logo."
)

JOBS = [
    {
        "name": "banner_v2.png",
        "aspect": "16:9",
        "prompt": (
            "YouTube channel banner, 2560x1440. CRITICAL SAFE-ZONE RULE: every important "
            "element (the raccoon, the gavel, all readable detail) must be fully contained "
            "inside the exact horizontal-center 60% and vertical-center 30% of the frame -- "
            "a small, compact, self-contained composition placed dead-center, noticeably "
            "smaller than the canvas, well clear of all four edges and clear of the very top "
            "and very bottom. Do not let the subject touch or cross the top edge. "
            "Subject: a sly gray raccoon mascot, glowing teal eyes, small dark hoodie, smug "
            "knowing grin, sitting cross-legged on top of a judge's gavel. The vast area "
            "outside that center box is a simple, mostly-empty dark charcoal gradient "
            "background with only faint, low-contrast silhouettes far out near the edges "
            "(classroom desk on the left edge, spinning wheel of fortune on the right edge) "
            "that can be safely cropped away." + STYLE_SUFFIX
        ),
    },
]

for job in JOBS:
    payload = {
        "model": "seedream",
        "task_type": "seedream-5-lite",
        "input": {
            "prompt": job["prompt"],
            "aspect_ratio": job["aspect"],
            "output_format": "png",
        },
    }
    r = requests.post(
        "https://api.piapi.ai/api/v1/task",
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    task_id = r.json()["data"]["task_id"]

    done = False
    for _ in range(60):
        time.sleep(2)
        poll = requests.get(
            f"https://api.piapi.ai/api/v1/task/{task_id}",
            headers={"X-API-Key": api_key},
            timeout=30,
        )
        poll.raise_for_status()
        task = poll.json()["data"]
        status = task.get("status", "").lower()
        if status in ("completed", "success"):
            output = task.get("output", {})
            img_url = (output.get("image_urls") or output.get("images") or [None])[0]
            if not img_url:
                print(f"FAIL {job['name']}: sin imagen de salida -- {output}")
                break
            img_resp = requests.get(img_url, timeout=60)
            img_resp.raise_for_status()
            (OUT / job["name"]).write_bytes(img_resp.content)
            print(f"OK {job['name']}")
            done = True
            break
        if status in ("failed", "error"):
            print(f"FAIL {job['name']}: {task.get('error')}")
            break
    if not done and status not in ("failed", "error"):
        print(f"TIMEOUT {job['name']}")
