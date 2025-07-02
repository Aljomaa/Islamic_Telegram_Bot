from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import get_user_reminder_settings, update_reminder_setting

def register(bot):
    @bot.message_handler(commands=['settings'])
    def show_settings_menu_command(msg):
        show_settings_menu(bot, msg.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("settings:toggle:"))
    def toggle_setting(call):
        _, _, setting_key = call.data.split(":")
        current_settings = get_user_reminder_settings(call.from_user.id)
        current_value = current_settings.get(setting_key, True)
        update_reminder_setting(call.from_user.id, setting_key, not current_value)
        bot.answer_callback_query(call.id, f"{'✅ تم التفعيل' if not current_value else '❌ تم الإلغاء'}")
        show_settings_menu(bot, call.from_user.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "settings:back")
    def back_to_main_menu(call):
        from main import welcome
        welcome(call)

def show_settings_menu(bot, chat_id, message_id=None):
    settings = get_user_reminder_settings(chat_id)

    def get_label(name, key, emoji):
        status = "✅ مفعّل" if settings.get(key, True) else "❌ غير مفعّل"
        return f"{emoji} {name}: {status}"

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(get_label("أذكار الصباح", "morning_adhkar", "🌅"), callback_data="settings:toggle:morning_adhkar"),
        InlineKeyboardButton(get_label("أذكار المساء", "evening_adhkar", "🌇"), callback_data="settings:toggle:evening_adhkar"),
        InlineKeyboardButton(get_label("تذكير الجمعة", "jumuah", "📿"), callback_data="settings:toggle:jumuah"),
        InlineKeyboardButton(get_label("تذكيرات الصلاة", "prayer", "🕌"), callback_data="settings:toggle:prayer")
    )
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="settings:back"))

    text = "⚙️ إعدادات الإشعارات:\n\nقم بالنقر على أي خيار لتفعيله أو إيقافه:"
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)
