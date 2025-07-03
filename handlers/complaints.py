from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId
from utils.db import comp_col
from config import ADMIN_ID
from datetime import datetime

def show_complaint_menu(bot, chat_id, message_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📩 تقديم شكوى", callback_data="start_complaint:complaint"),
        InlineKeyboardButton("💡 تقديم اقتراح", callback_data="start_complaint:suggestion")
    )
    bot.edit_message_text("يرجى اختيار نوع الرسالة:", chat_id, message_id, reply_markup=markup)

def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_complaint:"))
    def ask_for_input(call):
        ctype = call.data.split(":")[1]
        bot.send_message(call.message.chat.id, f"📝 أرسل { 'شكواك' if ctype == 'complaint' else 'اقتراحك' } الآن (نص، صورة، صوت، فيديو...).")
        bot.register_next_step_handler(call.message, lambda m: save_complaint(bot, m, ctype))

    def save_complaint(bot, msg, ctype):
        media_type = None
        file_id = None

        if msg.text:
            content = msg.text
            media_type = 'text'
        elif msg.photo:
            content = msg.caption or ""
            media_type = 'photo'
            file_id = msg.photo[-1].file_id
        elif msg.voice:
            content = msg.caption or ""
            media_type = 'voice'
            file_id = msg.voice.file_id
        elif msg.video:
            content = msg.caption or ""
            media_type = 'video'
            file_id = msg.video.file_id
        elif msg.sticker:
            content = ""
            media_type = 'sticker'
            file_id = msg.sticker.file_id
        else:
            bot.send_message(msg.chat.id, "❌ لم يتم التعرف على نوع الرسالة.")
            return

        data = {
            "user_id": msg.from_user.id,
            "username": msg.from_user.username or "غير معروف",
            "full_name": msg.from_user.full_name or "غير معروف",
            "text": content,
            "media_type": media_type,
            "file_id": file_id,
            "status": "open",
            "type": ctype,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        comp_col.insert_one(data)
        bot.send_message(msg.chat.id, "✅ تم إرسال الرسالة بنجاح. شكرًا لك!")

        # إخطار المشرف
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👁️ عرض الشكاوى", callback_data="view_complaints"))
        bot.send_message(ADMIN_ID, f"📩 { 'شكوى' if ctype == 'complaint' else 'اقتراح' } جديدة من @{data['username']}", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "view_complaints")
    def view_complaints(call):
        if call.from_user.id != ADMIN_ID:
            return bot.answer_callback_query(call.id, "❌ هذا الخيار مخصص للمشرف فقط.")

        complaints = list(comp_col.find({"status": "open"}).sort("_id", -1))
        if not complaints:
            bot.send_message(call.message.chat.id, "📭 لا توجد شكاوى حالياً.")
            return

        for comp in complaints:
            text = f"👤 الاسم: {comp['full_name']}\n"
            text += f"🆔 ID: {comp['user_id']}\n"
            text += f"🔗 المستخدم: @{comp['username']}\n"
            text += f"🕓 الوقت: {comp['timestamp']}\n"
            text += f"📌 النوع: {'شكوى' if comp['type'] == 'complaint' else 'اقتراح'}\n\n"
            text += f"📝 المحتوى:\n{comp['text']}" if comp['text'] else ""

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✉️ الرد", callback_data=f"reply_comp:{str(comp['_id'])}"),
                InlineKeyboardButton("✅ تم الحل", callback_data=f"resolve_comp:{str(comp['_id'])}")
            )

            if comp['media_type'] == "photo":
                bot.send_photo(call.message.chat.id, comp['file_id'], caption=text, reply_markup=markup)
            elif comp['media_type'] == "video":
                bot.send_video(call.message.chat.id, comp['file_id'], caption=text, reply_markup=markup)
            elif comp['media_type'] == "voice":
                bot.send_voice(call.message.chat.id, comp['file_id'])
                bot.send_message(call.message.chat.id, text, reply_markup=markup)
            elif comp['media_type'] == "sticker":
                bot.send_sticker(call.message.chat.id, comp['file_id'])
                bot.send_message(call.message.chat.id, text, reply_markup=markup)
            else:
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
            bot.send_message(comp["user_id"], f"📩 رد الإدارة على {'الشكوى' if comp['type'] == 'complaint' else 'الاقتراح'}:\n\n{msg.text}")
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
