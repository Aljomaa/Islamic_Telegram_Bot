import os
import requests
import random
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from utils.db import add_to_fav
from utils.menu import show_main_menu

load_dotenv()
API_KEY = os.getenv("HADITH_API_KEY")
API_BASE = "https://www.hadithapi.com/public/api"
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

user_sessions = {}

def show_hadith_menu(bot, msg):
    markup = InlineKeyboardMarkup(row_width=2)
    for slug, name in BOOKS.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"hadith_book:{slug}"))
    markup.add(InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="back_to_main"))
    bot.edit_message_text("📚 اختر مصدر الحديث:", msg.chat.id, msg.message_id, reply_markup=markup)

def fetch_hadith(slug, number):
    url = f"{API_BASE}/hadiths/{number}"
    params = {
        "apiKey": API_KEY,
        "book": slug,
        "language": "arabic"
    }
    res = requests.get(url, headers=HEADERS, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()
    return data.get("hadith", {})

def show_method_menu(bot, chat_id, slug, message_id):
    user_sessions[chat_id] = {"slug": slug}
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📖 حديث عشوائي", callback_data="random_hadith"),
        InlineKeyboardButton("🔢 حديث برقم", callback_data="get_by_number")
    )
    markup.add(InlineKeyboardButton("🔙 الرجوع للقائمة السابقة", callback_data="hadith_back_to_books"))
    markup.add(InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="back_to_main"))
    bot.edit_message_text("🕌 اختر طريقة عرض الحديث:", chat_id, message_id, reply_markup=markup)

def show_hadith(bot, chat_id, slug, number, message_id=None, edit=False):
    try:
        hadith = fetch_hadith(slug, number)
        text = hadith.get("hadithArabic", "")
        if not text:
            bot.send_message(chat_id, "❌ لا يوجد نص لهذا الحديث.")
            return

        msg_text = f"{BOOKS.get(slug)}\n\n🆔 الحديث رقم {number}\n\n{text}"
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{slug}:{number}")
        )
        nav = []
        if number > 1:
            nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"hadith_nav:{slug}:{number - 1}"))
        nav.append(InlineKeyboardButton("▶️ التالي", callback_data=f"hadith_nav:{slug}:{number + 1}"))
        markup.row(*nav)

        markup.add(InlineKeyboardButton("🔙 الرجوع للقائمة السابقة", callback_data="hadith_back_to_books"))
        markup.add(InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="back_to_main"))

        if edit and message_id:
            bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, msg_text, reply_markup=markup)
    except Exception as e:
        print(f"[ERROR show_hadith] {e}")
        bot.send_message(chat_id, "❌ تعذر عرض الحديث.")

def register(bot):
    @bot.message_handler(commands=['hadith', 'حديث'])
    def hadith_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def select_book(call):
        slug = call.data.split(":")[1]
        show_method_menu(bot, call.message.chat.id, slug, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "random_hadith")
    def handle_random(call):
        session = user_sessions.get(call.message.chat.id)
        if not session:
            return show_hadith_menu(bot, call.message)
        number = random.randint(1, 3000)
        show_hadith(bot, call.message.chat.id, session["slug"], number, call.message.message_id, edit=True)

    @bot.callback_query_handler(func=lambda call: call.data == "get_by_number")
    def handle_number_request(call):
        bot.send_message(call.message.chat.id, "📩 أرسل رقم الحديث الذي تريد عرضه:", reply_markup=ForceReply())

    @bot.message_handler(func=lambda msg: msg.reply_to_message and "أرسل رقم الحديث" in msg.reply_to_message.text)
    def handle_number_response(msg):
        session = user_sessions.get(msg.chat.id)
        if not session:
            return bot.send_message(msg.chat.id, "❌ لم يتم اختيار كتاب.")
        try:
            number = int(msg.text)
            show_hadith(bot, msg.chat.id, session["slug"], number)
        except:
            bot.send_message(msg.chat.id, "❌ رقم غير صالح.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_nav:"))
    def navigate(call):
        try:
            _, slug, number = call.data.split(":")
            number = int(number)
            if number < 1:
                return bot.answer_callback_query(call.id, "❌ لا يوجد حديث قبل هذا.")
            show_hadith(bot, call.message.chat.id, slug, number, call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR navigate] {e}")
            bot.answer_callback_query(call.id, "❌ خطأ في التنقل.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def save_favorite(call):
        try:
            _, slug, number = call.data.split(":")
            number = int(number)
            hadith = fetch_hadith(slug, number)
            content = {
                "type": "hadith",
                "book": BOOKS.get(slug),
                "number": number,
                "text": hadith.get("hadithArabic", "")
            }
            add_to_fav(call.from_user.id, "hadith", content)
            bot.answer_callback_query(call.id, "✅ تم حفظ الحديث في المفضلة.")
        except Exception as e:
            print(f"[ERROR fav_hadith] {e}")
            bot.answer_callback_query(call.id, "❌ فشل حفظ الحديث.")

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_back_to_books")
    def back_books(call):
        show_hadith_menu(bot, call.message)

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
    def back_main(call):
        show_main_menu(bot, call.message)
