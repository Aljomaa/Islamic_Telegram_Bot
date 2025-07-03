from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID
from utils.db import (
    get_bot_stats,
    get_complaints,
    reply_to_complaint,
    get_all_user_ids,
    is_admin,
    add_admin,
    remove_admin,
    get_admins
)

def register(bot):
    @bot.message_handler(commands=["admin"])
    def admin_panel(msg: Message):
        if not is_admin(msg.from_user.id):
            return
        show_admin_menu(bot, msg.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "menu:admin")
    def open_admin_menu(call):
        if not is_admin(call.from_user.id):
            return
        show_admin_menu(bot, call.message.chat.id, call.message.message_id)

    def show_admin_menu(bot, chat_id, message_id=None):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats"),
            InlineKeyboardButton("📬 الشكاوى والاقتراحات", callback_data="admin_complaints"),
            InlineKeyboardButton("📢 رسالة جماعية", callback_data="admin_broadcast"),
            InlineKeyboardButton("➕ إضافة مشرف", callback_data="admin_add"),
            InlineKeyboardButton("➖ إزالة مشرف", callback_data="admin_remove"),
            InlineKeyboardButton("♻️ إعادة تشغيل", callback_data="admin_restart"),
            InlineKeyboardButton("⏹️ إيقاف البوت", callback_data="admin_stop"),
            InlineKeyboardButton("▶️ تشغيل البوت", callback_data="admin_start"),
        )
        markup.add(
            InlineKeyboardButton("🔙 العودة", callback_data="main_menu")
        )

        text = "🧑‍💼 لوحة تحكم المشرف:\nاختر ما تريد من الأدوات التالية:"
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
    def show_stats(call):
        if not is_admin(call.from_user.id):
            return
        stats = get_bot_stats()
        msg = (
            f"📊 إحصائيات البوت:\n\n"
            f"👤 عدد المستخدمين: {stats['total_users']}\n"
            f"⭐ عدد العناصر في المفضلة: {stats['total_favorites']}\n"
            f"📬 عدد الشكاوى/الاقتراحات: {stats['total_complaints']}"
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                              reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 العودة", callback_data="menu:admin")))

    @bot.callback_query_handler(func=lambda call: call.data == "admin_complaints")
    def show_complaints(call):
        if not is_admin(call.from_user.id):
            return

        complaints = get_complaints()
        if not complaints:
            bot.edit_message_text("✅ لا توجد شكاوى حالياً.",
                                  call.message.chat.id, call.message.message_id,
                                  reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 العودة", callback_data="menu:admin")))
            return

        for comp in complaints:
            text = f"🆔 {comp['user_id']}\n👤 {comp.get('full_name', 'مجهول')} (@{comp.get('username', 'غير معروف')})\n\n📝 {comp['text']}"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("✉️ رد", callback_data=f"reply_to:{comp['_id']}"))
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reply_to:"))
    def ask_reply(call):
        if not is_admin(call.from_user.id):
            return
        complaint_id = call.data.split(":")[1]
        msg = bot.send_message(call.message.chat.id, "✉️ أرسل ردك الآن:")
        bot.register_next_step_handler(msg, lambda m: process_reply(bot, m, complaint_id))

    def process_reply(bot, msg: Message, complaint_id):
        if not is_admin(msg.from_user.id):
            return
        success = reply_to_complaint(complaint_id, msg.text, bot)
        if success:
            bot.send_message(msg.chat.id, "✅ تم إرسال الرد للمستخدم.")
        else:
            bot.send_message(msg.chat.id, "❌ فشل في إرسال الرد.")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
    def ask_broadcast(call):
        if not is_admin(call.from_user.id):
            return
        msg = bot.send_message(call.message.chat.id, "📢 أرسل الرسالة الآن ليتم إرسالها لجميع المستخدمين:")
        bot.register_next_step_handler(msg, lambda m: process_broadcast(bot, m))

    def process_broadcast(bot, msg: Message):
        if not is_admin(msg.from_user.id):
            return
        from utils.db import broadcast_message
        broadcast_message(bot, msg.text)
        bot.send_message(msg.chat.id, "✅ تم إرسال الرسالة بنجاح.")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_add")
    def ask_add_admin(call):
        if not is_admin(call.from_user.id):
            return
        msg = bot.send_message(call.message.chat.id, "🆔 أرسل رقم أو معرف المستخدم لإضافته كمشرف:")
        bot.register_next_step_handler(msg, process_add_admin)

    def process_add_admin(msg: Message):
        if not is_admin(msg.from_user.id):
            return
        identifier = msg.text.strip().lstrip("@")
        success = add_admin(identifier)
        if success:
            bot.send_message(msg.chat.id, "✅ تم إضافة المشرف بنجاح.")
        else:
            bot.send_message(msg.chat.id, "❌ لم يتم العثور على المستخدم أو المشرف موجود بالفعل.")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_remove")
    def ask_remove_admin(call):
        if not is_admin(call.from_user.id):
            return
        msg = bot.send_message(call.message.chat.id, "🆔 أرسل رقم أو معرف المشرف المراد حذفه:")
        bot.register_next_step_handler(msg, process_remove_admin)

    def process_remove_admin(msg: Message):
        if not is_admin(msg.from_user.id):
            return
        identifier = msg.text.strip().lstrip("@")
        success = remove_admin(identifier)
        if success:
            bot.send_message(msg.chat.id, "✅ تم إزالة المشرف بنجاح.")
        else:
            bot.send_message(msg.chat.id, "❌ لم يتم العثور على هذا المشرف.")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_restart")
    def restart_bot(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id, "♻️ تمت إعادة تشغيل البوت (وهمياً)")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_stop")
    def stop_bot(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id, "⏹️ تم إيقاف البوت مؤقتاً (وهمياً)")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_start")
    def start_bot(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id, "▶️ تم تشغيل البوت (وهمياً)")
