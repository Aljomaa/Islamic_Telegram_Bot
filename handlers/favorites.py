from utils.db import user_col

def register(bot):
    @bot.message_handler(commands=['fav'])
    def get_favs(msg):
        data = user_col.find_one({"_id": msg.from_user.id})
        if data and "favs" in data and data["favs"]:
            favs = "\n\n".join(data["favs"])
            bot.send_message(msg.chat.id, f"⭐ مفضلتك:\n\n{favs}")
        else:
            bot.send_message(msg.chat.id, "📭 لا توجد عناصر محفوظة في المفضلة بعد.")

    @bot.message_handler(func=lambda m: m.text and m.text.startswith("⭐"))
    def save_fav(msg):
        text = msg.text[1:].strip()
        if not text:
            bot.send_message(msg.chat.id, "❌ لا يوجد محتوى لحفظه.")
            return
        user_col.update_one(
            {"_id": msg.from_user.id},
            {"$addToSet": {"favs": text}},
            upsert=True
        )
        bot.reply_to(msg, "✅ تم حفظ هذا المحتوى في مفضلتك.")