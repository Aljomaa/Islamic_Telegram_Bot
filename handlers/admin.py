from config import ADMIN_ID
from utils.db import user_col, comp_col

def register(bot):
    @bot.message_handler(commands=['admin'])
    def show_admin_panel(msg):
        if msg.from_user.id != ADMIN_ID:
            return bot.send_message(msg.chat.id, "🚫 لا تملك صلاحية الدخول للوحة التحكم.")
        text = """🧑‍💼 لوحة التحكم:

/users - عدد المستخدمين
/broadcast - إرسال رسالة جماعية
/complaints - عرض الشكاوى
"""
        bot.send_message(msg.chat.id, text)

    @bot.message_handler(commands=['users'])
    def count_users(msg):
        if msg.from_user.id == ADMIN_ID:
            count = user_col.count_documents({})
            bot.send_message(msg.chat.id, f"👤 عدد المستخدمين المسجلين: {count}")

    @bot.message_handler(commands=['broadcast'])
    def ask_broadcast(msg):
        if msg.from_user.id == ADMIN_ID:
            bot.send_message(msg.chat.id, "✍️ أرسل الرسالة التي تريد إرسالها لجميع المستخدمين:")
            bot.register_next_step_handler(msg, send_broadcast)

    def send_broadcast(msg):
        users = user_col.find({}, {"_id": 1})
        success = 0
        for user in users:
            try:
                bot.send_message(user["_id"], msg.text)
                success += 1
            except:
                pass
        bot.send_message(msg.chat.id, f"✅ تم إرسال الرسالة إلى {success} مستخدم.")

    @bot.message_handler(commands=['complaints'])
    def show_complaints(msg):
        if msg.from_user.id == ADMIN_ID:
            complaints = comp_col.find().sort("_id", -1)
            text = "📬 الشكاوى الأخيرة:\n\n"
            for c in complaints:
                text += f"👤 @{c['username']} ({c['user_id']}):\n{c['text']}\n\n"
            bot.send_message(msg.chat.id, text[:4000] if text else "📭 لا توجد شكاوى حالياً.")