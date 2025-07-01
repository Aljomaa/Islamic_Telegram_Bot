import os
import requests
import random
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav

load_dotenv()
API_KEY = os.getenv("HADITH_API_KEY")

API_BASE = "https://api.hadithapi.com/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

BOOKS = {
    "sahih-bukhari": "📘 صحيح البخاري",
    "sahih-muslim": "📗 صحيح مسلم",
    "sunan-abu-dawood": "📙 سنن أبي داود",
    "jami-at-tirmidhi": "📕 سنن الترمذي",
    "sunan-an-nasai": "📒 سنن النسائي"
}

def show_hadith_menu(bot, msg):
    markup = InlineKeyboardMarkup()
    for key, name in BOOKS.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"hadith_book:{key}"))
    bot.send_message(msg.chat.id, "📚 اختر مصدر الحديث:", reply_markup=markup)

def register(bot):
    @bot.message_handler(commands=["hadith", "حديث"])
    def hadith_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def load_random_hadith(call):
        book_key = call.data.split(":")[1]
        try:
            # جلب عدد الصفحات
            res = requests.get(f"{API_BASE}/books/{book_key}/hadiths?page=1", headers=HEADERS, timeout=10)
            res.raise_for_status()
            meta = res.json().get("data", {}).get("pagination", {})
            total_pages = meta.get("last_page", 1)
            
            # اختر صفحة عشوائية
            page = random.randint(1, total_pages)

            res = requests.get(f"{API_BASE}/books/{book_key}/hadiths?page={page}", headers=HEADERS, timeout=10)
            res.raise_for_status()
            hadiths = res.json().get("data", {}).get("hadiths", [])

            if not hadiths:
                bot.send_message(call.message.chat.id, "❌ لا توجد أحاديث في هذا الكتاب.")
                return

            index = random.randint(0, len(hadiths) - 1)
            show_hadith(bot, call.message.chat.id, book_key, page, hadiths, index, call.message.message_id, edit=True)

        except Exception as e:
            print(f"[ERROR] load_random_hadith: {e}")
            bot.send_message(call.message.chat.id, "❌ حدث خطأ أثناء جلب الحديث.")

    def show_hadith(bot, chat_id, book_key, page, hadiths, index, message_id=None, edit=False):
        try:
            hadith = hadiths[index]
            number = hadith.get("hadithNumber", index + 1)
            text = hadith.get("arabicText", "❌ لا يوجد نص.")

            message = f"{BOOKS.get(book_key, '📕 كتاب')} \n\n🆔 الحديث رقم {number}\n\n{text}"

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{book_key}:{number}"))

            nav = []
            if index > 0:
                nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"nav_hadith:{book_key}:{page}:{index - 1}"))
            if index < len(hadiths) - 1:
                nav.append(InlineKeyboardButton("▶️ التالي", callback_data=f"nav_hadith:{book_key}:{page}:{index + 1}"))
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
            _, book_key, page, index = call.data.split(":")
            page = int(page)
            index = int(index)
            res = requests.get(f"{API_BASE}/books/{book_key}/hadiths?page={page}", headers=HEADERS, timeout=10)
            hadiths = res.json().get("data", {}).get("hadiths", [])
            show_hadith(bot, call.message.chat.id, book_key, page, hadiths, index, call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR] navigate_hadith: {e}")
            bot.answer_callback_query(call.id, "❌ تعذر التنقل بين الأحاديث.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def add_to_favorites(call):
        try:
            _, book_key, number = call.data.split(":")
            content = f"{BOOKS.get(book_key)} - رقم {number}"
            add_to_fav(call.from_user.id, "hadith", content)
            bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")
        except Exception as e:
            print(f"[ERROR] add_to_favorites: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_back_to_menu")
    def back_to_menu(call):
        show_hadith_menu(bot, call.message)
