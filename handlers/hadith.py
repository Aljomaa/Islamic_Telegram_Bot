import os
import requests
import random
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav

load_dotenv()
API_KEY = os.getenv("HADITH_API_KEY")
API_BASE = "https://www.hadithapi.com/public/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# خريطة أسماء الكتب والـ slugs الخاصة بها من API
BOOKS = {
    "sahih-bukhari": "📘 صحيح البخاري",
    "sahih-muslim": "📗 صحيح مسلم",
    "al-tirmidhi": "📕 سنن الترمذي",
    "abu-dawood": "📙 سنن أبي داود",
    "ibn-e-majah": "📓 سنن ابن ماجه",
    "sunan-nasai": "📒 سنن النسائي",
    "mishkat": "📔 مشكاة المصابيح"
}

# قائمة الكتب
def show_hadith_menu(bot, msg):
    markup = InlineKeyboardMarkup()
    for slug, name in BOOKS.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"hadith_book:{slug}"))
    bot.send_message(msg.chat.id, "📚 اختر مصدر الحديث:", reply_markup=markup)

def register(bot):
    @bot.message_handler(commands=['hadith', 'حديث'])
    def hadith_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def load_random_hadith(call):
        slug = call.data.split(":")[1]
        try:
            url = f"{API_BASE}/hadiths"
            params = {
                "apiKey": API_KEY,
                "book": slug,
                "language": "arabic",
                "limit": 50
            }
            res = requests.get(url, headers=HEADERS, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()

            hadiths = data['hadiths']['data']
            if not hadiths:
                bot.send_message(call.message.chat.id, "❌ لا توجد أحاديث في هذا الكتاب.")
                return

            index = random.randint(0, len(hadiths) - 1)
            show_hadith(bot, call.message.chat.id, slug, hadiths, index, call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR] load_random_hadith: {e}")
            bot.send_message(call.message.chat.id, "❌ حدث خطأ أثناء جلب الحديث.")

    def show_hadith(bot, chat_id, slug, hadiths, index, message_id=None, edit=False):
        try:
            hadith = hadiths[index]
            number = hadith.get("hadithNumber", index + 1)
            text = hadith.get("hadithArabic", "❌ لا يوجد نص")

            message = f"{BOOKS.get(slug)}\n\n🆔 الحديث رقم {number}\n\n{text}"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{slug}:{number}"))

            nav = []
            if index > 0:
                nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"nav_hadith:{slug}:{index - 1}"))
            if index < len(hadiths) - 1:
                nav.append(InlineKeyboardButton("▶️ التالي", callback_data=f"nav_hadith:{slug}:{index + 1}"))
            if nav:
                markup.row(*nav)

            markup.add(InlineKeyboardButton("🏠 العودة للقائمة", callback_data="hadith_back_to_menu"))

            if edit and message_id:
                bot.edit_message_text(message, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, message, reply_markup=markup)

        except Exception as e:
            print(f"[ERROR] show_hadith: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ أثناء عرض الحديث.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav_hadith:"))
    def navigate_hadith(call):
        try:
            _, slug, index = call.data.split(":")
            index = int(index)

            url = f"{API_BASE}/hadiths"
            params = {
                "apiKey": API_KEY,
                "book": slug,
                "language": "arabic",
                "limit": 50
            }
            res = requests.get(url, headers=HEADERS, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
            hadiths = data['hadiths']['data']

            show_hadith(bot, call.message.chat.id, slug, hadiths, index, call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR] navigate_hadith: {e}")
            bot.answer_callback_query(call.id, "❌ تعذر التنقل بين الأحاديث")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def add_to_favorites(call):
        try:
            _, slug, number = call.data.split(":")
            content = f"{BOOKS.get(slug)} - رقم {number}"
            add_to_fav(call.from_user.id, "hadith", content)
            bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")
        except Exception as e:
            print(f"[ERROR] add_to_favorites: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_back_to_menu")
    def back_to_menu(call):
        show_hadith_menu(bot, call.message)
