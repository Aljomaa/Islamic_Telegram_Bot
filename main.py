import telebot
from config import BOT_TOKEN
from handlers import prayers, quran, athkar, favorites, complaints, admin, hadith
from tasks import reminders

import threading
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import register_user

bot = telebot.TeleBot(BOT_TOKEN)

# بدء تشغيل التذكيرات
reminders.start_reminders(bot)

# رسالة الترحيب وزر القائمة الرئيسية
@bot.message_handler(commands=['start'])
def welcome(msg):
    register_user(msg.from_user.id)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🕌 أوقات الصلاة", callback_data="menu:prayer"),
        InlineKeyboardButton("📖 القرآن الكريم", callback_data="menu:quran"),
        InlineKeyboardButton("📿 الأذكار", callback_data="menu:athkar"),
        InlineKeyboardButton("📜 الحديث", callback_data="menu:hadith"),
        InlineKeyboardButton("⭐ المفضلة", callback_data="menu:fav"),
        InlineKeyboardButton("📝 الشكاوى", callback_data="menu:complain"),
        InlineKeyboardButton("🧑‍💼 المشرف", callback_data="menu:admin")
    )

    bot.send_message(msg.chat.id, "🌙 مرحبًا بك في البوت الإسلامي!\nاختر أحد الخيارات:", reply_markup=markup)

# معالجة أزرار القائمة الرئيسية
@bot.callback_query_handler(func=lambda call: call.data.startswith("menu:"))
def handle_main_menu(call):
    action = call.data.split(":")[1]

    if action == "prayer":
        from handlers.prayers import show_prayer_times
        show_prayer_times(bot, call.message)

    elif action == "quran":
        from handlers.quran import show_main_quran_menu
        show_main_quran_menu(bot, call.message)

    elif action == "athkar":
        from handlers.athkar import show_athkar_menu
        show_athkar_menu(bot, call.message)

    elif action == "hadith":
        from handlers.hadith import show_hadith_menu
        show_hadith_menu(bot, call.message)

    elif action == "fav":
        bot.send_message(call.message.chat.id, "/fav")

    elif action == "complain":
        bot.send_message(call.message.chat.id, "/complain")

    elif action == "admin":
        bot.send_message(call.message.chat.id, "/admin")

# تسجيل باقي الأوامر
prayers.register(bot)
quran.register(bot)
quran.handle_callbacks(bot)
athkar.register(bot)
favorites.register(bot)
complaints.register(bot)
admin.register(bot)
hadith.register(bot)

# إعداد وتشغيل البوت مع خادم Flask
def run_bot():
    bot.infinity_polling()

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
