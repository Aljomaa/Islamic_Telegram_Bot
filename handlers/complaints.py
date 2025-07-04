from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId
from utils.db import comp_col, get_admins
from datetime import datetime

# ✅ عرض قائمة نوع الرسالة
def show_complaint_menu(bot, chat_id, message_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📩 تقديم شكوى", callback_data="start_complaint:complaint"),
        InlineKeyboardButton("💡 تقديم اقتراح", callback_data="start_complaint:suggestion")
    )
    bot.edit_message_text("📝 يرجى اختيار نوع الرسالة:", chat_id, message_id, reply_markup=markup)

# ✅ تسجيل المعالجات
def register(bot):
    # استقبال الشكوى أو الاقتراح
    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_complaint:"))
    def ask_for_input(call):
        ctype = call.data.split(":")[1]
        bot.send_message(call.message.chat.id, f"📝 أرسل { 'شكواك' if ctype == 'complaint' else 'اقتراحك' } الآن (نص، صورة، صوت، فيديو...).")
        bot.register_next_step_handler(call.message, lambda m: save_complaint(bot, m, ctype))

    # حفظ الشكوى
    def save_complaint(bot, msg, ctype):
        media_type, file_id = None, None

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

        # إخطار كل المشرفين
        for admin in get_admins():
            bot.send_message(
                admin["_id"],
                f"📬 { 'شكوى' if ctype == 'complaint' else 'اقتراح' } جديدة من @{data['username']}\n👁️ استخدم /complaints لعرضها."
            )

    # عرض الشكاوى
    @bot.message_handler(commands=['complaints'])
    def show_all_complaints_command(msg):
        from utils.db import is_admin
        if not is_admin(msg.from_user.id):
            return
        complaints = list(comp_col.find({"status": "open"}).sort("_id", -1))
        if not complaints:
            bot.send_message(msg.chat.id, "📭 لا توجد شكاوى حالياً.")
        else:
            show_complaint(bot, msg.chat.id, complaints, 0)

# ✅ عرض شكوى واحدة مع أزرار التحكم
def show_complaint(bot, chat_id, complaints, index):
    if index < 0 or index >= len(complaints):
        return

    comp = complaints[index]
    text = f"👤 الاسم: {comp['full_name']}\n"
    text += f"🆔 ID: {comp['user_id']}\n"
    text += f"🔗 المستخدم: @{comp['username']}\n"
    text += f"🕓 الوقت: {comp['timestamp']}\n"
    text += f"📌 النوع: {'شكوى' if comp['type'] == 'complaint' else 'اقتراح'}\n\n"
    text += f"📝 المحتوى:\n{comp['text']}" if comp['text'] else ""

    markup = InlineKeyboardMarkup(row_width=2)
    if index > 0:
        markup.add(InlineKeyboardButton("⬅️ السابق", callback_data=f"comp_nav:{index-1}"))
    if index < len(complaints) - 1:
        markup.add(InlineKeyboardButton("➡️ التالي", callback_data=f"comp_nav:{index+1}"))

    markup.add(
        InlineKeyboardButton("✉️ الرد", callback_data=f"reply_comp:{str(comp['_id'])}"),
        InlineKeyboardButton("✅ تم الحل", callback_data=f"resolve_comp:{str(comp['_id'])}")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="close_complaint_view"))
    markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main"))

    if comp['media_type'] == "photo":
        bot.send_photo(chat_id, comp['file_id'], caption=text, reply_markup=markup)
    elif comp['media_type'] == "video":
        bot.send_video(chat_id, comp['file_id'], caption=text, reply_markup=markup)
    elif comp['media_type'] == "voice":
        bot.send_voice(chat_id, comp['file_id'])
        bot.send_message(chat_id, text, reply_markup=markup)
    elif comp['media_type'] == "sticker":
        bot.send_sticker(chat_id, comp['file_id'])
        bot.send_message(chat_id, text, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

# ✅ الرد على شكوى
def handle_callbacks(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("comp_nav:"))
    def navigate_complaints(call):
        from utils.db import is_admin
        if not is_admin(call.from_user.id):
            return
        index = int(call.data.split(":")[1])
        complaints = list(comp_col.find({"status": "open"}).sort("_id", -1))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_complaint(bot, call.message.chat.id, complaints, index)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reply_comp:"))
    def ask_reply(call):
        from utils.db import is_admin
        if not is_admin(call.from_user.id):
            return
        comp_id = call.data.split(":")[1]
        msg = bot.send_message(call.message.chat.id, "✏️ اكتب الرد الآن:")
        bot.register_next_step_handler(msg, lambda m: send_reply(bot, m, comp_id))

    def send_reply(bot, msg, comp_id):
        comp = comp_col.find_one({"_id": ObjectId(comp_id)})
        if not comp:
            bot.send_message(msg.chat.id, "❌ لم يتم العثور على الشكوى.")
            return

        try:
            bot.send_message(
                comp["user_id"],
                f"📩 رد الإدارة على {'الشكوى' if comp['type'] == 'complaint' else 'الاقتراح'}:\n\n{msg.text}"
            )
            bot.send_message(msg.chat.id, "✅ تم إرسال الرد للمستخدم.")
            comp_col.update_one({"_id": ObjectId(comp_id)}, {"$set": {"status": "closed"}})
        except:
            bot.send_message(msg.chat.id, "⚠️ تعذر إرسال الرسالة للمستخدم.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("resolve_comp:"))
    def resolve_complaint(call):
        from utils.db import is_admin
        if not is_admin(call.from_user.id):
            return
        comp_id = call.data.split(":")[1]
        comp_col.update_one({"_id": ObjectId(comp_id)}, {"$set": {"status": "closed"}})
        bot.answer_callback_query(call.id, "✅ تم وضع الشكوى كمنتهية.")
        bot.edit_message_text("✅ تم حل الشكوى.", call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "close_complaint_view")
    def close_view(call):
        bot.delete_message(call.message.chat.id, call.message.message_id)
