import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import HADITH_API_KEY
from utils.db import add_to_fav
from utils.menu import show_main_menu

BASE_URL = "https://www.hadithapi.com/public/api"

headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
}

params_base = {
    "apiKey": HADITH_API_KEY,
    "language": "arabic"
}

def register(bot):
    @bot.message_handler(commands=['hadith'])
    def show_hadith_menu_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith:"))
    def handle_callback(call):
        bot.answer_callback_query(call.id)
        data = call.data.split(":")
        action = data[1]

        if action == "menu":
            show_hadith_menu(bot, call.message)

        elif action == "books":
            show_books(bot, call.message)

        elif action == "book":
            book_id = data[2]
            book_name = data[3]
            show_book_options(bot, call.message, book_id, book_name)

        elif action == "random":
            book_id = data[2]
            send_random_hadith(bot, call.message, book_id)

        elif action == "bynumber":
            book_id = data[2]
            msg = bot.send_message(call.message.chat.id, "📃 أدخل رقم الحديث:")
            bot.register_next_step_handler(msg, lambda m: send_hadith_by_number(bot, m, book_id))

        elif action == "fav":
            text = call.message.text
            user_id = call.from_user.id
            add_to_fav(user_id, text)
            bot.answer_callback_query(call.id, "✔️ تم حفظ الحديث في المفضلة")

def show_hadith_menu(bot, msg):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📙 عرض الكتب", callback_data="hadith:books")
    )
    bot.send_message(msg.chat.id, "اختر كتابًا للحديث:", reply_markup=markup)

def show_books(bot, msg):
    try:
        res = requests.get(f"{BASE_URL}/books", params=params_base, headers=headers)
        books = res.json().get("books", [])
        markup = InlineKeyboardMarkup(row_width=2)
        for book in books:
            name_ar = arabic_book_name(book['bookName'])
            markup.add(InlineKeyboardButton(f"📘 {name_ar}", callback_data=f"hadith:book:{book['id']}:{book['bookName']}"))
        markup.add(InlineKeyboardButton("⬅️ العودة", callback_data="hadith:menu"))
        bot.edit_message_text("اختر كتاب الحديث:", msg.chat.id, msg.message_id, reply_markup=markup)
    except Exception:
        bot.send_message(msg.chat.id, "⚠️ خطأ في جلب الكتب")

def arabic_book_name(english_name):
    names = {
        "Sahih Bukhari": "صحيح البخاري",
        "Sahih Muslim": "صحيح مسلم",
        "Jami' Al-Tirmidhi": "جامع الترمذي",
        "Sunan Abu Dawood": "سنن أبي داود",
        "Sunan Ibn-e-Majah": "سنن ابن ماجه",
        "Sunan An-Nasa`i": "سنن النسائي",
        "Mishkat Al-Masabih": "مشكاة المصابيح",
        "Musnad Ahmad": "مسند أحمد",
        "Al-Silsila Sahiha": "السلسلة الصحيحة",
    }
    return names.get(english_name, english_name)

def show_book_options(bot, msg, book_id, book_name):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎲 حديث عشوائي", callback_data=f"hadith:random:{book_id}"),
        InlineKeyboardButton("📓 حديث برقم", callback_data=f"hadith:bynumber:{book_id}")
    )
    markup.add(InlineKeyboardButton("⬅️ العودة", callback_data="hadith:books"))
    bot.edit_message_text("ماذا تريد فعله بهذا الكتاب؟", msg.chat.id, msg.message_id, reply_markup=markup)

def send_random_hadith(bot, msg, book_id):
    try:
        res = requests.get(f"{BASE_URL}/hadiths", params={**params_base, "book": book_id, "page": 1}, headers=headers)
        hadiths = res.json().get("hadiths", {}).get("data", [])
        import random
        if hadiths:
            hadith = random.choice(hadiths)
            send_hadith(bot, msg, hadith)
        else:
            bot.edit_message_text("❌ لم يتم العثور على حديث.", msg.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ خطأ: {e}", msg.chat.id, msg.message_id)

def send_hadith_by_number(bot, msg, book_id):
    try:
        number = int(msg.text.strip())
        page = (number - 1) // 25 + 1
        index = (number - 1) % 25
        res = requests.get(f"{BASE_URL}/hadiths", params={**params_base, "book": book_id, "page": page}, headers=headers)
        hadiths = res.json().get("hadiths", {}).get("data", [])
        if index < len(hadiths):
            hadith = hadiths[index]
            send_hadith(bot, msg, hadith)
        else:
            bot.send_message(msg.chat.id, "⚠️ لم يتم العثور على الحديث.")
    except Exception as e:
        bot.send_message(msg.chat.id, f"⚠️ خطأ: {e}")

def send_hadith(bot, msg, hadith):
    text = f"حديث رقم {hadith['id']}\n\n{hadith['hadithArabic']}"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📌 إضافة للمفضلة", callback_data="hadith:fav"))
    markup.add(InlineKeyboardButton("⬅️ العودة", callback_data="hadith:books"))
    try:
        bot.edit_message_text(text, msg.chat.id, msg.message_id, reply_markup=markup)
    except:
        bot.send_message(msg.chat.id, text, reply_markup=markup)
            
