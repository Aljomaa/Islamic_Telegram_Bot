from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID

def show_main_menu(bot, message):
    # التعامل مع call.message أو message مباشرة
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
    msg_id = message.message_id if hasattr(message, 'message_id') else message.message.message_id

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🕌 أوقات الصلاة", callback_data="menu:prayer"),
        InlineKeyboardButton("📖 القرآن الكريم", callback_data="menu:quran"),
        InlineKeyboardButton("📿 الأذكار", callback_data="menu:athkar"),
        InlineKeyboardButton("📜 الحديث", callback_data="menu:hadith"),
        InlineKeyboardButton("📿 المسبحة", callback_data="menu:misbaha"),
        InlineKeyboardButton("📘 ختمتي", callback_data="menu:khatmah"),
        InlineKeyboardButton("⭐ المفضلة", callback_data="menu:fav"),
        InlineKeyboardButton("📝 الشكاوى", callback_data="menu:complain"),
        InlineKeyboardButton("⚙️ الإعدادات", callback_data="menu:settings")
    )

    if chat_id == OWNER_ID:
        markup.add(InlineKeyboardButton("🧑‍💼 المشرف", callback_data="menu:admin"))

    bot.edit_message_text(
        "🌙 مرحبًا بك في البوت الإسلامي!\nاختر أحد الخيارات:",
        chat_id,
        msg_id,
        reply_markup=markup
    )
