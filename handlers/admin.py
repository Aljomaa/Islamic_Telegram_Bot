from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID
from utils.db import (
    get_bot_stats,
    get_complaints,
    reply_to_complaint,
    get_all_users,
)
from loader import bot

def register(bot):
    @bot.message_handler(commands=["admin"])
    def admin_panel(msg: Message):
        if msg.from_user.id != ADMIN_ID:
            return

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats"),
            InlineKeyboardButton("📬 الشكاوى والاقتراحات", callback_data="admin_complaints"),
            InlineKeyboardButton("📢 رسالة جماعية", callback_data="admin_broadcast"),
        )
        bot.send_message(msg.chat.id, "🧑‍💼 لوحة تحكم المشرف:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
    def show_stats(call):
        if call.from_user.id != ADMIN_ID:
            return
        stats = get_bot_stats()
        msg = (
            f"📊 إحصائيات البوت:\n\n"
            f"👤 عدد المستخدمين: {stats['total_users']}\n"
            f"⭐ عدد العناصر في المفضلة: {stats['total_favorites']}\n"
            f"📬 عدد الشكاوى/الاقتراحات: {stats['total_complaints']}"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, msg)

    @bot.callback_query_handler(func=lambda call: call.data == "admin_complaints")
    def show_complaints(call):
        if call.from_user.id != ADMIN_ID:
            return

        complaints = get_complaints()
        if not complaints:
            bot.send_message(call.message.chat.id, "✅ لا توجد شكاوى حالياً.")
            return

        for comp in complaints:
            text = f"🆔 {comp['user_id']}\n📝 {comp['text']}"
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✉️ رد", callback_data=f"reply_to:{comp['_id']}")
            )
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reply_to:"))
    def ask_reply(call):
        if call.from_user.id != ADMIN_ID:
            return

        complaint_id = call.data.split(":")[1]
        msg = bot.send_message(call.message.chat.id, "✉️ أرسل ردك الآن:")
        bot.register_next_step_handler(msg, process_reply, complaint_id)

    def process_reply(msg, complaint_id):
        if msg.from_user.id != ADMIN_ID:
            return
        success = reply_to_complaint(complaint_id, msg.text)
        if success:
            bot.send_message(msg.chat.id, "✅ تم إرسال الرد بنجاح.")
        else:
            bot.send_message(msg.chat.id, "❌ فشل في إرسال الرد.")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
    def ask_broadcast(call):
        if call.from_user.id != ADMIN_ID:
            return
        msg = bot.send_message(call.message.chat.id, "📢 أرسل الرسالة التي تريد إرسالها للجميع:")
        bot.register_next_step_handler(msg, process_broadcast)

    def process_broadcast(msg: Message):
        if msg.from_user.id != ADMIN_ID:
            return
        broadcast_message(bot, msg.text)
        bot.send_message(msg.chat.id, "✅ تم إرسال الرسالة لجميع المستخدمين.")

# ================================
# 📨 دالة الإرسال الجماعي هنا
# ================================
def broadcast_message(bot, message_text):
    for user in get_all_users():
        try:
            bot.send_message(user["_id"], message_text)
        except:
            continue
