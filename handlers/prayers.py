import requests
import os
from dotenv import load_dotenv
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from utils.db import set_user_location, get_user_location

load_dotenv()
TIMEZONE_API_KEY = os.getenv("TIMEZONE_API_KEY")
TIMEZONE_API_URL = "http://api.timezonedb.com/v2.1/get-time-zone"

# ✅ تسجيل أوامر الصلاة
def register(bot):
    @bot.message_handler(commands=['prayer'])
    def handle_prayer_command(msg):
        show_prayer_times(bot, msg)

    @bot.message_handler(content_types=['location'])
    def handle_location(msg):
        lat = msg.location.latitude
        lon = msg.location.longitude

        # ✅ جلب المنطقة الزمنية تلقائيًا
        tz_name = "auto"
        try:
            params = {
                "key": TIMEZONE_API_KEY,
                "format": "json",
                "by": "position",
                "lat": lat,
                "lng": lon
            }
            res = requests.get(TIMEZONE_API_URL, params=params, timeout=10)
            data = res.json()
            tz_name = data.get("zoneName", "auto")
        except Exception as e:
            print(f"[ERROR] جلب التوقيت المحلي: {e}")

        set_user_location(msg.from_user.id, lat, lon, tz_name)
        show_prayer_times(bot, msg)

    # ✅ زر تحديث الموقع من داخل البوت
    @bot.callback_query_handler(func=lambda call: call.data == "update_location")
    def ask_new_location(call):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("📍 إرسال موقعي", request_location=True))
        bot.send_message(call.message.chat.id, "📍 الرجاء إرسال موقعك الجديد.", reply_markup=markup)

# ✅ عرض أوقات الصلاة أو طلب الموقع
def show_prayer_times(bot, message):
    lat, lon = get_user_location(message.chat.id)

    if not lat or not lon:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("📍 إرسال موقعي", request_location=True))
        return bot.send_message(
            message.chat.id,
            "📍 الرجاء إرسال موقعك الجغرافي للحصول على أوقات الصلاة بدقة.",
            reply_markup=markup
        )

    try:
        res = requests.get(
            f"http://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=4"
        )
        data = res.json()

        if data["code"] != 200:
            raise Exception("❌ فشل في جلب أوقات الصلاة من API.")

        times = data["data"]["timings"]
        date = data["data"]["date"]["readable"]

        text = (
            f"🕌 <b>أوقات الصلاة لليوم ({date})</b>\n\n"
            f"📿 الفجر: <b>{times['Fajr']}</b>\n"
            f"🌅 الشروق: <b>{times['Sunrise']}</b>\n"
            f"☀️ الظهر: <b>{times['Dhuhr']}</b>\n"
            f"🌇 العصر: <b>{times['Asr']}</b>\n"
            f"🌆 المغرب: <b>{times['Maghrib']}</b>\n"
            f"🌃 العشاء: <b>{times['Isha']}</b>\n"
        )

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📍 تحديث موقعي", callback_data="update_location"),
            InlineKeyboardButton("⬅️ العودة إلى القائمة الرئيسية", callback_data="back_to_main")
        )

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"[ERROR] Prayer API: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ أثناء جلب أوقات الصلاة.")
