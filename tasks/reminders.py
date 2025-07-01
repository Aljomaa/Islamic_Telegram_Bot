import threading
import time
from datetime import datetime, timedelta
from utils.db import (
    get_all_user_ids,
    get_user_location,
    get_user_reminder_settings
)
import requests

API_PRAYER = "http://api.aladhan.com/v1/timings"

def send_adhkar(bot, user_id, time_of_day):
    """إرسال أذكار الصباح أو المساء"""
    if time_of_day == 'morning':
        text = "🌅 أذكار الصباح:\n\n🕌 {اذكر الله وابدأ يومك ببركة!}"
    elif time_of_day == 'evening':
        text = "🌇 أذكار المساء:\n\n🌙 {تحصّن بأذكار المساء قبل غروب الشمس}"
    else:
        return
    try:
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
    now = datetime.utcnow()
    users = get_all_user_ids()

    for user_id in users:
        loc = get_user_location(user_id)
        if not loc:
            continue

        lat, lon = loc
        try:
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
                prayer_time = datetime.strptime(timings[key], "%H:%M")
                now_local = now + timedelta(hours=3)  # مؤقتًا تعويض المنطقة الزمنية

                if (
                    prayer_time.hour == now_local.hour
                    and prayer_time.minute - now_local.minute == 10
                ):
                    bot.send_message(user_id, f"🕌 اقترب موعد صلاة {name} بعد 10 دقائق.")
        except Exception as e:
            print(f"[ERROR] أوقات الصلاة للمستخدم {user_id}: {e}")

def start_reminders(bot):
    """تشغيل التذكيرات في خيوط منفصلة"""

    def adhkar_loop():
        while True:
            now = datetime.utcnow() + timedelta(hours=3)
            if now.hour == 7 and now.minute == 0:
                for uid in get_all_user_ids():
                    settings = get_user_reminder_settings(uid)
                    if settings.get("morning_adhkar", True):
                        send_adhkar(bot, uid, "morning")
                time.sleep(60)

            elif now.hour == 19 and now.minute == 0:
                for uid in get_all_user_ids():
                    settings = get_user_reminder_settings(uid)
                    if settings.get("evening_adhkar", True):
                        send_adhkar(bot, uid, "evening")
                time.sleep(60)
            else:
                time.sleep(30)

    def jumuah_loop():
        while True:
            now = datetime.utcnow() + timedelta(hours=3)
            if now.weekday() == 4 and now.hour == 9 and now.minute == 0:
                for uid in get_all_user_ids():
                    settings = get_user_reminder_settings(uid)
                    if settings.get("jumuah", True):
                        send_jumuah_reminder(bot, uid)
                time.sleep(60)
            else:
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
