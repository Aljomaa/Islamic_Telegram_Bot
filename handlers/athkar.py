import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
import logging

# تسجيل الأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ATHKAR_API_URL = "https://raw.githubusercontent.com/fawazahmed0/athkar-api/main/athkar.json"

# 📿 القائمة الرئيسية للأذكار
def show_athkar_menu(bot, message):
    try:
        response = requests.get(ATHKAR_API_URL, timeout=10)
        data = response.json()
        categories = list(data.keys())

        markup = InlineKeyboardMarkup(row_width=2)
        for cat in categories:
            markup.add(InlineKeyboardButton(f"📿 {cat}", callback_data=f"athkar:{cat}"))

        bot.send_message(message.chat.id, "📿 اختر نوع الذكر الذي تريده:", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error loading athkar: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ أثناء تحميل الأذكار. حاول لاحقاً.")

# ✅ تسجيل المعالجات
def register(bot):
    @bot.message_handler(commands=['athkar', 'أذكار'])
    def handle_athkar_cmd(msg):
        show_athkar_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("athkar:"))
    def show_athkar_list(call):
        try:
            category = call.data.split(":", 1)[1]
            response = requests.get(ATHKAR_API_URL, timeout=10)
            data = response.json()

            azkar = data.get(category, [])

            if not azkar:
                bot.answer_callback_query(call.id, "❌ لا يوجد أذكار في هذا القسم.")
                return

            for item in azkar[:10]:  # عرض أول 10 أذكار فقط
                text = f"📿 {item.strip()}"
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_athkar:{item[:40]}")
                )
                markup.row(
                    InlineKeyboardButton("🏠 رجوع", callback_data="athkar_menu")
                )
                bot.send_message(call.message.chat.id, text, reply_markup=markup)

            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"Error showing athkar list: {e}")
            bot.send_message(call.message.chat.id, "❌ حدث خطأ أثناء عرض الأذكار.")

    @bot.callback_query_handler(func=lambda call: call.data == "athkar_menu")
    def return_to_menu(call):
        show_athkar_menu(bot, call.message)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_athkar:"))
    def add_to_favorites(call):
        try:
            snippet = call.data.split(":", 1)[1]
            content = f"ذكر:\n{snippet}..."
            add_to_fav(call.from_user.id, "athkar", content)
            bot.answer_callback_query(call.id, "✅ تم حفظ الذكر في المفضلة.")
        except Exception as e:
            logger.error(f"Error adding athkar to fav: {e}")
            bot.answer_callback_query(call.id, "❌ تعذر حفظ الذكر في المفضلة.")
