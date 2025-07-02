import os
import requests
import random
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from utils.db import add_to_fav
from utils.menu import show_main_menu

load_dotenv()
API_KEY = os.getenv("HADITH_API_KEY")
API_BASE = "https://www.hadithapi.com/public/api/hadiths"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

BOOKS = {
    "sahih-bukhari": "📘 صحيح البخاري",
    "sahih-muslim": "📗 صحيح مسلم",
    "al-tirmidhi": "📕 سنن الترمذي",
    "abu-dawood": "📙 سنن أبي داود",
    "ibn-e-majah": "📓 سنن ابن ماجه",
    "sunan-nasai": "📒 سنن النسائي",
    "mishkat": "📔 مشكاة المصابيح"
}

ITEMS_PER_PAGE = 25


def show_hadith_menu(bot, msg):
    markup = InlineKeyboardMarkup(row_width=2)
    for slug, name in BOOKS.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"hadith_book:{slug}:1"))
    markup.add(InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="back_to_main"))
    bot.edit_message_text("📚 اختر مصدر الحديث:", msg.chat.id, msg.message_id, reply_markup=markup)


def register(bot):
    @bot.message_handler(commands=['hadith', 'حديث'])
    def hadith_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def load_book(call):
        slug, page = call.data.split(":")[1:]
        fetch_and_show_hadith(bot, call.message.chat.id, slug, int(page), 0, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_page:"))
    def change_page(call):
        slug, page = call.data.split(":")[1:]
        fetch_and_show_hadith(bot, call.message.chat.id, slug, int(page), 0, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_nav:"))
    def navigate(call):
        slug, page, index = call.data.split(":")[1:]
        page = int(page)
        index = int(index)
        fetch_and_show_hadith(bot, call.message.chat.id, slug, page, index, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def save_to_fav(call):
        try:
            _, slug, number, text = call.data.split(":", 3)
            content = {
                "type": "hadith",
                "book": BOOKS.get(slug, slug),
                "number": int(number),
                "text": text
            }
            add_to_fav(call.from_user.id, "hadith", content)
            bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")
        except Exception as e:
            print(f"[ERROR] fav_hadith: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
    def back_main(call):
        show_main_menu(bot, call.message)


def fetch_and_show_hadith(bot, chat_id, slug, page, index, message_id):
    try:
        params = {
            "apiKey": API_KEY,
            "book": slug,
            "language": "arabic",
            "page": page,
            "limit": ITEMS_PER_PAGE
        }
        res = requests.get(API_BASE, headers=HEADERS, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        hadiths = data.get("hadiths", {}).get("data", [])

        if not hadiths:
            return bot.send_message(chat_id, "❌ لا توجد أحاديث.")

        index = max(0, min(index, len(hadiths) - 1))
        hadith = hadiths[index]
        number = hadith.get("hadithNumber")
        text = hadith.get("hadithArabic")

        msg = f"{BOOKS.get(slug)}\n\n🆔 الحديث رقم {number}\n\n{text}"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⭐ إضافة للمفضلة",
            callback_data=f"fav_hadith:{slug}:{number}:{text[:40]}"))

        nav_buttons = []
        if index > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"hadith_nav:{slug}:{page}:{index - 1}"))
        if index < len(hadiths) - 1:
            nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"hadith_nav:{slug}:{page}:{index + 1}"))
        if nav_buttons:
            markup.row(*nav_buttons)

        markup.row(
            InlineKeyboardButton("🔄 صفحة أخرى", callback_data=f"hadith_page:{slug}:{page + 1}"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")
        )

        bot.edit_message_text(msg, chat_id, message_id, reply_markup=markup)
    except Exception as e:
        print(f"[ERROR] fetch_and_show_hadith: {e}")
        bot.send_message(chat_id, "❌ تعذر تحميل الحديث.")
        
