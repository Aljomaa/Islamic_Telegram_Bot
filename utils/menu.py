from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID

def show_main_menu(bot, message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🕌 أوقات الصلاة", callback_data="menu:prayer"),
        InlineKeyboardButton("📖 القرآن الكريم", callback_data="menu:quran"),
        InlineKeyboardButton("📿 الأذكار", callback_data="menu:athkar"),
        InlineKeyboardButton("📜 الحديث", callback_data="menu:hadith"),
        InlineKeyboardButton("⭐ المفضلة", callback_data="menu:fav"),
        InlineKeyboardButton("📝 الشكاوى", callback_data="menu:complain"),
        InlineKeyboardButton("⚙️ الإعدادات", callback_data="menu:settings")
    )
    if message.chat.id == ADMIN_ID:
        markup.add(InlineKeyboardButton("🧑‍💼 المشرف", callback_data="menu:admin"))

    bot.edit_message_text("🌙 مرحبًا بك في البوت الإسلامي!\nاختر أحد الخيارات:", message.chat.id, message.message_id, reply_markup=markup)
