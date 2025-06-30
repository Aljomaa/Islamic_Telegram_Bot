from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import comp_col
from config import ADMIN_ID
from bson import ObjectId

def register(bot):
    # ========== إرسال شكوى ==========
    @bot.message_handler(commands=['complain'])
    def ask_complaint(msg):
        bot.send_message(msg.chat.id, "📝 اكتب شكواك أو اقتراحك، وسنقوم بمراجعتها:")
        bot.register_next_step_handler(msg, save_complaint)

    def save_complaint(msg):
        complaint = {
            "user_id": msg.from_user.id,
            "username": msg.from_user.username or "غير معروف",
            "text": msg.text,
            "replied": False
        }
        comp_col.insert_one(complaint)

        bot.reply_to(msg, "✅ تم إرسال شكواك بنجاح. شكراً لتواصلك ❤️")
        bot.send_message(ADMIN_ID, f"📥 شكوى جديدة من @{complaint['username']}:\n\n{msg.text}")

    # ========== فقط للمشرف: عرض الشكاوى ==========
    @bot.message_handler(commands=['admin_complaints'])
    def show_complaints(msg):
        if msg.from_user.id != ADMIN_ID:
            return  # تجاهل الطلب من أي شخص غير المشرف

        complaints = list(comp_col.find({"replied": False}))
        if not complaints:
            bot.send_message(msg.chat.id, "✅ لا توجد شكاوى جديدة حالياً.")
            return

        for c in complaints:
            text = f"📨 من: @{c['username']}\n🆔 ID: {c['user_id']}\n\n📝 {c['text']}"
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✉️ الرد على المستخدم", callback_data=f"reply:{str(c['_id'])}")
            )
            bot.send_message(msg.chat.id, text, reply_markup=markup)

    # ========== بدء الرد ==========
    @bot.callback_query_handler(func=lambda call: call.data.startswith("reply:"))
    def ask_reply(call):
        if call.from_user.id != ADMIN_ID:
            return

        comp_id = call.data.split(":")[1]
        try:
            comp = comp_col.find_one({"_id": ObjectId(comp_id)})
            if not comp:
                bot.answer_callback_query(call.id, "❌ لم يتم العثور على الشكوى.")
                return

            bot.send_message(call.message.chat.id, f"✍️ اكتب ردك لـ @{comp['username']}:")
            bot.register_next_step_handler(call.message, send_reply, comp)
        except:
            bot.send_message(call.message.chat.id, "❌ حصل خطأ أثناء فتح الشكوى.")

    # ========== إرسال الرد للمستخدم ==========
    def send_reply(msg, complaint):
        try:
            user_id = complaint["user_id"]
            bot.send_message(user_id, f"📬 رد على شكواك:\n\n{msg.text}")
            bot.send_message(msg.chat.id, "✅ تم إرسال الرد بنجاح.")
            comp_col.update_one({"_id": complaint["_id"]}, {"$set": {"replied": True}})
        except:
            bot.send_message(msg.chat.id, "❌ فشل في إرسال الرسالة. قد يكون المستخدم حظر البوت.")