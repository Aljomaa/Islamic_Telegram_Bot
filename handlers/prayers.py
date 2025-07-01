import requests
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from utils.db import set_user_location, get_user_location
from datetime import datetime
import pytz

def register(bot):
    @bot.message_handler(commands=['prayer'])
    def ask_location(msg):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn = KeyboardButton("📍 إرسال موقعي", request_location=True)
        markup.add(btn)
        bot.send_message(msg.chat.id, "📍 الرجاء إرسال موقعك للحصول على أوقات الصلاة بدقة.", reply_markup=markup)

    @bot.message_handler(content_types=['location'])
    def handle_location(msg):
        lat = msg.location.latitude
        lon = msg.location.longitude
        set_user_location(msg.from_user.id, lat, lon)

        try:
            res = requests.get(f"http://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=4")
            data = res.json()

            if data["code"] != 200:
                raise Exception("خطأ في API")

            times = data["data"]["timings"]
            date = data["data"]["date"]["readable"]

            text = f"🕌 أوقات الصلاة لليوم ({date}):\n\n"
            text += f"الفجر: {times['Fajr']}\n"
            text += f"الشروق: {times['Sunrise']}\n"
            text += f"الظهر: {times['Dhuhr']}\n"
            text += f"العصر: {times['Asr']}\n"
            text += f"المغرب: {times['Maghrib']}\n"
            text += f"العشاء: {times['Isha']}\n"

            bot.send_message(msg.chat.id, text)

        except Exception as e:
            print(f"[ERROR] Prayer API: {e}")
            bot.send_message(msg.chat.id, "❌ حدث خطأ أثناء جلب أوقات الصلاة.")