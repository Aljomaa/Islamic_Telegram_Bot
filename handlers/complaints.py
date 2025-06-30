from utils.db import comp_col

def register(bot):
    @bot.message_handler(commands=['complain'])
    def ask_complaint(msg):
        bot.send_message(msg.chat.id, "✍️ أرسل شكواك أو اقتراحك الآن:")
        bot.register_next_step_handler(msg, save_complaint)

    def save_complaint(msg):
        complaint = {
            "user_id": msg.from_user.id,
            "username": msg.from_user.username or "غير معروف",
            "text": msg.text
        }
        comp_col.insert_one(complaint)
        bot.send_message(msg.chat.id, "✅ تم استلام شكواك، شكرًا لمشاركتك.")