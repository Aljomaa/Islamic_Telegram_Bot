from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from utils.db import set_user_location

def register(bot):
    @bot.message_handler(commands=['enable_notifications'])
    def ask_location(msg):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn = KeyboardButton("📍 شارك موقعي", request_location=True)
        markup.add(btn)
        bot.send_message(msg.chat.id, "📍 من فضلك شارك موقعك لتفعيل التنبيهات حسب توقيتك المحلي:", reply_markup=markup)

    @bot.message_handler(content_types=['location'])
    def save_location(msg):
        if not msg.location:
            bot.send_message(msg.chat.id, "❌ لم يتم استلام موقعك. يرجى المحاولة مجددًا.")
            return

        lat = msg.location.latitude
        lon = msg.location.longitude

        # حفظ الموقع مع وضع 'auto' كوقت مبدئي
        set_user_location(msg.from_user.id, lat, lon, timezone="auto")

        bot.send_message(msg.chat.id, "✅ تم حفظ موقعك وتفعيل التنبيهات اليومية بإذن الله.")
