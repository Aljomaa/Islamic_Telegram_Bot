import telebot
from config import BOT_TOKEN
from handlers import prayers, quran, athkar, favorites, complaints, admin, hadith

import threading
from flask import Flask

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def welcome(msg):
    bot.reply_to(msg, """🌙 مرحبًا بك في البوت الإسلامي!

🕌 /prayer - أوقات الصلاة  
📖 /quran - عرض سورة  
🔊 /ayah - تلاوة آية  
📿 /athkar - الأذكار اليومية  
📜 /hadith - حديث عشوائي  
🔍 /search_hadith - بحث في الأحاديث  
⭐ /fav - المفضلة  
📝 /complain - شكوى  
🧑‍💼 /admin - لوحة التحكم
""")

# تسجيل الأوامر
prayers.register(bot)
quran.register(bot)
athkar.register(bot)
favorites.register(bot)
complaints.register(bot)
admin.register(bot)
hadith.register(bot)

# تشغيل البوت في خيط منفصل
def run_bot():
    bot.infinity_polling()

# خادم Flask وهمي لتخطي فحص Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)