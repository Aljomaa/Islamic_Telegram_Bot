from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId
from utils.db import comp_col, user_col
from config import ADMIN_ID

def register(bot):
    @bot.message_handler(commands=['complain'])
    def handle_complaint(msg):
        bot.send_message(msg.chat.id, "📝 اكتب شكواك أو اقتراحك وسأقوم بإرساله للإدارة.")
        bot.register_next_step_handler(msg, lambda m: save_complaint(bot, m))

    def save_complaint(bot, msg):
        comp_col.insert_one({
            "user_id": msg.from_user.id,
            "username": msg.from_user.username or "غير معروف",
            "text": msg.text,
            "status": "open"
        })
        bot.send_message(msg.chat.id, "✅ تم إرسال الشكوى بنجاح. شكرًا لك!")

        # إخطار المشرف
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👁️ عرض الشكاوى", callback_data="view_complaints"))
        bot.send_message(ADMIN_ID, f"📩 شكوى جديدة من @{msg.from_user.username or msg.from_user.id}", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "view_complaints")
    def view_complaints(call):
        if call.from_user.id != ADMIN_ID:
            return bot.answer_callback_query(call.id, "❌ هذا الخيار مخصص للمشرف فقط.")

        complaints = list(comp_col.find({"status": "open"}).sort("_id", -1))
        if not complaints:
            bot.send_message(call.message.chat.id, "📭 لا توجد شكاوى حالياً.")
            return

        for comp in complaints:
            text = f"👤 المستخدم: @{comp['username']}\n🆔 ID: {comp['user_id']}\n\n📝 {comp['text']}"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("✉️ الرد", callback_data=f"reply_comp:{str(comp['_id'])}"))
            markup.add(InlineKeyboardButton("✅ تم الحل", callback_data=f"resolve_comp:{str(comp['_id'])}"))
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reply_comp:"))
    def ask_reply(call):
        if call.from_user.id != ADMIN_ID:
            return
        comp_id = call.data.split(":")[1]
        msg = bot.send_message(call.message.chat.id, "✏️ اكتب الرد الآن:")
        bot.register_next_step_handler(msg, lambda m: send_reply(bot, m, comp_id))

    def send_reply(bot, msg, comp_id):
        try:
            comp = comp_col.find_one({"_id": ObjectId(comp_id)})
        except:
            comp = None

        if not comp:
            bot.send_message(msg.chat.id, "❌ لم يتم العثور على الشكوى.")
            return

        try:
            bot.send_message(comp["user_id"], f"📩 رد الإدارة على شكواك:\n\n{msg.text}")
            bot.send_message(msg.chat.id, "✅ تم إرسال الرد للمستخدم.")
        except:
            bot.send_message(msg.chat.id, "⚠️ تعذر إرسال الرسالة للمستخدم.")

        comp_col.update_one({"_id": ObjectId(comp_id)}, {"$set": {"status": "closed"}})

    @bot.callback_query_handler(func=lambda call: call.data.startswith("resolve_comp:"))
    def resolve_complaint(call):
        if call.from_user.id != ADMIN_ID:
            return
        comp_id = call.data.split(":")[1]
        try:
            comp_col.update_one({"_id": ObjectId(comp_id)}, {"$set": {"status": "closed"}})
            bot.answer_callback_query(call.id, "✅ تم وضع الشكوى كمنتهية.")
            bot.edit_message_text("✅ تم وضع الشكوى كمنتهية.", call.message.chat.id, call.message.message_id)
        except:
            bot.send_message(call.message.chat.id, "❌ حدث خطأ أثناء معالجة الطلب.")
