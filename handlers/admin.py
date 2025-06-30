from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID
from utils.db import user_col, get_bot_stats, comp_col
from loader import bot

# ========== لوحة التحكم ==========
@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats"),
        InlineKeyboardButton("📮 الشكاوى", callback_data="admin_complaints"),
    )
    markup.add(
        InlineKeyboardButton("📬 رسالة خاصة", callback_data="admin_reply"),
        InlineKeyboardButton("📢 رسالة جماعية", callback_data="admin_broadcast")
    )
    bot.send_message(msg.chat.id, "🧑‍💼 لوحة التحكم:", reply_markup=markup)

# ========== إحصائيات ==========
@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def show_stats(call):
    stats = get_bot_stats()
    text = f"""📊 إحصائيات البوت:
👤 عدد المستخدمين: {stats['users']}
📬 عدد الشكاوى: {stats['complaints']}"""
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text)

# ========== عرض الشكاوى ==========
@bot.callback_query_handler(func=lambda call: call.data == "admin_complaints")
def list_complaints(call):
    bot.answer_callback_query(call.id)
    complaints = comp_col.find().sort("date", -1).limit(10)
    if complaints.count() == 0:
        bot.send_message(call.message.chat.id, "❌ لا توجد شكاوى حالياً.")
        return

    for c in complaints:
        text = f"📨 من: [{c['user_id']}](tg://user?id={c['user_id']})\n\n📌 {c['text']}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✉️ رد", callback_data=f"reply_to:{c['user_id']}"))
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# ========== رد خاص على شكوى ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_to:"))
def ask_admin_reply(call):
    user_id = int(call.data.split(":")[1])
    bot.send_message(call.message.chat.id, f"✉️ اكتب الرسالة لإرسالها إلى المستخدم {user_id}:")
    bot.register_next_step_handler(call.message, lambda msg: send_admin_reply(msg, user_id))

def send_admin_reply(msg, user_id):
    try:
        bot.send_message(user_id, f"📬 رد من المشرف:\n\n{msg.text}")
        bot.send_message(msg.chat.id, "✅ تم إرسال الرد للمستخدم.")
    except:
        bot.send_message(msg.chat.id, "❌ فشل في إرسال الرسالة.")

# ========== إرسال رسالة خاصة ==========
@bot.callback_query_handler(func=lambda call: call.data == "admin_reply")
def ask_private_user(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "👤 أدخل رقم تعريف المستخدم (user ID):")
    bot.register_next_step_handler(call.message, ask_private_msg)

def ask_private_msg(msg):
    try:
        user_id = int(msg.text.strip())
        bot.send_message(msg.chat.id, "✍️ اكتب الرسالة لإرسالها:")
        bot.register_next_step_handler(msg, lambda m: send_admin_reply(m, user_id))
    except:
        bot.send_message(msg.chat.id, "❌ رقم مستخدم غير صالح.")

# ========== إرسال رسالة جماعية ==========
@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def ask_broadcast_msg(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📢 اكتب الرسالة لإرسالها لجميع المستخدمين:")
    bot.register_next_step_handler(call.message, do_broadcast)

def do_broadcast(msg):
    sent, failed = 0, 0
    for user in user_col.find({}, {"_id": 1}):
        try:
            bot.send_message(user["_id"], msg.text)
            sent += 1
        except:
            failed += 1
    bot.send_message(msg.chat.id, f"📬 تم الإرسال.\n✅ إلى: {sent} مستخدم\n❌ فشل: {failed}")