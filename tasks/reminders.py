import threading
import time
import datetime
import requests
import pytz
from utils.db import get_all_users, get_user_location, get_user_timezone, user_notifications_enabled
from telebot import TeleBot
from config import BOT_TOKEN

bot = TeleBot(BOT_TOKEN)

# ========================================================
# 📌 دالة إرسال رسالة جماعية (تُستخدم داخل المهام)
# ========================================================
def broadcast_message(user_ids, text):
    for uid in user_ids:
        try:
            bot.send_message(uid, text, parse_mode="Markdown")
        except:
            continue

# ========================================================
# 📿 أذكار الصباح والمساء حسب التوقيت المحلي
# ========================================================
def send_morning_evening_adhkar():
    while True:
        now_utc = datetime.datetime.utcnow()
        for user in get_all_users():
            if not user_notifications_enabled(user["_id"]):
                continue

            tz = pytz.timezone(user.get("timezone", "Asia/Riyadh"))
            user_now = now_utc.replace(tzinfo=pytz.utc).astimezone(tz)
            hour = user_now.hour
            minute = user_now.minute

            # الساعة 7 صباحاً
            if hour == 7 and minute == 0 and not user.get("sent_morning"):
                try:
                    bot.send_message(user["_id"], "☀️ *أذكار الصباح*:\nhttps://salla.sa/s/Zz0Rwo", parse_mode="Markdown")
                    user["sent_morning"] = True
                except:
                    continue

            # الساعة 7 مساءً
            if hour == 19 and minute == 0 and not user.get("sent_evening"):
                try:
                    bot.send_message(user["_id"], "🌙 *أذكار المساء*:\nhttps://salla.sa/s/mLNnxW", parse_mode="Markdown")
                    user["sent_evening"] = True
                except:
                    continue

        time.sleep(60)

# ========================================================
# 🕌 تذكير قبل الصلاة بـ 10 دقائق (حسب موقع المستخدم)
# ========================================================
def notify_prayer():
    while True:
        now_utc = datetime.datetime.utcnow()

        for user in get_all_users():
            if not user_notifications_enabled(user["_id"]):
                continue

            lat, lon = get_user_location(user["_id"])
            if not lat or not lon:
                continue

            tz = pytz.timezone(user.get("timezone", "Asia/Riyadh"))
            user_now = now_utc.replace(tzinfo=pytz.utc).astimezone(tz)

            date = user_now.strftime("%Y-%m-%d")
            res = requests.get(f"https://api.aladhan.com/v1/timings/{date}?latitude={lat}&longitude={lon}&method=4")
            if res.status_code != 200:
                continue

            timings = res.json()["data"]["timings"]
            for prayer, time_str in timings.items():
                try:
                    hour, minute = map(int, time_str.split(":"))
                    prayer_time = user_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    delta = (prayer_time - user_now).total_seconds()

                    if 540 <= delta <= 600:  # من 9 إلى 10 دقائق قبل الصلاة
                        bot.send_message(user["_id"], f"🕌 بقي 10 دقائق على صلاة {prayer}.\nاستعد للصلاة 🌙")
                except:
                    continue

        time.sleep(60)

# ========================================================
# 📜 تذكير يوم الجمعة
# ========================================================
def send_friday_reminder():
    while True:
        now_utc = datetime.datetime.utcnow()
        weekday = now_utc.weekday()

        if weekday == 4 and now_utc.hour == 9 and now_utc.minute == 0:
            msg = (
                "🕌 *جمعة مباركة!*\n\n"
                "📖 لا تنسَ قراءة *سورة الكهف*\n"
                "🕋 وأكثِر من الصلاة على النبي ﷺ:\n"
                "_اللهم صل وسلم على نبينا محمد عدد ما ذكره الذاكرون وغفل عن ذكره الغافلون_ ❤️"
            )
            users = [u["_id"] for u in get_all_users() if user_notifications_enabled(u["_id"])]
            broadcast_message(users, msg)

        time.sleep(60)

# ========================================================
# ✅ بدء كل المهام في خيوط منفصلة
# ========================================================
def start_reminders():
    threading.Thread(target=send_morning_evening_adhkar).start()
    threading.Thread(target=notify_prayer).start()
    threading.Thread(target=send_friday_reminder).start()