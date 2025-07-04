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
ATHKAR_API = "https://ahegazy.github.io/muslimKit/json/"

last_sent_prayer = {}
last_sent_adhkar = {}

# ✅ إرسال أذكار الصباح أو المساء
def send_adhkar(bot, user_id, time_of_day):
    try:
        endpoint = "azkar_sabah.json" if time_of_day == "morning" else "azkar_massa.json"
        response = requests.get(f"{ATHKAR_API}{endpoint}", timeout=10)
        data = response.json()
        azkar = data.get("content", [])[:10]

        message = f"📿 أذكار {'الصباح' if time_of_day == 'morning' else 'المساء'}:\n" + "-"*50 + "\n"
        for i, item in enumerate(azkar, 1):
            text = item.get("zekr", "").strip()
            repeat = item.get("repeat", "غير مذكور")
            message += f"{i}. 📖 {text}\n🔁 التكرار: {repeat}\n\n"

        bot.send_message(user_id, message)
    except Exception as e:
        print(f"[ERROR] إرسال أذكار {time_of_day} للمستخدم {user_id}: {e}")

# ✅ تذكير الجمعة
def send_jumuah_reminder(bot, user_id):
    try:
        bot.send_message(user_id,
            "🌙 جمعة مباركة!\n\n"
            "📖 لا تنسَ قراءة *سورة الكهف* اليوم.\n"
            "💌 وأكثر من الصلاة على النبي ﷺ.\n\n"
            "اللهم صلِّ وسلم على نبينا محمد"
        )
    except Exception as e:
        print(f"[ERROR] تذكير الجمعة للمستخدم {user_id}: {e}")

# ✅ منع التكرار لتذكير الصلاة
def should_send(user_id, prayer_key):
    now = datetime.utcnow()
    key = (user_id, prayer_key)
    last = last_sent_prayer.get(key)
    if not last or (now - last) > timedelta(minutes=10):
        last_sent_prayer[key] = now
        return True
    return False

# ✅ منع التكرار لتذكير الأذكار بعد الصلاة
def should_send_adhkar(user_id, label):
    now = datetime.utcnow()
    key = (user_id, label)
    last = last_sent_adhkar.get(key)
    if not last or (now - last) > timedelta(minutes=60):
        last_sent_adhkar[key] = now
        return True
    return False

# ✅ تذكير الصلاة + أذكار بعد الفجر والعشاء
def send_prayer_reminders(bot):
    now_utc = datetime.utcnow()
    for user_id in get_all_user_ids():
        lat, lon = get_user_location(user_id)
        tz_name = get_user_timezone(user_id)
        settings = get_user_reminder_settings(user_id)

        if not lat or not lon or not settings.get("prayer", True):
            continue

        try:
            user_tz = tz(tz_name) if tz_name and tz_name != "auto" else utc
            now_user = now_utc.replace(tzinfo=utc).astimezone(user_tz)

            response = requests.get(f"{API_PRAYER}?latitude={lat}&longitude={lon}&method=4", timeout=10)
            timings = response.json()["data"]["timings"]

            prayers = {
                "Fajr": "الفجر",
                "Dhuhr": "الظهر",
                "Asr": "العصر",
                "Maghrib": "المغرب",
                "Isha": "العشاء"
            }

            for key, name in prayers.items():
                prayer_time = datetime.strptime(timings[key], "%H:%M").replace(
                    year=now_user.year, month=now_user.month, day=now_user.day
                )
                prayer_time = user_tz.localize(prayer_time, is_dst=None)

                # ⏰ التذكير قبل الصلاة بـ10 دقائق (مرونة ±6 دقائق)
                remind_time = prayer_time - timedelta(minutes=10)
                minutes_to_reminder = (remind_time - now_user).total_seconds() / 60
                if -2 <= minutes_to_reminder <= 6 and should_send(user_id, key):
                    bot.send_message(
                        user_id,
                        f"🕌 {name}\n"
                        "لم يتبقَّ الكثير على الأذان والصلاة ⏳ فلا تنساها ولا تتغافل عنها ✨\n"
                        "اللهم اجعلنا من المحافظين عليها 🤲"
                    )

                # 🕯️ أذكار بعد الفجر أو العشاء بين 28–32 دقيقة
                if key in ["Fajr", "Isha"]:
                    target = "morning" if key == "Fajr" else "evening"
                    delta = (now_user - prayer_time).total_seconds() / 60
                    if 28 <= delta <= 32 and should_send_adhkar(user_id, f"{key}_athkar"):
                        send_adhkar(bot, user_id, target)

        except Exception as e:
            print(f"[ERROR] تذكير الصلاة للمستخدم {user_id}: {e}")

# ✅ الحلقات
def start_reminders(bot):
    def jumuah_loop():
        while True:
            now_utc = datetime.utcnow()
            for uid in get_all_user_ids():
                tz_name = get_user_timezone(uid)
                user_tz = tz(tz_name) if tz_name and tz_name != "auto" else utc
                now_local = now_utc.replace(tzinfo=utc).astimezone(user_tz)
                settings = get_user_reminder_settings(uid)
                if now_local.weekday() == 4 and now_local.hour == 9 and now_local.minute == 0 and settings.get("jumuah", True):
                    send_jumuah_reminder(bot, uid)
            time.sleep(60)

    def prayer_loop():
        while True:
            send_prayer_reminders(bot)
            time.sleep(30)

    threading.Thread(target=jumuah_loop, daemon=True).start()
    threading.Thread(target=prayer_loop, daemon=True).start()
