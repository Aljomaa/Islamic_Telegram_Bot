import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ATHKAR_CATEGORIES = {
    "الصباح": "https://ahegazy.github.io/muslimKit/json/azkar_sabah.json",
    "المساء": "https://ahegazy.github.io/muslimKit/json/azkar_massa.json",
    "بعد الصلاة": "https://ahegazy.github.io/muslimKit/json/PostPrayer_azkar.json"
}

athkar_cache = {}

def show_athkar_menu(bot, message):
    markup = InlineKeyboardMarkup(row_width=2)
    for cat in ATHKAR_CATEGORIES:
        markup.add(InlineKeyboardButton(f"📿 {cat}", callback_data=f"athkar_cat:{cat}"))
    bot.send_message(message.chat.id, "📿 اختر نوع الأذكار:", reply_markup=markup)

def register(bot):
    @bot.message_handler(commands=['athkar', 'أذكار'])
    def handle_menu_command(msg):
        show_athkar_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("athkar_cat:"))
    def handle_category(call):
        category = call.data.split(":")[1]
        try:
            if category not in athkar_cache:
                url = ATHKAR_CATEGORIES[category]
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                data = res.json()
                athkar_list = data.get("content", [])
                athkar_cache[category] = athkar_list
            else:
                athkar_list = athkar_cache[category]

            if not athkar_list:
                bot.send_message(call.message.chat.id, "❌ لا توجد أذكار متاحة.")
                return

            send_athkar_by_index(bot, call.message.chat.id, category, 0, call.message.message_id, edit=True)
        except Exception as e:
            logger.error(f"[ERROR] تحميل الأذكار: {e}")
            bot.send_message(call.message.chat.id, "❌ فشل تحميل الأذكار.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("athkar_nav:"))
    def navigate_athkar(call):
        _, category, index = call.data.split(":")
        index = int(index)
        send_athkar_by_index(bot, call.message.chat.id, category, index, call.message.message_id, edit=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_athkar:"))
    def add_to_favorites(call):
        try:
            _, category, index = call.data.split(":")
            index = int(index)
            content = athkar_cache[category][index].get("zekr", "")
            add_to_fav(call.from_user.id, "athkar", content)
            bot.answer_callback_query(call.id, "✅ تم حفظ الذكر في المفضلة.")
        except Exception as e:
            logger.error(f"[ERROR] حفظ المفضلة: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")

    @bot.callback_query_handler(func=lambda call: call.data == "athkar_main")
    def return_to_main(call):
        from main import welcome  # استدعاء القائمة الرئيسية
        welcome(call.message)

def send_athkar_by_index(bot, chat_id, category, index, message_id=None, edit=False):
    try:
        athkar_list = athkar_cache.get(category, [])
        if not athkar_list or not (0 <= index < len(athkar_list)):
            bot.send_message(chat_id, "❌ لا يوجد ذكر في هذا الموضع.")
            return

        item = athkar_list[index]
        text = item.get("zekr", "").strip()
        count = item.get("repeat", "")
        reference = item.get("reference", "") or item.get("bless", "")

        final_text = f"📿 *{category}*\n\n{text}"
        if count:
            final_text += f"\n\n📌 التكرار: {count}"
        if reference:
            final_text += f"\n📖 المرجع: {reference}"

        markup = InlineKeyboardMarkup()

        nav_buttons = []
        if index > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"athkar_nav:{category}:{index - 1}"))
        if index < len(athkar_list) - 1:
            nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"athkar_nav:{category}:{index + 1}"))
        if nav_buttons:
            markup.row(*nav_buttons)

        markup.row(
            InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_athkar:{category}:{index}"),
            InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="athkar_main")
        )

        if edit and message_id:
            bot.edit_message_text(final_text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, final_text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"[ERROR] عرض الذكر: {e}")
        bot.send_message(chat_id, "❌ تعذر عرض الذكر.")
