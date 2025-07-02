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

# لتجنب السبام في الصلاة
last_sent_prayer = {}

def send_adhkar(bot, user_id, time_of_day):
    try:
        response = requests.get(ATHKAR_API, timeout=10)
        data = response.json()

        if time_of_day == 'morning':
            azkar = data.get("أذكار الصباح", [])
        elif time_of_day == 'evening':
            azkar = data.get("أذكار المساء", [])
        else:
            return

        for item in azkar[:10]:  # أرسل أول 10 أذكار فقط
            text = f"📿 {item.get('zekr', '').strip()}"
            bot.send_message(user_id, text)
    except Exception as e:
        print(f"[ERROR] إرسال أذكار {time_of_day}: {e}")

def send_jumuah_reminder(bot, user_id):
    msg = (
        "📿 جمعة مباركة!\n\n"
        "📖 لا تنس قراءة سورة الكهف اليوم.\n"
        "💌 وأكثر من الصلاة على النبي ﷺ.\n\n"
        "اللهم صلِّ وسلم على نبينا محمد"
    )
    try:
        bot.send_message(user_id, msg)
    except Exception as e:
        print(f"[ERROR] تذكير الجمعة: {e}")

def should_send_prayer_reminder(user_id, prayer_key):
    now = datetime.utcnow()
    key = (user_id, prayer_key)
    last_time = last_sent_prayer.get(key)

    if not last_time or (now - last_time) > timedelta(minutes=30):
        last_sent_prayer[key] = now
        return True
    return False

def send_prayer_reminders(bot):
    now_utc = datetime.utcnow()
    for user_id in get_all_user_ids():
        lat, lon = get_user_location(user_id)
        tz_name = get_user_timezone(user_id)

        if not lat or not lon:
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
                prayer_time = user_tz.localize(prayer_time)

                delta = (prayer_time - now_user).total_seconds() / 60
                if 9 <= delta <= 11:
                    if should_send_prayer_reminder(user_id, key):
                        bot.send_message(
                            user_id,
                            f"🕌 اقترب موعد صلاة {name} بعد 10 دقائق، تجهز أثابك الله وهداك ونفع بك 🤲"
                        )
        except Exception as e:
            print(f"[ERROR] تذكير الصلاة للمستخدم {user_id}: {e}")

def start_reminders(bot):
    def adhkar_loop():
        while True:
            now_utc = datetime.utcnow()
            for uid in get_all_user_ids():
                tz_name = get_user_timezone(uid)
                user_tz = tz(tz_name) if tz_name != "auto" else utc
                now_local = now_utc.replace(tzinfo=utc).astimezone(user_tz)
                settings = get_user_reminder_settings(uid)

                if now_local.hour == 7 and now_local.minute == 0:
                    if settings.get("morning_adhkar", True):
                        send_adhkar(bot, uid, "morning")

                if now_local.hour == 19 and now_local.minute == 0:
                    if settings.get("evening_adhkar", True):
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

                if now_local.weekday() == 4 and now_local.hour == 9 and now_local.minute == 0:
                    if settings.get("jumuah", True):
                        send_jumuah_reminder(bot, uid)

            time.sleep(60)

    def prayer_loop():
        while True:
            for uid in get_all_user_ids():
                settings = get_user_reminder_settings(uid)
                if settings.get("prayer", True):
                    send_prayer_reminders(bot)
            time.sleep(60)

    threading.Thread(target=adhkar_loop, daemon=True).start()
    threading.Thread(target=jumuah_loop, daemon=True).start()
    threading.Thread(target=prayer_loop, daemon=True).start()
