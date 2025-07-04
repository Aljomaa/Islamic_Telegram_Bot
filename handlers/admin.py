from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID
from utils.db import (
    get_bot_stats,
    get_all_user_ids,
    is_admin,
    add_admin,
    remove_admin,
    get_admins,
    get_complaints,
    user_col
)
import os
import sys

def show_admin_menu(bot, chat_id, message_id=None):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats"),
        InlineKeyboardButton("📢 رسالة جماعية", callback_data="admin_broadcast"),
        InlineKeyboardButton("➕ إضافة مشرف", callback_data="admin_add"),
        InlineKeyboardButton("➖ إزالة مشرف", callback_data="admin_remove"),
        InlineKeyboardButton("👥 قائمة المشرفين", callback_data="admin_list")
    )
    markup.add(InlineKeyboardButton("🏠 العودة إلى الرئيسية", callback_data="main_menu"))

    text = "🧑‍💼 لوحة تحكم المشرف:\nاختر ما تريد من الأدوات التالية:"
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

def register(bot):
    @bot.message_handler(commands=["admin"])
    def admin_panel(msg: Message):
        if is_admin(msg.from_user.id):
            show_admin_menu(bot, msg.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "menu:admin")
    def open_admin_menu(call):
        if is_admin(call.from_user.id):
            show_admin_menu(bot, call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
    def show_stats(call):
        if not is_admin(call.from_user.id): return
        stats = get_bot_stats()
        msg = (
            f"📊 إحصائيات البوت:\n\n"
            f"👤 عدد المستخدمين: {stats['total_users']}\n"
            f"⭐ عدد العناصر في المفضلة: {stats['total_favorites']}\n"
            f"📬 عدد الشكاوى/الاقتراحات: {stats['total_complaints']}"
        )
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 العودة", callback_data="menu:admin"))
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "admin_list")
    def show_admin_list(call):
        if not is_admin(call.from_user.id): return
        admins = get_admins()
        if not admins:
            msg = "❌ لا يوجد مشرفون حالياً."
        else:
            msg = "👥 قائمة المشرفين:\n\n"
            for a in admins:
                uid = a.get("_id")
                uname = a.get("username")
                line = f"• @{uname}" if uname else f"• `{uid}`"
                msg += line + "\n"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 العودة", callback_data="menu:admin"))
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_add")
    def ask_for_admin_input(call):
        if not is_admin(call.from_user.id): return
        msg = bot.send_message(call.message.chat.id, "🆔 أرسل الآن رقم ID أو @username للمستخدم الذي تريد إضافته كمشرف:")
        bot.register_next_step_handler(msg, process_admin_add)

    def process_admin_add(msg):
        text = msg.text.strip()
        user_doc = None

        if text.isdigit():
            uid = int(text)
            user_doc = user_col.find_one({"_id": uid})
        elif text.startswith("@"):
            username = text[1:].lower()
            user_doc = user_col.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        else:
            bot.send_message(msg.chat.id, "❌ يرجى إدخال رقم ID أو @username صالح فقط.")
            return

        if not user_doc:
            bot.send_message(msg.chat.id, "❌ هذا المستخدم غير موجود في البوت أو لم يضغط /start بعد.")
            return

        add_admin(user_doc["_id"])
        display = f"@{user_doc.get('username')}" if user_doc.get("username") else user_doc["_id"]
        bot.send_message(msg.chat.id, f"✅ تم إضافة {display} كمشرف بنجاح.")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_remove")
    def handle_remove_admin(call):
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ هذا الخيار متاح فقط للمشرف الأساسي.", show_alert=True)
            return

        admins = get_admins()
        if not admins or len(admins) <= 1:
            bot.edit_message_text("⚠️ لا يوجد مشرفين آخرين لإزالتهم.", call.message.chat.id, call.message.message_id)
            return

        markup = InlineKeyboardMarkup()
        for a in admins:
            uid = a["_id"]
            if uid == ADMIN_ID:
                continue
            uname = a.get("username")
            label = f"@{uname}" if uname else str(uid)
            markup.add(InlineKeyboardButton(f"❌ إزالة {label}", callback_data=f"remove_admin:{uid}"))
        markup.add(InlineKeyboardButton("🔙 العودة", callback_data="menu:admin"))

        bot.edit_message_text("👥 اختر المشرف الذي تريد إزالته:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("remove_admin:"))
    def confirm_remove_admin(call):
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ هذا الخيار متاح فقط للمشرف الأساسي.", show_alert=True)
            return

        uid = int(call.data.split(":")[1])
        remove_admin(uid)
        bot.edit_message_text(f"✅ تم إزالة المشرف: `{uid}` بنجاح.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
