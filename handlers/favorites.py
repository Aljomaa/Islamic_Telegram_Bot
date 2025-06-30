from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import user_col
from math import ceil

ITEMS_PER_PAGE = 5

def register(bot):
    @bot.message_handler(commands=['fav'])
    def show_favorites(msg):
        show_fav_page(bot, msg.chat.id, 0)

def show_fav_page(bot, chat_id, page):
    user = user_col.find_one({"_id": chat_id})
    if not user or "favorites" not in user or len(user["favorites"]) == 0:
        bot.send_message(chat_id, "⭐ لم تقم بإضافة أي شيء إلى المفضلة بعد.")
        return

    favs = user["favorites"]
    total_pages = ceil(len(favs) / ITEMS_PER_PAGE)

    page = max(0, min(page, total_pages - 1))  # تأكد أن الصفحة ضمن الحدود
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_favs = favs[start:end]

    text = f"⭐ *مفضلتك* (صفحة {page + 1} من {total_pages})\n\n"
    for i, fav in enumerate(current_favs, start=1 + start):
        icon = "📖" if fav['type'] == 'ayah' else "📜" if fav['type'] == 'hadith' else "📿"
        text += f"{icon} *{i}.* {fav['content'][:80]}...\n"

    markup = InlineKeyboardMarkup(row_width=3)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⏮️ السابق", callback_data=f"fav_page:{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("⏭️ التالي", callback_data=f"fav_page:{page+1}"))

    if nav_buttons:
        markup.add(*nav_buttons)
    markup.add(InlineKeyboardButton("🗑️ حذف عنصر", callback_data=f"fav_delete_menu:{page}"))

    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("fav_page:"))
def change_fav_page(call):
    new_page = int(call.data.split(":")[1])
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_fav_page(bot, call.message.chat.id, new_page)

@bot.callback_query_handler(func=lambda call: call.data.startswith("fav_delete_menu:"))
def delete_menu(call):
    page = int(call.data.split(":")[1])
    user = user_col.find_one({"_id": call.message.chat.id})
    if not user or "favorites" not in user:
        return

    favs = user["favorites"]
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_favs = favs[start:end]

    markup = InlineKeyboardMarkup(row_width=1)
    for i, fav in enumerate(current_favs, start=start):
        label = f"{fav['content'][:40]}..."
        markup.add(InlineKeyboardButton(f"❌ حذف: {label}", callback_data=f"fav_delete:{i}:{page}"))

    markup.add(InlineKeyboardButton("⬅️ رجوع", callback_data=f"fav_page:{page}"))
    bot.edit_message_text("🗑️ اختر العنصر الذي تريد حذفه من المفضلة:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("fav_delete:"))
def delete_favorite(call):
    parts = call.data.split(":")
    index = int(parts[1])
    page = int(parts[2])

    user_col.update_one({"_id": call.message.chat.id}, {"$unset": {f"favorites.{index}": 1}})
    user_col.update_one({"_id": call.message.chat.id}, {"$pull": {"favorites": None}})
    
    bot.answer_callback_query(call.id, "✅ تم حذف العنصر من المفضلة.")
    show_fav_page(bot, call.message.chat.id, page)