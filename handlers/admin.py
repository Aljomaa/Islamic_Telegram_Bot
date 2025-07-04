from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils.db import is_admin, add_admin, remove_admin, get_bot_stats, get_admins
from config import OWNER_ID

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
