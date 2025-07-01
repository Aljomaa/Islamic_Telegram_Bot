import requests
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav

API_URL = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions"

BOOKS = {
    "bukhari": "📘 صحيح البخاري",
    "muslim": "📗 صحيح مسلم",
    "abudawud": "📙 سنن أبي داود",
    "tirmidhi": "📕 سنن الترمذي",
    "nasai": "📒 سنن النسائي"
}

def register(bot):
    @bot.message_handler(commands=['hadith'])
    def hadith_menu(msg):
        markup = InlineKeyboardMarkup()
        for key, name in BOOKS.items():
            markup.add(InlineKeyboardButton(name, callback_data=f"hadith_book:{key}"))
        bot.send_message(msg.chat.id, "📚 اختر مصدر الحديث:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def send_random_hadith(call):
        book_key = call.data.split(":")[1]
        try:
            url = f"{API_URL}/{book_key}.json"
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            data = res.json()
            hadiths = data["hadiths"]

            chosen = random.choice(hadiths)
            number = chosen.get("hadithNumber", "؟")
            text = chosen.get("arab", "❌ لا يوجد نص")

            text = f"{BOOKS[book_key]}\n\n🆔 رقم الحديث: {number}\n\n{str(text)}"

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔁 حديث آخر", callback_data=f"hadith_book:{book_key}"))
            markup.add(InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{book_key}:{number}"))

            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            print(f"[ERROR] Hadith fetch: {e}")
            bot.send_message(call.message.chat.id, "❌ حدث خطأ أثناء جلب الحديث.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def add_to_favorites(call):
        try:
            _, book_key, number = call.data.split(":")
            content = f"{BOOKS.get(book_key, 'حديث')} - رقم {number}"
            add_to_fav(call.from_user.id, "hadith", content)
            bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")
        except Exception as e:
            print(f"[ERROR] Add hadith to favorites: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")
