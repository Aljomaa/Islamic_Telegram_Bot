import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav

def register(bot):
    @bot.message_handler(commands=['hadith'])
    def ask_book(msg):
        markup = InlineKeyboardMarkup(row_width=2)
        books = {
            "bukhari": "📘 صحيح البخاري",
            "muslim": "📙 صحيح مسلم",
            "tirmidhi": "📕 الترمذي",
            "nasai": "📗 النسائي",
            "abudaud": "📒 أبي داوود"
        }
        for key, name in books.items():
            markup.add(InlineKeyboardButton(name, callback_data=f"hadith_book:{key}"))
        bot.send_message(msg.chat.id, "📚 اختر كتاب الحديث:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def ask_number(call):
        book = call.data.split(":")[1]
        bot.send_message(call.message.chat.id, f"📌 أرسل رقم الحديث من {book.upper()}")
        bot.register_next_step_handler(call.message, lambda m: fetch_hadith(m, book))

    def fetch_hadith(msg, book):
        try:
            number = int(msg.text.strip())
        except:
            bot.send_message(msg.chat.id, "❌ رقم الحديث غير صحيح.")
            return

        url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/{book}-arabic.json"
        res = requests.get(url)

        if res.status_code != 200:
            bot.send_message(msg.chat.id, "❌ حدث خطأ أثناء جلب الحديث.")
            return

        hadiths = res.json().get("hadiths", [])
        if number < 1 or number > len(hadiths):
            bot.send_message(msg.chat.id, f"❌ رقم الحديث خارج النطاق. يوجد {len(hadiths)} حديث فقط.")
            return

        text = hadiths[number - 1]["text"]
        full_text = f"📘 {book.upper()} - حديث رقم {number}\n\n{text}"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⭐ إضافة إلى المفضلة", callback_data=f"fav_hadith:{book}:{number}:{text[:30]}"))
        bot.send_message(msg.chat.id, full_text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def add_hadith_fav(call):
        _, book, number, partial = call.data.split(":", 3)
        content = f"{book.upper()} - حديث رقم {number}\n{partial}..."
        add_to_fav(call.from_user.id, "hadith", content)
        bot.answer_callback_query(call.id, "✅ تم إضافة الحديث إلى المفضلة.")