import requests
import random
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
        show_books(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith:"))
    def handle_callback(call):
        bot.answer_callback_query(call.id)
        data = call.data.split(":")
        action = data[1]

        if action == "menu":
            show_books(bot, call.message)

        elif action == "book":
            slug = data[2]
            show_book_options(bot, call.message, slug)

        elif action == "random":
            slug = data[2]
            send_random_hadith(bot, call.message, slug)

        elif action == "bynumber":
            slug = data[2]
            msg = bot.send_message(call.message.chat.id, "📃 أدخل رقم الحديث:")
            bot.register_next_step_handler(msg, lambda m: send_hadith_by_number(bot, m, slug))

        elif action == "fav":
            text = call.message.text
            user_id = call.from_user.id
            add_to_fav(user_id, text)
            bot.answer_callback_query(call.id, "✔️ تم حفظ الحديث في المفضلة")

        elif action == "nav":
            slug = data[2]
            page = int(data[3])
            index = int(data[4])
            send_hadith_by_index(bot, call.message, slug, page, index)

def show_books(bot, msg):
    try:
        res = requests.get(f"{BASE_URL}/books", params=params_base, headers=headers)
        books = res.json().get("books", [])
        markup = InlineKeyboardMarkup(row_width=2)
        for book in books:
            name_ar = arabic_book_name(book['bookName'])
            slug = book['bookSlug']
            markup.add(InlineKeyboardButton(f"📘 {name_ar}", callback_data=f"hadith:book:{slug}"))
        markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main:menu"))
        bot.edit_message_text("📚 اختر كتاب الحديث:", msg.chat.id, msg.message_id, reply_markup=markup)
    except:
        bot.edit_message_text("⚠️ خطأ في جلب الكتب.", msg.chat.id, msg.message_id)

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

def show_book_options(bot, msg, slug):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎲 حديث عشوائي", callback_data=f"hadith:random:{slug}"),
        InlineKeyboardButton("📓 حديث برقم", callback_data=f"hadith:bynumber:{slug}")
    )
    markup.add(
        InlineKeyboardButton("⬅️ العودة", callback_data="hadith:menu"),
        InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main:menu")
    )
    bot.edit_message_text("ماذا تريد فعله بهذا الكتاب؟", msg.chat.id, msg.message_id, reply_markup=markup)

def send_random_hadith(bot, msg, slug):
    try:
        res = requests.get(f"{BASE_URL}/hadiths", params={**params_base, "book": slug, "page": 1}, headers=headers)
        hadiths = res.json().get("hadiths", {}).get("data", [])
        if hadiths:
            hadith = random.choice(hadiths)
            index = hadiths.index(hadith)
            send_hadith(bot, msg, slug, 1, index, hadith)
        else:
            bot.edit_message_text("❌ لا توجد أحاديث في هذا الكتاب.", msg.chat.id, msg.message_id)
    except:
        bot.edit_message_text("⚠️ حدث خطأ أثناء جلب الحديث.", msg.chat.id, msg.message_id)

def send_hadith_by_number(bot, msg, slug):
    try:
        number = int(msg.text.strip())
        page = (number - 1) // 25 + 1
        index = (number - 1) % 25
        send_hadith_by_index(bot, msg, slug, page, index)
    except:
        bot.send_message(msg.chat.id, "⚠️ رقم الحديث غير صالح.")

def send_hadith_by_index(bot, msg, slug, page, index):
    try:
        res = requests.get(f"{BASE_URL}/hadiths", params={**params_base, "book": slug, "page": page}, headers=headers)
        hadiths = res.json().get("hadiths", {}).get("data", [])
        if index < len(hadiths):
            hadith = hadiths[index]
            send_hadith(bot, msg, slug, page, index, hadith)
        else:
            bot.edit_message_text("❌ لا توجد أحاديث في هذه الصفحة.", msg.chat.id, msg.message_id)
    except:
        bot.edit_message_text("⚠️ فشل في تحميل الحديث.", msg.chat.id, msg.message_id)

def send_hadith(bot, msg, slug, page, index, hadith):
    text = f"📖 *حديث رقم {hadith['id']}*

{hadith['hadithArabic']}"
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⬅️ السابق", callback_data=f"hadith:nav:{slug}:{page}:{max(0, index - 1)}"),
        InlineKeyboardButton("➡️ التالي", callback_data=f"hadith:nav:{slug}:{page}:{index + 1}")
    )
    markup.add(
        InlineKeyboardButton("📌 إضافة للمفضلة", callback_data="hadith:fav")
    )
    markup.add(
        InlineKeyboardButton("⬅️ العودة", callback_data="hadith:menu"),
        InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main:menu")
    )
    try:
        bot.edit_message_text(text, msg.chat.id, msg.message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(msg.chat.id, text, reply_markup=markup, parse_mode="Markdown")
            
