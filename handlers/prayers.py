import requests
from telebot import types

def register(bot):
    @bot.message_handler(commands=['prayer'])
    def ask_location(msg):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("📍 أرسل موقعي", request_location=True))
        bot.send_message(msg.chat.id, "📍 أرسل موقعك للحصول على أوقات الصلاة بدقة", reply_markup=kb)

    @bot.message_handler(content_types=['location'])
    def send_times(msg):
        lat, lon = msg.location.latitude, msg.location.longitude
        url = f"https://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=4"
        res = requests.get(url).json()
        if res["code"] == 200:
            t = res["data"]["timings"]
            out = f"""🕌 أوقات الصلاة:
الفجر: {t['Fajr']}
الظهر: {t['Dhuhr']}
العصر: {t['Asr']}
المغرب: {t['Maghrib']}
العشاء: {t['Isha']}"""
            bot.send_message(msg.chat.id, out, reply_markup=types.ReplyKeyboardRemove())
        else:
            bot.send_message(msg.chat.id, "❌ تعذر جلب أوقات الصلاة.")