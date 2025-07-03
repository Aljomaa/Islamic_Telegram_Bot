import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import HADITH_API_KEY
from utils.db import add_to_fav

BASE_URL = "https://www.hadithapi.com/public/api"
LANG = "arabic"

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
        elif action == "random":
            send_random_hadith(bot, call.message)
        elif action == "books":
            show_books(bot, call.message)
        elif action == "book":
            book_id = data[2]
            page = int(data[3]) if len(data) > 3 else 1
            get_hadiths_by_book(bot, call.message, book_id, page)
        elif action == "fav":
            hadith_text = call.message.text
            user_id = call.from_user.id
            add_to_fav(user_id, "hadith", hadith_text)
            bot.answer_callback_query(call.id, text="تمت الإضافة إلى المفضلة 💖", show_alert=False)

def show_hadith_menu(bot, message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📚 عرض الكتب", callback_data="hadith:books"),
        InlineKeyboardButton("🎲 حديث عشوائي", callback_data="hadith:random"),
    )
    bot.send_message(message.chat.id, "📖 اختر من القائمة التالية:", reply_markup=markup)

def send_random_hadith(bot, message):
    params = {
        "apiKey": HADITH_API_KEY,
        "language": LANG
    }
    try:
        res = requests.get(f"{BASE_URL}/hadiths/random", params=params)
        data = res.json()
        if res.status_code == 200 and "hadith" in data:
            hadith_text = data["hadith"]["hadithArabic"]
            send_hadith_with_buttons(bot, message.chat.id, hadith_text)
        else:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على حديث.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ خطأ: {e}")

def show_books(bot, message):
    params = {
        "apiKey": HADITH_API_KEY,
        "language": LANG
    }
    try:
        res = requests.get(f"{BASE_URL}/books", params=params)
        data = res.json()
        if res.status_code == 200 and "books" in data:
            markup = InlineKeyboardMarkup()
            for book in data["books"]:
                btn = InlineKeyboardButton(f"📘 {book['bookName']}", callback_data=f"hadith:book:{book['id']}:1")
                markup.add(btn)
            markup.add(InlineKeyboardButton("🔙 العودة", callback_data="hadith:menu"))
            bot.send_message(message.chat.id, "📚 اختر كتاب الحديث:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على الكتب.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ خطأ: {e}")

def get_hadiths_by_book(bot, message, book_id, page=1):
    params = {
        "apiKey": HADITH_API_KEY,
        "language": LANG,
        "book": book_id,
        "page": page,
        "limit": 25
    }
    try:
        res = requests.get(f"{BASE_URL}/hadiths", params=params)
        data = res.json()
        if res.status_code == 200 and "hadiths" in data and "data" in data["hadiths"]:
            hadiths = data["hadiths"]["data"]
            if not hadiths:
                bot.send_message(message.chat.id, "❌ لا توجد أحاديث في هذه الصفحة.")
                return

            for hadith in hadiths:
                hadith_text = hadith["hadithArabic"]
                send_hadith_with_buttons(bot, message.chat.id, hadith_text, book_id, page)
                break  # Show only one hadith per page (like browsing)

        else:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على أحاديث.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ خطأ: {e}")

def send_hadith_with_buttons(bot, chat_id, hadith_text, book_id=None, page=None):
    markup = InlineKeyboardMarkup()
    if book_id and page:
        prev_btn = InlineKeyboardButton("⬅️ السابق", callback_data=f"hadith:book:{book_id}:{page - 1}") if page > 1 else None
        next_btn = InlineKeyboardButton("➡️ التالي", callback_data=f"hadith:book:{book_id}:{page + 1}")
        if prev_btn:
            markup.add(prev_btn, next_btn)
        else:
            markup.add(next_btn)
    markup.add(
        InlineKeyboardButton("💖 أضف إلى المفضلة", callback_data="hadith:fav"),
        InlineKeyboardButton("🏠 العودة إلى القائمة", callback_data="hadith:menu")
    )
    bot.send_message(chat_id, hadith_text, reply_markup=markup)
