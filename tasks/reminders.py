import threading
import time
import requests
from datetime import datetime, timedelta
from pytz import timezone as tz, utc
from utils.db import (
    get_all_user_ids,
    get_user_location,
    get_user_timezone,
    get_user_reminder_settings
)

API_PRAYER = "http://api.aladhan.com/v1/timings"
ATHKAR_API = "https://raw.githubusercontent.com/hisnmuslim/hisn-muslim-api/main/ar/hisn.json"

# منع التكرار في تذكير الصلاة
last_sent_prayer = {}

# ✅ إرسال أذكار الصباح أو المساء
def send_adhkar(bot, user_id, time_of_day):
    try:
        response = requests.get(ATHKAR_API, timeout=10)
        data = response.json()
        azkar = data.get("أذكار الصباح" if time_of_day == "morning" else "أذكار المساء", [])

        for item in azkar[:10]:
            text = f"📿 {item.get('zekr', '').strip()}"
            bot.send_message(user_id, text)

    except Exception as e:
        print(f"[ERROR] إرسال أذكار {time_of_day} للمستخدم {user_id}: {e}")

# ✅ إرسال تذكير الجمعة
def send_jumuah_reminder(bot, user_id):
    try:
        bot.send_message(user_id, (
            "📿 جمعة مباركة!\n\n"
            "📖 لا تنس قراءة سورة الكهف اليوم.\n"
            "💌 وأكثر من الصلاة على النبي ﷺ.\n\n"
            "اللهم صلِّ وسلم على نبينا محمد"
        ))
    except Exception as e:
        print(f"[ERROR] تذكير الجمعة للمستخدم {user_id}: {e}")

# ✅ تحديد هل تم إرسال تذكير قريباً أم لا
def should_send(user_id, prayer_key):
    now = datetime.utcnow()
    key = (user_id, prayer_key)
    last = last_sent_prayer.get(key)

    if not last or (now - last) > timedelta(minutes=10):
        last_sent_prayer[key] = now
        return True
    return False

# ✅ إرسال تذكير الصلاة قبل 10 دقائق
def send_prayer_reminders(bot):
    now_utc = datetime.utcnow()
    for user_id in get_all_user_ids():
        lat, lon = get_user_location(user_id)
        tz_name = get_user_timezone(user_id)
        settings = get_user_reminder_settings(user_id)

        if not lat or not lon or not settings.get("prayer", True):
            continue

        try:
            user_tz = tz(tz_name) if tz_name != "auto" else utc
            now_user = now_utc.replace(tzinfo=utc).astimezone(user_tz)

            response = requests.get(
                f"{API_PRAYER}?latitude={lat}&longitude={lon}&method=4",
                timeout=10
            )
            timings = response.json()["data"]["timings"]

            prayers = {
                "Fajr": "الفجر",
                "Dhuhr": "الظهر",
                "Asr": "العصر",
                "Maghrib": "المغرب",
                "Isha": "العشاء"
            }

            for key, name in prayers.items():
                prayer_str = timings[key]
                prayer_time = datetime.strptime(prayer_str, "%H:%M").replace(
                    year=now_user.year, month=now_user.month, day=now_user.day
                )
                prayer_time = user_tz.localize(prayer_time, is_dst=None)
                remind_time = prayer_time - timedelta(minutes=10)

                minutes_to_reminder = (remind_time - now_user).total_seconds() / 60
                if 0 <= minutes_to_reminder <= 1 and should_send(user_id, key):
                    bot.send_message(
                        user_id,
                        f"🕌 تبقّى 10 دقائق على أذان {name}.\nتهيّأ للصلاة وكن من الذاكرين 🤲"
                    )

        except Exception as e:
            print(f"[ERROR] تذكير الصلاة للمستخدم {user_id}: {e}")

# ✅ بدء الحلقات الثلاثة
def start_reminders(bot):
    def adhkar_loop():
        while True:
            now_utc = datetime.utcnow()
            for uid in get_all_user_ids():
                tz_name = get_user_timezone(uid)
                user_tz = tz(tz_name) if tz_name != "auto" else utc
                now_local = now_utc.replace(tzinfo=utc).astimezone(user_tz)
                settings = get_user_reminder_settings(uid)

                if now_local.hour == 7 and now_local.minute == 0 and settings.get("morning_adhkar", True):
                    send_adhkar(bot, uid, "morning")
                if now_local.hour == 19 and now_local.minute == 0 and settings.get("evening_adhkar", True):
                    send_adhkar(bot, uid, "evening")

            time.sleep(60)

    def jumuah_loop():
        while True:
            now_utc = datetime.utcnow()
            for uid in get_all_user_ids():
                tz_name = get_user_timezone(uid)
                user_tz = tz(tz_name) if tz_name != "auto" else utc
                now_local = now_utc.replace(tzinfo=utc).astimezone(user_tz)
                settings = get_user_reminder_settings(uid)

                if now_local.weekday() == 4 and now_local.hour == 9 and now_local.minute == 0 and settings.get("jumuah", True):
                    send_jumuah_reminder(bot, uid)

            time.sleep(60)

    def prayer_loop():
        while True:
            send_prayer_reminders(bot)
            time.sleep(30)  # فحص كل نصف دقيقة لضمان الدقة

    threading.Thread(target=adhkar_loop, daemon=True).start()
    threading.Thread(target=jumuah_loop, daemon=True).start()
    threading.Thread(target=prayer_loop, daemon=True).start()
