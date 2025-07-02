from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import get_user_favs, user_col
from math import ceil

def register(bot):
    @bot.message_handler(commands=['fav'])
    def fav_command(msg):
        show_fav_categories(bot, msg.chat.id, msg.message_id if msg.message_id else None)

    def show_fav_categories(bot, chat_id, message_id=None):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📖 الآيات", callback_data="fav:ayah:0"),
            InlineKeyboardButton("📜 الأحاديث", callback_data="fav:hadith:0"),
            InlineKeyboardButton("📿 الأذكار", callback_data="fav:dhikr:0")
        )
        markup.add(InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="back_to_main"))

        text = "⭐ اختر نوع المفضلة التي تريد عرضها:"
        if message_id:
            try:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            except:
                bot.send_message(chat_id, text, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav:"))
    def handle_fav_section(call):
        _, type_, index = call.data.split(":")
        index = int(index)
        favs = [f for f in get_user_favs(call.from_user.id) if f["type"] == type_]
        if not favs:
            bot.answer_callback_query(call.id, "❌ لا يوجد عناصر في هذا القسم.")
            return show_fav_categories(bot, call.message.chat.id, call.message.message_id)

        index = max(0, min(index, len(favs) - 1))
        fav = favs[index]

        text = f"⭐ <b>العنصر {index + 1} من {len(favs)}</b>\n\n{fav['content']}"
        markup = InlineKeyboardMarkup()

        nav_buttons = []
        if index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"fav:{type_}:{index - 1}"))
        if index < len(favs) - 1:
            nav_buttons.append(InlineKeyboardButton("➡️ التالي", callback_data=f"fav:{type_}:{index + 1}"))
        if nav_buttons:
            markup.row(*nav_buttons)

        markup.add(
            InlineKeyboardButton("🗑️ حذف", callback_data=f"favdel:{type_}:{index}"),
            InlineKeyboardButton("🔙 الرجوع إلى الأقسام", callback_data="fav:back"),
            InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="back_to_main")
        )

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

    @bot.callback_query_handler(func=lambda call: call.data == "fav:back")
    def back_to_categories(call):
        show_fav_categories(bot, call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("favdel:"))
    def delete_favorite(call):
        _, type_, index = call.data.split(":")
        index = int(index)
        user = user_col.find_one({"_id": call.from_user.id})
        if not user or "favorites" not in user:
            return

        # احسب موقع العنصر داخل المصفوفة الأصلية
        full_list = user["favorites"]
        filtered = [f for f in full_list if f["type"] == type_]

        if index >= len(filtered):
            bot.answer_callback_query(call.id, "❌ العنصر غير موجود.")
            return

        target_item = filtered[index]
        try:
            real_index = full_list.index(target_item)
        except ValueError:
            bot.answer_callback_query(call.id, "❌ خطأ أثناء الحذف.")
            return

        # احذف العنصر الحقيقي
        user_col.update_one({"_id": call.from_user.id}, {"$unset": {f"favorites.{real_index}": 1}})
        user_col.update_one({"_id": call.from_user.id}, {"$pull": {"favorites": None}})

        bot.answer_callback_query(call.id, "✅ تم حذف العنصر من المفضلة.")
        show_fav_categories(bot, call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
    def back_to_main(call):
        from main import show_main_menu
        show_main_menu(bot, call.message)
