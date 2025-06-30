import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav

def register(bot):
    @bot.message_handler(commands=['athkar'])
    def send_zekr(msg):
        res = requests.get("https://azkar-api.vercel.app/api/random")
        if res.status_code != 200:
            bot.send_message(msg.chat.id, "❌ تعذر جلب الذكر حالياً.")
            return

        data = res.json()
        text = f"📿 *{data['category']}*\n\n{data['content']}\n\n🔁 *التكرار:* {data['count']}"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⭐ إضافة إلى المفضلة", callback_data=f"fav_zekr:{data['content'][:50]}"))
        bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_zekr:"))
    def add_zekr_fav(call):
        content = call.data.split(":", 1)[1]
        add_to_fav(call.from_user.id, "zekr", content + "...")
        bot.answer_callback_query(call.id, "✅ تم حفظ الذكر في المفضلة.")