from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import user_col
from math import ceil

ITEMS_PER_PAGE = 3

# ✅ هذه متاحة للاستدعاء من main.py
def show_fav_main_menu(bot, chat_id, message_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📖 آيات", callback_data="fav_section:quran"),
        InlineKeyboardButton("📜 أحاديث", callback_data="fav_section:hadith"),
        InlineKeyboardButton("📿 أذكار", callback_data="fav_section:athkar")
    )
    markup.add(InlineKeyboardButton("🏠 الرجوع للرئيسية", callback_data="main_menu"))
    bot.edit_message_text("⭐ اختر القسم الذي تريد عرضه من المفضلة:", chat_id, message_id, reply_markup=markup)

# ✅ تسجيل الأحداث
def register(bot):
    section_to_type = {
        "quran": "ayah",
        "hadith": "hadith",
        "athkar": "athkar"
    }

    @bot.callback_query_handler(func=lambda call: call.data == "menu:fav")
    def open_favorites_main(call):
        show_fav_main_menu(bot, call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_section:"))
    def show_fav_section(call):
        section = call.data.split(":")[1]
        show_fav_page(bot, call.message.chat.id, call.message.message_id, section, 0)

    def show_fav_page(bot, chat_id, message_id, section, page):
        user = user_col.find_one({"_id": chat_id})
        if not user or "favorites" not in user:
            return bot.edit_message_text("⭐ لا يوجد عناصر في المفضلة.", chat_id, message_id)

        actual_type = section_to_type.get(section)
        favs = [f for f in user["favorites"] if f.get("type") == actual_type and isinstance(f.get("content"), str)]

        if not favs:
            return bot.edit_message_text("⭐ لا يوجد عناصر في هذا القسم من المفضلة.", chat_id, message_id)

        total_pages = ceil(len(favs) / ITEMS_PER_PAGE)
        page = max(0, min(page, total_pages - 1))
        start = page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        current_favs = favs[start:end]

        title_map = {
            "quran": "📖 آيات محفوظة",
            "hadith": "📜 أحاديث محفوظة",
            "athkar": "📿 أذكار محفوظة"
        }
        text = f"{title_map.get(section, '')} (صفحة {page + 1} من {total_pages})\n\n"
        for i, fav in enumerate(current_favs, start=start):
            text += f"*{i + 1}.* {fav['content'][:300]}\n\n"

        markup = InlineKeyboardMarkup(row_width=3)
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⏮️ السابق", callback_data=f"fav_page:{section}:{page - 1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("⏭️ التالي", callback_data=f"fav_page:{section}:{page + 1}"))
        if nav:
            markup.row(*nav)

        markup.add(InlineKeyboardButton("🗑️ حذف عنصر", callback_data=f"fav_delete_menu:{section}:{page}"))
        markup.add(
            InlineKeyboardButton("🔙 الرجوع للأقسام", callback_data="menu:fav"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        )

        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_page:"))
    def change_page(call):
        _, section, page = call.data.split(":")
        show_fav_page(bot, call.message.chat.id, call.message.message_id, section, int(page))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_delete_menu:"))
    def delete_menu(call):
        _, section, page = call.data.split(":")
        page = int(page)
        user = user_col.find_one({"_id": call.message.chat.id})
        if not user or "favorites" not in user:
            return
        actual_type = section_to_type.get(section)
        favs = [f for f in user["favorites"] if f.get("type") == actual_type and isinstance(f.get("content"), str)]
        start = page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        current_favs = favs[start:end]

        markup = InlineKeyboardMarkup(row_width=1)
        for i, fav in enumerate(current_favs, start=start):
            label = fav["content"][:40].replace("\n", " ")
            markup.add(InlineKeyboardButton(f"❌ حذف: {label}", callback_data=f"fav_delete:{section}:{i}:{page}"))

        markup.add(InlineKeyboardButton("⬅️ رجوع", callback_data=f"fav_page:{section}:{page}"))
        bot.edit_message_text("🗑️ اختر العنصر الذي تريد حذفه:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_delete:"))
    def delete_favorite(call):
        _, section, index, page = call.data.split(":")
        index = int(index)
        user_col.update_one({"_id": call.message.chat.id}, {"$unset": {f"favorites.{index}": 1}})
        user_col.update_one({"_id": call.message.chat.id}, {"$pull": {"favorites": None}})
        bot.answer_callback_query(call.id, "✅ تم الحذف من المفضلة.")
        show_fav_page(bot, call.message.chat.id, call.message.message_id, section, int(page))
