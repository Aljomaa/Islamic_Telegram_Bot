import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav

def register(bot):
    @bot.message_handler(commands=['athkar'])
    def send_zekr(msg):
        try:
            res = requests.get("https://azkar-api.vercel.app/api/random", timeout=10)
            res.raise_for_status()
        except Exception:
            bot.send_message(msg.chat.id, "❌ تعذر جلب الذكر حالياً، حاول لاحقاً.")
            return

        data = res.json()
        category = data.get('category', 'ذكر')
        content = data.get('content', 'لا يوجد ذكر حالياً.')
        count = data.get('count', '')

        text = f"📿 *{category}*\n\n{content}\n\n🔁 *التكرار:* {count}"

        # لأسباب تتعلق بحجم callback_data نرسل معرف قصير وليس النص الكامل
        # يمكن نرسل أول 20 حرف فقط للتمييز أو رقم فريد لو متوفر
        snippet = content[:30].replace(':', '').replace('|', '').replace(';', '')  # تنظيف بعض الأحرف

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⭐ إضافة إلى المفضلة", callback_data=f"fav_zekr:{snippet}"))
        bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_zekr:"))
    def add_zekr_fav(call):
        content = call.data.split(":", 1)[1]
        add_to_fav(call.from_user.id, "zekr", content + "...")
        bot.answer_callback_query(call.id, "✅ تم حفظ الذكر في المفضلة.")
