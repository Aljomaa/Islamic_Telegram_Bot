import os
import requests
import random
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav

load_dotenv()
API_KEY = os.getenv("HADITH_API_KEY")

API_URL = "https://www.hadithapi.com/public/api/hadiths"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}
LANG = "arabic"

# عرض قائمة الكتب
def show_hadith_menu(bot, msg):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📚 حديث عشوائي", callback_data="hadith_random"))
    bot.send_message(msg.chat.id, "📖 اختر من القائمة:", reply_markup=markup)

def register(bot):
    @bot.message_handler(commands=['hadith', 'حديث'])
    def hadith_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_random")
    def handle_random(call):
        fetch_and_display(bot, call.message.chat.id, call.message.message_id, index=None)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav_hadith:"))
    def handle_nav(call):
        try:
            _, index = call.data.split(":")
            fetch_and_display(bot, call.message.chat.id, call.message.message_id, int(index))
        except Exception as e:
            print(f"[ERROR] navigate: {e}")
            bot.answer_callback_query(call.id, "❌ تعذر التنقل")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def handle_fav(call):
        try:
            _, number = call.data.split(":")
            content = f"📖 حديث رقم {number}"
            add_to_fav(call.from_user.id, "hadith", content)
            bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")
        except Exception as e:
            print(f"[ERROR] fav: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_back_to_menu")
    def back_to_menu(call):
        show_hadith_menu(bot, call.message)

def fetch_and_display(bot, chat_id, message_id, index=None, edit=True):
    try:
        params = {
            "apiKey": API_KEY,
            "language": LANG,
            "limit": 20,
            "page": 1
        }
        res = requests.get(API_URL, headers=HEADERS, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        hadiths = data.get("hadiths", {}).get("data", [])

        if not hadiths:
            bot.send_message(chat_id, "❌ لا توجد أحاديث.")
            return

        if index is None:
            index = random.randint(0, len(hadiths) - 1)

        if index < 0 or index >= len(hadiths):
            bot.send_message(chat_id, "❌ رقم الحديث غير صحيح.")
            return

        hadith = hadiths[index]
        number = hadith.get("hadithNumber", index + 1)
        text = hadith.get("hadithArabic", "❌ لا يوجد نص.")

        message = f"📖 الحديث رقم {number}\n\n{text}"

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{number}")
        )

        nav_buttons = []
        if index > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"nav_hadith:{index - 1}"))
        if index < len(hadiths) - 1:
            nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"nav_hadith:{index + 1}"))
        if nav_buttons:
            markup.row(*nav_buttons)

        markup.add(InlineKeyboardButton("🏠 العودة للقائمة", callback_data="hadith_back_to_menu"))

        if edit:
            bot.edit_message_text(message, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, message, reply_markup=markup)

    except Exception as e:
        print(f"[ERROR] fetch_and_display: {e}")
        bot.send_message(chat_id, "❌ حدث خطأ أثناء جلب الحديث.")
