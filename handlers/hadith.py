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
BOOKS = {}  # سيُملأ لاحقًا

def fetch_books():
    global BOOKS
    try:
        res = requests.get(f"{API_BASE}/books", headers=HEADERS, params={"apiKey": API_KEY, "language": "arabic"}, timeout=10)
        res.raise_for_status()
        data = res.json()
        BOOKS = {book["bookSlug"]: book["bookName"] for book in data["books"]["data"]}
    except Exception as e:
        print(f"[ERROR] Failed to load books: {e}")

def show_hadith_menu(bot, msg):
    if not BOOKS:
        fetch_books()
    markup = InlineKeyboardMarkup()
    for slug, name in BOOKS.items():
        markup.add(InlineKeyboardButton(f"📚 {name}", callback_data=f"hadith_book:{slug}:1"))
    bot.send_message(msg.chat.id, "📖 اختر مصدر الحديث:", reply_markup=markup)

def register(bot):
    fetch_books()

    @bot.message_handler(commands=["hadith", "حديث"])
    def hadith_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def send_hadith(call):
        try:
            _, book_slug, page = call.data.split(":")
            page = int(page)
            res = requests.get(
                f"{API_BASE}/hadiths",
                headers=HEADERS,
                params={
                    "apiKey": API_KEY,
                    "language": "arabic",
                    "book": book_slug,
                    "page": page,
                    "limit": 1
                },
                timeout=10
            )
            res.raise_for_status()
            data = res.json()
            hadith = data["hadiths"]["data"][0]
            number = hadith["hadithNumber"]
            text = hadith["hadithArabic"]

            message = f"{BOOKS.get(book_slug, '📕 حديث')}\n\n🆔 الحديث رقم {number}\n\n{text}"
            markup = InlineKeyboardMarkup()

            # أزرار التنقل
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"hadith_book:{book_slug}:{page - 1}"))
            if data["hadiths"]["next_page_url"]:
                nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"hadith_book:{book_slug}:{page + 1}"))
            if nav_buttons:
                markup.row(*nav_buttons)

            markup.add(
                InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{book_slug}:{number}"),
                InlineKeyboardButton("🏠 العودة", callback_data="hadith_back_to_menu")
            )

            bot.edit_message_text(message, call.message.chat.id, call.message.message_id, reply_markup=markup)

        except Exception as e:
            print(f"[ERROR] send_hadith: {e}")
            bot.send_message(call.message.chat.id, "❌ حدث خطأ أثناء جلب الحديث.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def add_to_favorites(call):
        try:
            _, book_slug, number = call.data.split(":")
            content = f"{BOOKS.get(book_slug, '📘 حديث')} - رقم {number}"
            add_to_fav(call.from_user.id, "hadith", content)
            bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")
        except Exception as e:
            print(f"[ERROR] add_to_favorites: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_back_to_menu")
    def back_to_menu(call):
        show_hadith_menu(bot, call.message)
