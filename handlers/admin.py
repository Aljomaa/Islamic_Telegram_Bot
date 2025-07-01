from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import get_bot_stats, broadcast_message, get_complaints, reply_to_complaint
from config import ADMIN_ID

def register(bot):
    @bot.message_handler(commands=["admin"])
    def admin_panel(msg):
        if msg.from_user.id != ADMIN_ID:
            return
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats"),
            InlineKeyboardButton("📬 الشكاوى والاقتراحات", callback_data="admin_complaints"),
            InlineKeyboardButton("📢 رسالة جماعية", callback_data="admin_broadcast")
        )
        bot.send_message(msg.chat.id, "🧑‍💼 لوحة تحكم المشرف:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
    def send_stats(call):
        stats = get_bot_stats()
        text = f"👤 عدد المستخدمين: {stats['users']}\n✉️ عدد الشكاوى: {stats['complaints']}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text)

    @bot.callback_query_handler(func=lambda call: call.data == "admin_complaints")
    def show_complaints(call):
        complaints = get_complaints()
        if not complaints:
            bot.send_message(call.message.chat.id, "📭 لا توجد شكاوى حالياً.")
            return
        for comp in complaints:
            text = f"🆔 {comp['_id']}\n👤 من: {comp['user_id']}\n📝 {comp['message']}"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("↩️ رد", callback_data=f"reply_comp:{comp['_id']}"))
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reply_comp:"))
    def ask_reply(call):
        comp_id = call.data.split(":")[1]
        bot.send_message(call.message.chat.id, "📝 اكتب الرد:")
        bot.register_next_step_handler(call.message, lambda m: handle_reply(m, comp_id))

    def handle_reply(msg, comp_id):
        reply_to_complaint(comp_id, msg.text)
        bot.send_message(msg.chat.id, "✅ تم إرسال الرد للمستخدم.")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
    def ask_broadcast(call):
        bot.send_message(call.message.chat.id, "📝 أرسل الرسالة التي تريد إرسالها لجميع المستخدمين:")
        bot.register_next_step_handler(call.message, process_broadcast)

    def process_broadcast(msg):
        count = broadcast_message(msg.text, bot)
        bot.send_message(msg.chat.id, f"📢 تم إرسال الرسالة إلى {count} مستخدم.")