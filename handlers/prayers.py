import os
import requests
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import set_user_location, get_user_location
from dotenv import load_dotenv

load_dotenv()
TIMEZONE_API_KEY = os.getenv("TIMEZONE_API_KEY")

def register(bot):
    @bot.message_handler(commands=['prayer'])
    def ask_location(msg):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn = KeyboardButton("📍 إرسال موقعي", request_location=True)
        markup.add(btn)
        bot.send_message(
            msg.chat.id,
            "📍 الرجاء إرسال موقعك للحصول على أوقات الصلاة بدقة.",
            reply_markup=markup
        )

    @bot.message_handler(content_types=['location'])
    def handle_location(msg):
        lat = msg.location.latitude
        lon = msg.location.longitude
        timezone = get_timezone_from_api(lat, lon)
        set_user_location(msg.from_user.id, lat, lon, timezone)
        show_prayer_times(bot, msg)

# ✅ إحضار المنطقة الزمنية من API
def get_timezone_from_api(lat, lon):
    try:
        res = requests.get(
            f"https://api.timezonedb.com/v2.1/get-time-zone?key={TIMEZONE_API_KEY}&format=json&by=position&lat={lat}&lng={lon}&fields=zoneName",
            timeout=10
        )
        data = res.json()
        return data.get("zoneName", "auto")
    except Exception as e:
        print(f"[ERROR] Timezone API: {e}")
        return "auto"

# ✅ عرض أوقات الصلاة
def show_prayer_times(bot, message):
    lat, lon = get_user_location(message.chat.id)
    if not lat or not lon:
        bot.send_message(
            message.chat.id,
            "❗ الرجاء استخدام الأمر /prayer ومشاركة موقعك أولًا."
        )
        return

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
        markup.add(InlineKeyboardButton("⬅️ العودة إلى القائمة الرئيسية", callback_data="back_to_main"))

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"[ERROR] Prayer API: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ أثناء جلب أوقات الصلاة.")
