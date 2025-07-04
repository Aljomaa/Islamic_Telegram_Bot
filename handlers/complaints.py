from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId
from datetime import datetime
from utils.db import comp_col, get_admins, is_admin

def show_complaint_menu(bot, chat_id, message_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📩 تقديم شكوى", callback_data="start_complaint:complaint"),
        InlineKeyboardButton("💡 تقديم اقتراح", callback_data="start_complaint:suggestion"),
        InlineKeyboardButton("📬 عرض شكاواي", callback_data="view_my_complaints:0")
    )
    bot.edit_message_text("📝 يرجى اختيار نوع الرسالة:", chat_id, message_id, reply_markup=markup)


def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_complaint:"))
    def ask_for_input(call):
        ctype = call.data.split(":")[1]
        bot.send_message(call.message.chat.id, f"📝 أرسل {'شكواك' if ctype == 'complaint' else 'اقتراحك'} الآن (نص، صورة، صوت، فيديو...).")
        bot.register_next_step_handler(call.message, lambda m: save_complaint(bot, m, ctype))

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
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "replies": []
        }

        comp_col.insert_one(data)
        bot.send_message(msg.chat.id, "✅ تم إرسال الرسالة بنجاح. شكرًا لك!")

        for admin in get_admins():
            bot.send_message(
                admin["_id"],
                f"📬 {'شكوى' if ctype == 'complaint' else 'اقتراح'} جديدة من @{data['username']}\n👁️ استخدم /complaints لعرضها."
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_my_complaints:"))
    def view_my_complaints(call):
        bot.answer_callback_query(call.id)
        index = int(call.data.split(":")[1])
        user_id = call.from_user.id
        complaints = list(comp_col.find({"user_id": user_id}).sort("_id", -1))
        if not complaints:
            bot.edit_message_text("📭 لا توجد شكاوى أو اقتراحات لك حتى الآن.", call.message.chat.id, call.message.message_id)
            return

        total = len(complaints)
        c = complaints[index]
        text = f"📌 [{index+1}/{total}] {'شكوى' if c['type']=='complaint' else 'اقتراح'}\n"
        text += f"🕒 أُرسلت في: {c['timestamp']}\n"
        text += f"📎 المحتوى:\n{c['text'] or '—'}\n"

        if c["replies"]:
            text += "\n💬 الردود:\n"
            for r in c["replies"]:
                t = r.get("time", "غير معروف")
                text += f"🕒 {t}\n🔹 {r['text']}\n"
        else:
            text += "\n💬 لا يوجد رد حتى الآن."

        markup = InlineKeyboardMarkup()
        row = []
        if index > 0:
            row.append(InlineKeyboardButton("⏮️ السابق", callback_data=f"view_my_complaints:{index - 1}"))
        if index < total - 1:
            row.append(InlineKeyboardButton("⏭️ التالي", callback_data=f"view_my_complaints:{index + 1}"))
        if row:
            markup.row(*row)
        markup.row(InlineKeyboardButton("⬅️ رجوع", callback_data="menu:complain"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reply:"))
    def start_admin_reply(call):
        if not is_admin(call.from_user.id):
            return
        cid = call.data.split(":")[1]
        bot.send_message(call.message.chat.id, "📝 اكتب الرد الآن.")
        bot.register_next_step_handler(call.message, lambda m: finish_reply(bot, m, cid))

    def finish_reply(bot, msg, cid):
        complaint = comp_col.find_one({"_id": ObjectId(cid)})
        if not complaint:
            bot.send_message(msg.chat.id, "❌ لم يتم العثور على الشكوى.")
            return

        reply_obj = {
            "text": msg.text.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        comp_col.update_one({"_id": ObjectId(cid)}, {"$push": {"replies": reply_obj}})
        bot.send_message(complaint["user_id"], f"📬 رد جديد على {'شكواك' if complaint['type'] == 'complaint' else 'اقتراحك'}:\n\n{reply_obj['text']}")
        bot.send_message(msg.chat.id, "✅ تم إرسال الرد للمستخدم.")


# ✅ أمر /complaints
def handle_callbacks(bot):
    @bot.message_handler(commands=["complaints"])
    def handle_complaints(msg):
        if not is_admin(msg.from_user.id):
            bot.send_message(msg.chat.id, "❌ هذا الأمر مخصص للمشرفين فقط.")
            return

        complaints = list(comp_col.find({"status": "open"}).sort("_id", -1))
        if not complaints:
            bot.send_message(msg.chat.id, "📭 لا توجد شكاوى حالية.")
            return

        send_complaint(bot, msg.chat.id, complaints, 0)

    def send_complaint(bot, chat_id, complaints, index):
        c = complaints[index]
        text = f"📌 [{index+1}/{len(complaints)}] {'شكوى' if c['type']=='complaint' else 'اقتراح'}\n"
        text += f"👤 {c['full_name']} (@{c['username']})\n"
        text += f"🕒 {c['timestamp']}\n"
        text += f"📎 المحتوى:\n{c['text'] or '—'}"

        markup = InlineKeyboardMarkup()
        row = []
        if index > 0:
            row.append(InlineKeyboardButton("⏮️ السابق", callback_data=f"admin_prev:{index - 1}"))
        if index < len(complaints) - 1:
            row.append(InlineKeyboardButton("⏭️ التالي", callback_data=f"admin_next:{index + 1}"))
        if row:
            markup.row(*row)
        markup.row(
            InlineKeyboardButton("💬 رد", callback_data=f"reply:{str(c['_id'])}"),
            InlineKeyboardButton("✅ إغلاق", callback_data=f"close:{str(c['_id'])}")
        )
        markup.row(InlineKeyboardButton("⬅️ رجوع", callback_data="menu:admin"))

        if c["media_type"] == "photo":
            bot.send_photo(chat_id, c["file_id"], caption=text, reply_markup=markup)
        elif c["media_type"] == "video":
            bot.send_video(chat_id, c["file_id"], caption=text, reply_markup=markup)
        elif c["media_type"] == "voice":
            bot.send_voice(chat_id, c["file_id"], caption=text, reply_markup=markup)
        elif c["media_type"] == "sticker":
            bot.send_sticker(chat_id, c["file_id"])
            bot.send_message(chat_id, text, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_next:") or call.data.startswith("admin_prev:"))
    def navigate_complaints(call):
        index = int(call.data.split(":")[1])
        complaints = list(comp_col.find({"status": "open"}).sort("_id", -1))
        bot.answer_callback_query(call.id)
        send_complaint(bot, call.message.chat.id, complaints, index)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("close:"))
    def close_complaint(call):
        if not is_admin(call.from_user.id):
            return
        cid = call.data.split(":")[1]
        comp_col.update_one({"_id": ObjectId(cid)}, {"$set": {"status": "closed"}})
        bot.answer_callback_query(call.id, "✅ تم إغلاق الشكوى.")
        bot.edit_message_text("✅ تم إغلاق هذه الشكوى.", call.message.chat.id, call.message.message_id)
