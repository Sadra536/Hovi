"""
aggregate_report.py
جمع‌کردن نتایج JSON همه‌ی کاربران شبیه‌سازی‌شده و ساخت یک گزارش خلاصه.
این اسکریپت توی job جداگانه (بعد از تموم شدن matrix) اجرا می‌شه.
"""

import json
import glob
import statistics

files = glob.glob("artifacts/**/result_*.json", recursive=True)

if not files:
    print("هیچ فایل نتیجه‌ای پیدا نشد.")
    exit(0)

all_stats = []
for path in files:
    with open(path, encoding="utf-8") as f:
        all_stats.append(json.load(f))

total_requests = sum(s["total_requests"] for s in all_stats)
total_success = sum(s["successful"] for s in all_stats)
total_failed = sum(s["failed"] for s in all_stats)

all_times = []
for s in all_stats:
    all_times.extend(s["response_times_ms"])

persona_breakdown = {}
for s in all_stats:
    p = s["persona"]
    persona_breakdown.setdefault(p, {"users": 0, "requests": 0, "success": 0, "failed": 0})
    persona_breakdown[p]["users"] += 1
    persona_breakdown[p]["requests"] += s["total_requests"]
    persona_breakdown[p]["success"] += s["successful"]
    persona_breakdown[p]["failed"] += s["failed"]

report_lines = []
report_lines.append("# گزارش شبیه‌سازی کاربران\n")
report_lines.append(f"- تعداد کاربران: **{len(all_stats)}**")
report_lines.append(f"- کل درخواست‌ها: **{total_requests}**")
report_lines.append(f"- موفق: **{total_success}** | ناموفق: **{total_failed}**")
if all_times:
    report_lines.append(f"- میانگین زمان پاسخ: **{round(statistics.mean(all_times), 1)}ms**")
    report_lines.append(f"- کمترین: **{min(all_times)}ms** | بیشترین: **{max(all_times)}ms**")
    if len(all_times) > 1:
        report_lines.append(f"- میانه (p50): **{round(statistics.median(all_times), 1)}ms**")
        sorted_times = sorted(all_times)
        p95_idx = int(len(sorted_times) * 0.95)
        report_lines.append(f"- p95: **{sorted_times[min(p95_idx, len(sorted_times)-1)]}ms**")

report_lines.append("\n## تفکیک بر اساس شخصیت کاربر\n")
report_lines.append("| شخصیت | تعداد کاربر | درخواست‌ها | موفق | ناموفق |")
report_lines.append("|---|---|---|---|---|")
for persona, d in persona_breakdown.items():
    report_lines.append(f"| {persona} | {d['users']} | {d['requests']} | {d['success']} | {d['failed']} |")

# خطاهای رایج (اگه بود)
errors = []
for s in all_stats:
    errors.extend(s.get("errors", []))
if errors:
    report_lines.append(f"\n## خطاها ({len(errors)} مورد)\n")
    for e in errors[:20]:
        report_lines.append(f"- {e}")
    if len(errors) > 20:
        report_lines.append(f"- ... و {len(errors) - 20} خطای دیگر")

report = "\n".join(report_lines)
print(report)

with open("summary.md", "w", encoding="utf-8") as f:
    f.write(report)
