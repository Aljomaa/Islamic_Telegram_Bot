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

# 📜 عرض قائمة مصادر الحديث
def show_hadith_menu(bot, msg):
    markup = InlineKeyboardMarkup()
    for key, name in BOOKS.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"hadith_book:{key}"))
    bot.send_message(msg.chat.id, "📚 اختر مصدر الحديث:", reply_markup=markup)

def register(bot):
    @bot.message_handler(commands=['hadith', 'حديث'])
    def hadith_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def send_random_hadith(call):
        book_key = call.data.split(":")[1]
        url = f"{API_URL}/{book_key}.json"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                bot.send_message(call.message.chat.id, f"❌ فشل الاتصال ({res.status_code})")
                return

            data = res.json()
            hadiths = data.get("hadiths")
            if not hadiths:
                bot.send_message(call.message.chat.id, "❌ لا توجد أحاديث متوفرة في هذا المصدر.")
                return

            index = random.randint(0, len(hadiths) - 1)
            send_hadith(bot, call.message.chat.id, book_key, index, call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR] Hadith fetch: {e}")
            bot.send_message(call.message.chat.id, "❌ حدث خطأ أثناء جلب الحديث.")

    def send_hadith(bot, chat_id, book_key, index, message_id=None, edit=False):
        url = f"{API_URL}/{book_key}.json"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                bot.send_message(chat_id, f"❌ فشل تحميل المصدر ({res.status_code})")
                return

            data = res.json()
            hadiths = data.get("hadiths")
            if not hadiths or not (0 <= index < len(hadiths)):
                bot.send_message(chat_id, "❌ لا يوجد حديث بهذا الرقم")
                return

            hadith = hadiths[index]
            number = hadith.get("hadithNumber", index + 1)
            text = hadith.get("arab", "❌ لا يوجد نص لهذا الحديث")

            message = f"{BOOKS.get(book_key)}\n\n🆔 الحديث رقم {number}\n\n{text}"

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{book_key}:{number}")
            )

            nav_buttons = []
            if index > 0:
                nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"nav_hadith:{book_key}:{index - 1}"))
            if index < len(hadiths) - 1:
                nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"nav_hadith:{book_key}:{index + 1}"))
            if nav_buttons:
                markup.row(*nav_buttons)

            markup.add(InlineKeyboardButton("🏠 العودة للقائمة", callback_data="hadith_back_to_menu"))

            if edit and message_id:
                bot.edit_message_text(message, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, message, reply_markup=markup)
        except Exception as e:
            print(f"[ERROR] Display hadith: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ أثناء عرض الحديث.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav_hadith:"))
    def navigate_hadiths(call):
        try:
            _, book_key, index = call.data.split(":")
            send_hadith(bot, call.message.chat.id, book_key, int(index), call.message.message_id, edit=True)
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

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_back_to_menu")
    def back_to_main_menu(call):
        try:
            show_hadith_menu(bot, call.message)
        except Exception as e:
            print(f"[ERROR] Back to menu: {e}")
            bot.answer_callback_query(call.id, "❌ تعذر العودة للقائمة")
