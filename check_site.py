"""
check_site.py
تست سلامت و زمان پاسخ سایت شهرداری سرخرود (sorkhroud.ir) با ۲ کاربر شبیه‌سازی‌شده.
هر کاربر چند صفحه از سایت رو باز می‌کنه، کد وضعیت و زمان پاسخ رو ثبت می‌کنه.
"""

import os
import random
import time
import json
import sys

try:
    import requests
except ImportError:
    print("پکیج requests نصب نیست. با: pip install requests")
    sys.exit(1)

SITE_URL = os.environ.get("SITE_URL", "https://sorkhroud.ir").rstrip("/")
USER_LABEL = os.environ.get("USER_LABEL", "user")

# صفحاتی که چک می‌شن - اگه صفحه‌ی دیگه‌ای مهمه (اخبار، تماس با ما و ...) اضافه کن
PAGES = [
    "/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SiteHealthCheck/1.0)"
}

stats = {
    "user_label": USER_LABEL,
    "total_requests": 0,
    "successful": 0,
    "failed": 0,
    "response_times_ms": [],
    "details": [],
}


def log(msg):
    print(f"[{USER_LABEL}] {msg}")


def human_delay(a=1.0, b=3.0):
    time.sleep(random.uniform(a, b))


def check_page(path):
    url = f"{SITE_URL}{path}"
    start = time.monotonic()
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        stats["total_requests"] += 1
        stats["response_times_ms"].append(elapsed_ms)
        ok = r.status_code < 400
        stats["successful" if ok else "failed"] += 1
        stats["details"].append({
            "path": path, "status": r.status_code,
            "ms": elapsed_ms, "content_length": len(r.content)
        })
        log(f"{path} -> {r.status_code} ({elapsed_ms}ms, {len(r.content)} بایت)")
    except requests.RequestException as e:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        stats["total_requests"] += 1
        stats["failed"] += 1
        stats["details"].append({"path": path, "error": str(e), "ms": elapsed_ms})
        log(f"خطا در {path}: {e}")


def main():
    log(f"شروع بازدید از {SITE_URL}")
    human_delay(0.5, 2)

    # هر کاربر چند بار صفحه رو باز می‌کنه (شبیه رفرش/گشتن)
    visits = random.randint(3, 5)
    for _ in range(visits):
        page = random.choice(PAGES)
        check_page(page)
        human_delay(1, 4)

    times = stats["response_times_ms"]
    stats["avg_response_ms"] = round(sum(times) / len(times), 1) if times else None

    out_path = f"result_{USER_LABEL}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    log(f"پایان. {stats['successful']} موفق / {stats['failed']} ناموفق، "
        f"میانگین پاسخ: {stats['avg_response_ms']}ms")


if __name__ == "__main__":
    main()
