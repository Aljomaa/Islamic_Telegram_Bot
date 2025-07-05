from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils.db import is_admin, add_admin, remove_admin, get_bot_stats, get_admins, get_all_user_ids
from config import OWNER_ID

broadcast_cache = {}

def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin:"))
    def handle_admin_actions(call: CallbackQuery):
        bot.answer_callback_query(call.id)
        data = call.data.split(":")

        if data[1] == "menu":
            show_admin_menu(bot, call.message.chat.id, call.message.message_id)

        elif data[1] == "stats":
            stats = get_bot_stats()
            msg = f"📊 إحصائيات البوت:\n\n👤 المستخدمون: {stats['total_users']}\n⭐ المفضلة: {stats['total_favorites']}\n📝 الشكاوى: {stats['total_complaints']}"
            back_button = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 عودة", callback_data="admin:menu"))
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=back_button)

        elif data[1] == "add":
            if call.from_user.id != OWNER_ID:
                bot.answer_callback_query(call.id, "❌ فقط مالك البوت يمكنه إضافة مشرفين.", show_alert=True)
                return
            msg = bot.send_message(call.message.chat.id, "🆔 أرسل معرف المستخدم أو رقمه لإضافته كمشرف:")
            bot.register_next_step_handler(msg, lambda m: process_add_admin(bot, m))

        elif data[1] == "list":
            admins = get_admins()
            if not admins:
                bot.edit_message_text("❌ لا يوجد مشرفون حالياً.", call.message.chat.id, call.message.message_id)
                return

            markup = InlineKeyboardMarkup(row_width=1)
            for admin in admins:
                admin_id = admin["_id"]
                username = admin.get("username", f"{admin_id}")
                label = f"🧑‍💼 @{username}" if username else f"🧑‍💼 {admin_id}"
                if str(admin_id) != str(OWNER_ID):
                    markup.add(InlineKeyboardButton(f"{label} ❌ إزالة", callback_data=f"admin:remove:{admin_id}"))
                else:
                    markup.add(InlineKeyboardButton(f"{label} 👑", callback_data="none"))

            markup.add(InlineKeyboardButton("🔙 عودة", callback_data="admin:menu"))
            bot.edit_message_text("👥 قائمة المشرفين:", call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif data[1] == "remove":
            target_id = data[2]
            if str(call.from_user.id) != str(OWNER_ID):
                bot.answer_callback_query(call.id, "❌ فقط مالك البوت يمكنه إزالة مشرفين.", show_alert=True)
                return
            if str(target_id) == str(OWNER_ID):
                bot.answer_callback_query(call.id, "❌ لا يمكنك إزالة نفسك كمالك للبوت.", show_alert=True)
                return
            success = remove_admin(target_id)
            if success:
                bot.answer_callback_query(call.id, "✅ تم إزالة المشرف.")
                show_admin_menu(bot, call.message.chat.id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "❌ فشل في إزالة المشرف.")

    @bot.callback_query_handler(func=lambda call: call.data == "broadcast:start")
    def start_broadcast(call):
        if not is_admin(call.from_user.id):
            return
        msg = bot.send_message(call.message.chat.id, "📝 أرسل الآن الرسالة الجماعية (نص أو صورة أو فيديو أو غيرها):")
        bot.register_next_step_handler(msg, lambda m: preview_broadcast(bot, m))

    @bot.callback_query_handler(func=lambda call: call.data == "broadcast:confirm")
    def confirm_broadcast(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id, "🚀 يتم الآن إرسال الرسالة...")
        content = broadcast_cache.get(call.from_user.id)
        if not content:
            bot.send_message(call.message.chat.id, "❌ لا توجد رسالة لإرسالها.")
            return

        user_ids = get_all_user_ids()
        sent = 0

        for user_id in user_ids:
            try:
                if content['type'] == 'text':
                    bot.send_message(user_id, content['text'])
                elif content['type'] == 'photo':
                    bot.send_photo(user_id, content['file_id'], caption=content['caption'])
                elif content['type'] == 'video':
                    bot.send_video(user_id, content['file_id'], caption=content['caption'])
                elif content['type'] == 'voice':
                    bot.send_voice(user_id, content['file_id'], caption=content['caption'])
                elif content['type'] == 'document':
                    bot.send_document(user_id, content['file_id'], caption=content['caption'])
                elif content['type'] == 'sticker':
                    bot.send_sticker(user_id, content['file_id'])
                sent += 1
            except:
                continue

        bot.send_message(call.message.chat.id, f"✅ تم إرسال الرسالة إلى {sent} مستخدم.")
        del broadcast_cache[call.from_user.id]

    @bot.callback_query_handler(func=lambda call: call.data == "broadcast:cancel")
    def cancel_broadcast(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id, "❌ تم إلغاء الإرسال.")
        show_admin_menu(bot, call.message.chat.id, call.message.message_id)

def preview_broadcast(bot, msg):
    media_type = None
    file_id = None
    caption = msg.caption or msg.text or ""

    if msg.text:
        media_type = 'text'
        broadcast_cache[msg.from_user.id] = {"type": "text", "text": msg.text}

    elif msg.photo:
        media_type = 'photo'
        file_id = msg.photo[-1].file_id
        broadcast_cache[msg.from_user.id] = {"type": "photo", "file_id": file_id, "caption": caption}

    elif msg.video:
        media_type = 'video'
        file_id = msg.video.file_id
        broadcast_cache[msg.from_user.id] = {"type": "video", "file_id": file_id, "caption": caption}

    elif msg.voice:
        media_type = 'voice'
        file_id = msg.voice.file_id
        broadcast_cache[msg.from_user.id] = {"type": "voice", "file_id": file_id, "caption": caption}

    elif msg.document:
        media_type = 'document'
        file_id = msg.document.file_id
        broadcast_cache[msg.from_user.id] = {"type": "document", "file_id": file_id, "caption": caption}

    elif msg.sticker:
        media_type = 'sticker'
        file_id = msg.sticker.file_id
        broadcast_cache[msg.from_user.id] = {"type": "sticker", "file_id": file_id}

    else:
        bot.send_message(msg.chat.id, "❌ نوع الرسالة غير مدعوم.")
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ نعم، أرسل", callback_data="broadcast:confirm"),
        InlineKeyboardButton("❌ إلغاء", callback_data="broadcast:cancel")
    )

    if media_type == "text":
        bot.send_message(msg.chat.id, f"📬 المعاينة:\n\n{msg.text}", reply_markup=markup)
    elif media_type == "photo":
        bot.send_photo(msg.chat.id, file_id, caption=caption, reply_markup=markup)
    elif media_type == "video":
        bot.send_video(msg.chat.id, file_id, caption=caption, reply_markup=markup)
    elif media_type == "voice":
        bot.send_voice(msg.chat.id, file_id, caption=caption, reply_markup=markup)
    elif media_type == "document":
        bot.send_document(msg.chat.id, file_id, caption=caption, reply_markup=markup)
    elif media_type == "sticker":
        bot.send_sticker(msg.chat.id, file_id)
        bot.send_message(msg.chat.id, "📬 هل تريد إرسال هذا الملصق؟", reply_markup=markup)

def show_admin_menu(bot, chat_id, message_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 الإحصائيات", callback_data="admin:stats"),
        InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="broadcast:start"),
        InlineKeyboardButton("➕ إضافة مشرف", callback_data="admin:add"),
        InlineKeyboardButton("👥 عرض المشرفين", callback_data="admin:list")
    )
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main"))

    bot.edit_message_text("🧑‍💼 لوحة المشرف:", chat_id, message_id, reply_markup=markup)

def process_add_admin(bot, msg):
    user_input = msg.text.strip()
    if not user_input:
        bot.reply_to(msg, "❌ يرجى إدخال قيمة صحيحة.")
        return

    if user_input.startswith("@"):
        user_input = user_input[1:]

    if not user_input.isdigit() and not user_input.isalnum():
        bot.reply_to(msg, "❌ يرجى إدخال رقم ID أو @username صالح فقط.")
        return

    success = add_admin(user_input)
    if success:
        bot.reply_to(msg, f"✅ تم إضافة {user_input} كمشرف بنجاح.")
    else:
        bot.reply_to(msg, "❌ هذا المستخدم غير موجود في البوت أو لم يضغط /start بعد.")
