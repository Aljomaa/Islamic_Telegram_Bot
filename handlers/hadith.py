import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
import random

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

            index = random.randint(0, len(hadiths) - 1)
            return send_hadith(call.message.chat.id, book_key, index, call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR] Hadith fetch: {e}")
            bot.send_message(call.message.chat.id, "❌ حدث خطأ أثناء جلب الحديث.")

    def send_hadith(chat_id, book_key, index, message_id=None, edit=False):
        try:
            url = f"{API_URL}/{book_key}.json"
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            data = res.json()
            hadiths = data["hadiths"]

            if not (0 <= index < len(hadiths)):
                return bot.send_message(chat_id, "❌ لا يوجد حديث بهذا الرقم")

            hadith = hadiths[index]
            number = hadith.get("hadithNumber", index + 1)
            text = hadith.get("arab", "❌ لا يوجد نص")

            full_text = f"{BOOKS.get(book_key)}\n\n🆔 الحديث رقم {number}\n\n{text}"

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("🔁 حديث آخر", callback_data=f"hadith_book:{book_key}"),
                InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{book_key}:{number}")
            )

            nav_buttons = []
            if index > 0:
                nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"nav_hadith:{book_key}:{index-1}"))
            if index < len(hadiths) - 1:
                nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"nav_hadith:{book_key}:{index+1}"))
            if nav_buttons:
                markup.row(*nav_buttons)

            if edit and message_id:
                bot.edit_message_text(full_text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, full_text, reply_markup=markup)
        except Exception as e:
            print(f"[ERROR] Display hadith: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ أثناء عرض الحديث.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav_hadith:"))
    def navigate_hadiths(call):
        try:
            _, book_key, index = call.data.split(":")
            send_hadith(call.message.chat.id, book_key, int(index), call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR] Navigate hadith: {e}")
            bot.answer_callback_query(call.id, "❌ تعذر التنقل بين الأحاديث")

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
