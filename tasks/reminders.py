import threading
import time
import requests
from datetime import datetime, timedelta
from utils.db import (
    get_all_user_ids,
    get_user_location,
    get_user_timezone,
    get_user_reminder_settings
)
from pytz import timezone as tz, utc

API_PRAYER = "http://api.aladhan.com/v1/timings"
ATHKAR_API = "https://raw.githubusercontent.com/hisnmuslim/hisn-muslim-api/main/ar/hisn.json"

def send_adhkar(bot, user_id, time_of_day):
    """إرسال أذكار الصباح أو المساء من API"""
    try:
        response = requests.get(ATHKAR_API, timeout=10)
        data = response.json()
        if time_of_day == 'morning':
            azkar = data.get("أذكار الصباح", [])
        elif time_of_day == 'evening':
            azkar = data.get("أذكار المساء", [])
        else:
            return

        if not azkar:
            return

        # إرسال 3 أذكار عشوائية من القائمة
        for item in azkar[:3]:
            text = f"📿 {item.get('content', '').strip()}"
            bot.send_message(user_id, text)
    except Exception as e:
        print(f"[ERROR] إرسال أذكار {time_of_day}: {e}")

def send_jumuah_reminder(bot, user_id):
    """إرسال تذكير الجمعة"""
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

def send_prayer_reminders(bot):
    """إرسال تنبيهات الصلاة قبل 10 دقائق"""
    now_utc = datetime.utcnow()
    for user_id in get_all_user_ids():
        lat, lon = get_user_location(user_id)
        tz_name = get_user_timezone(user_id)

        if not lat or not lon:
            continue

        try:
            # توقيت المستخدم
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

                # الفارق بين الآن ووقت الصلاة
                delta = (prayer_time - now_user).total_seconds() / 60
                if 9 <= delta <= 11:  # تقريباً 10 دقائق قبل الأذان
                    bot.send_message(user_id, f"🕌 اقترب موعد صلاة {name} بعد 10 دقائق.")
        except Exception as e:
            print(f"[ERROR] تذكير الصلاة للمستخدم {user_id}: {e}")

def start_reminders(bot):
    """تشغيل جميع التذكيرات في خيوط منفصلة"""

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
