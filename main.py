import telebot
from config import BOT_TOKEN
from handlers import prayers, quran, athkar, favorites, complaints, admin, hadith
from tasks import reminders  # استيراد reminders

import threading
from flask import Flask

bot = telebot.TeleBot(BOT_TOKEN)

# ✅ تسجيل المستخدم عند /start
@bot.message_handler(commands=['start'])
def welcome(msg):
    from utils.db import register_user
    register_user(msg.from_user)

    bot.reply_to(msg, """🌙 مرحبًا بك في البوت الإسلامي!

🕌 /prayer - أوقات الصلاة  
📖 /quran - عرض سورة  
🔊 /ayah - تلاوة آية أو تصفح القرآن  
📿 /athkar - الأذكار اليومية  
📜 /hadith - عرض حديث من الكتب الستة  
🔍 /search_hadith - (سيضاف لاحقاً) بحث في الأحاديث  
⭐ /fav - المفضلة  
📝 /complain - إرسال شكوى أو اقتراح  
🧑‍💼 /admin - لوحة تحكم المشرف
""")

# ✅ تسجيل جميع الأوامر
prayers.register(bot)
quran.register(bot)
athkar.register(bot)
favorites.register(bot)
complaints.register(bot)
admin.register(bot)
hadith.register(bot)

# ✅ بدء مهام التنبيهات في خيوط منفصلة
reminders.start_reminders()

# ✅ تشغيل البوت في خيط منفصل
def run_bot():
    bot.infinity_polling()

# ✅ خادم Flask لتجاوز قيود Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
