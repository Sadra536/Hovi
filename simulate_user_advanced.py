"""
simulate_user.py (نسخه پیشرفته)
شبیه‌سازی رفتار کاربران واقعی با شخصیت‌های مختلف + جمع‌آوری آمار دقیق.

شخصیت‌ها:
    fast    - تندخون: مکث‌های کوتاه، سریع بین صفحات رد می‌شه
    slow    - کندخون: مکث‌های طولانی، هر صفحه رو با دقت می‌بینه
    chatty  - پرحرف: تعداد اکشن‌های زیاد توی هر نشست
    quiet   - ساکت: فقط چند تا اکشن کوتاه و می‌ره

خروجی: یک فایل JSON با آمار این کاربر (تعداد درخواست موفق/ناموفق،
میانگین زمان پاسخ، جزئیات هر درخواست) که توی ورک‌فلو به‌عنوان artifact
آپلود و در گزارش نهایی جمع می‌شه.
"""

import os
import random
import time
import sys
import json

try:
    import requests
except ImportError:
    print("پکیج requests نصب نیست. با: pip install requests")
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
USER_LABEL = os.environ.get("USER_LABEL", "user")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("SUPABASE_URL و SUPABASE_KEY باید ست بشن (به عنوان GitHub Secrets).")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

# جدول‌هایی که واقعاً توی هویت وجود دارن - اینا رو با اسم جدول‌های خودت جایگزین کن
READ_ENDPOINTS = [
    "/rest/v1/chats?select=id,updated_at&limit=20",
    "/rest/v1/messages?select=id,created_at&limit=20",
    "/rest/v1/profiles?select=id,username&limit=20",
]

# ---- تعریف شخصیت‌ها ----
PERSONAS = {
    "fast":   {"delay_range": (0.3, 1.2), "actions_range": (4, 7),  "sessions_range": (1, 2)},
    "slow":   {"delay_range": (3.0, 9.0), "actions_range": (2, 4),  "sessions_range": (1, 2)},
    "chatty": {"delay_range": (0.8, 2.5), "actions_range": (8, 15), "sessions_range": (2, 4)},
    "quiet":  {"delay_range": (1.0, 3.0), "actions_range": (1, 3),  "sessions_range": (1, 1)},
}


def pick_persona():
    # اگه از بیرون مشخص نشده، رندوم انتخاب می‌شه
    forced = os.environ.get("PERSONA")
    if forced in PERSONAS:
        return forced
    return random.choice(list(PERSONAS.keys()))


PERSONA_NAME = pick_persona()
PERSONA = PERSONAS[PERSONA_NAME]

stats = {
    "user_label": USER_LABEL,
    "persona": PERSONA_NAME,
    "total_requests": 0,
    "successful": 0,
    "failed": 0,
    "response_times_ms": [],
    "errors": [],
    "started_at": None,
    "finished_at": None,
}


def log(msg):
    print(f"[{USER_LABEL}/{PERSONA_NAME}] {msg}")


def human_delay(scale=1.0):
    a, b = PERSONA["delay_range"]
    time.sleep(random.uniform(a, b) * scale)


def do_request(endpoint):
    url = f"{SUPABASE_URL}{endpoint}"
    start = time.monotonic()
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        stats["total_requests"] += 1
        stats["response_times_ms"].append(elapsed_ms)
        if r.status_code < 400:
            stats["successful"] += 1
        else:
            stats["failed"] += 1
            stats["errors"].append({"endpoint": endpoint, "status": r.status_code})
        log(f"{endpoint.split('?')[0]} -> {r.status_code} ({elapsed_ms}ms)")
    except requests.RequestException as e:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        stats["total_requests"] += 1
        stats["failed"] += 1
        stats["errors"].append({"endpoint": endpoint, "error": str(e)})
        log(f"خطا در {endpoint.split('?')[0]}: {e}")


def open_app_session():
    log("در حال باز کردن اپ...")
    human_delay(scale=0.6)

    lo, hi = PERSONA["actions_range"]
    actions = random.randint(lo, hi)

    for i in range(actions):
        endpoint = random.choice(READ_ENDPOINTS)
        do_request(endpoint)

        # نوسان طبیعی مکث - حتی توی یک شخصیت، هر اکشن یکسان نیست
        pause_roll = random.random()
        if pause_roll < 0.15:
            human_delay(scale=0.3)   # رد شدن سریع
        elif pause_roll < 0.85:
            human_delay(scale=1.0)   # مکث معمولِ همون شخصیت
        else:
            human_delay(scale=2.2)   # موند و بیشتر خوند

    log("اپ رو بست.")


def main():
    stats["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    lo, hi = PERSONA["sessions_range"]
    sessions = random.randint(lo, hi)
    for s in range(sessions):
        open_app_session()
        if s < sessions - 1:
            human_delay(scale=4.0)  # فاصله بین دو بار باز کردن اپ

    stats["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # محاسبه میانگین زمان پاسخ
    times = stats["response_times_ms"]
    stats["avg_response_ms"] = round(sum(times) / len(times), 1) if times else None
    stats["max_response_ms"] = max(times) if times else None
    stats["min_response_ms"] = min(times) if times else None

    out_path = f"result_{USER_LABEL}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    log(f"پایان. {stats['successful']} موفق / {stats['failed']} ناموفق "
        f"از {stats['total_requests']} درخواست. نتیجه در {out_path}")


if __name__ == "__main__":
    main()
