from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import get_misbahah_count, update_misbahah_count, reset_misbahah
from utils.menu import show_main_menu

def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "menu:misbahah")
    def open_misbahah(call):
        show_misbahah_menu(bot, call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("misbahah:"))
    def handle_misbahah_actions(call):
        user_id = call.from_user.id
        action = call.data.split(":")[1]

        count = get_misbahah_count(user_id)

        if action == "add":
            count += 1
            update_misbahah_count(user_id, count)
            update_misbahah_message(bot, call.message, count)

        elif action == "reset":
            count = 0
            reset_misbahah(user_id)
            update_misbahah_message(bot, call.message, count)

        elif action == "back":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_main_menu(bot, call.message)

def show_misbahah_menu(bot, chat_id, message_id=None):
    count = get_misbahah_count(chat_id)
    text = f"📿 *المسبحة الإلكترونية*\n\n🔢 *عدد التسبيحات:* `{count}`"

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ سبح", callback_data="misbahah:add"),
        InlineKeyboardButton("♻️ تصفير", callback_data="misbahah:reset"),
    )
    markup.add(InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="misbahah:back"))

    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def update_misbahah_message(bot, message, count):
    text = f"📿 *المسبحة الإلكترونية*\n\n🔢 *عدد التسبيحات:* `{count}`"

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ سبح", callback_data="misbahah:add"),
        InlineKeyboardButton("♻️ تصفير", callback_data="misbahah:reset"),
    )
    markup.add(InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="misbahah:back"))

    bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup, parse_mode="Markdown")
