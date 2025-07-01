import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
import logging

ATHKAR_API_URL = "https://cdn.jsdelivr.net/gh/fawazahmed0/athkar-api@1/athkar.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

athkar_data = {}
athkar_categories = []

def register(bot):
    # تحميل الأذكار مرة واحدة عند بدء البوت
    global athkar_data, athkar_categories
    try:
        response = requests.get(ATHKAR_API_URL, timeout=10)
        athkar_data = response.json()
        athkar_categories = list(athkar_data.keys())
    except Exception as e:
        logger.error(f"❌ فشل تحميل الأذكار عند التشغيل: {e}")

    @bot.message_handler(commands=['athkar', 'أذكار'])
    def show_athkar_menu(msg):
        if not athkar_categories:
            bot.send_message(msg.chat.id, "❌ حدث خطأ أثناء تحميل الأذكار.")
            return

        markup = InlineKeyboardMarkup(row_width=2)
        for cat in athkar_categories:
            markup.add(InlineKeyboardButton(f"📿 {cat}", callback_data=f"athkar_cat:{cat}"))
        bot.send_message(msg.chat.id, "📿 اختر نوع الذكر الذي تريده:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("athkar_cat:"))
    def show_athkar_list(call):
        category = call.data.split(":", 1)[1]
        send_athkar_by_index(bot, call.message.chat.id, category, 0, call.message.message_id, edit=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("athkar_nav:"))
    def navigate_athkar(call):
        _, category, index = call.data.split(":")
        send_athkar_by_index(bot, call.message.chat.id, category, int(index), call.message.message_id, edit=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_athkar:"))
    def add_to_favorites(call):
        try:
            _, category, index = call.data.split(":")
            index = int(index)
            content = athkar_data[category][index]
            add_to_fav(call.from_user.id, "athkar", content)
            bot.answer_callback_query(call.id, "✅ تم حفظ الذكر في المفضلة.")
        except Exception as e:
            logger.error(f"Error adding to fav: {e}")
            bot.answer_callback_query(call.id, "❌ تعذر حفظ الذكر.")

    @bot.callback_query_handler(func=lambda call: call.data == "athkar_main")
    def return_to_main_menu(call):
        bot.send_message(call.message.chat.id, "🌙 مرحبًا بك في البوت الإسلامي!\nاختر أحد الخيارات:\n/start")

def send_athkar_by_index(bot, chat_id, category, index, message_id=None, edit=False):
    try:
        azkar = athkar_data.get(category, [])
        if not azkar or index < 0 or index >= len(azkar):
            bot.send_message(chat_id, "❌ لا يوجد ذكر في هذا الموضع.")
            return

        text = f"📿 {azkar[index]}"
        markup = InlineKeyboardMarkup()

        # أزرار التنقل
        nav_buttons = []
        if index > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"athkar_nav:{category}:{index - 1}"))
        if index < len(azkar) - 1:
            nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"athkar_nav:{category}:{index + 1}"))
        if nav_buttons:
            markup.row(*nav_buttons)

        # أزرار إضافية
        markup.row(
            InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_athkar:{category}:{index}"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="athkar_main")
        )

        if edit and message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    except Exception as e:
        logger.error(f"Error sending athkar: {e}")
        bot.send_message(chat_id, "❌ حدث خطأ أثناء عرض الذكر.")
