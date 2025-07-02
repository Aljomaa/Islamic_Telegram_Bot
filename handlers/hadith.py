import os
import random
import requests
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

def show_hadith_menu(bot, msg_or_call):
    markup = InlineKeyboardMarkup(row_width=2)
    for slug, name in BOOKS.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"hadith_book:{slug}"))
    markup.add(InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="back_to_main"))

    chat_id = msg_or_call.chat.id
    msg_id = msg_or_call.message_id
    bot.edit_message_text("📚 اختر مصدر الحديث:", chat_id, msg_id, reply_markup=markup)

def register(bot):
    @bot.message_handler(commands=['hadith'])
    def hadith_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def select_book(call):
        slug = call.data.split(":")[1]
        user_sessions[call.from_user.id] = {"book": slug}
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📖 حديث عشوائي", callback_data="hadith_random"),
            InlineKeyboardButton("📅 حديث برقم", callback_data="hadith_by_number")
        )
        markup.add(InlineKeyboardButton("🔙 الرجوع للقائمة السابقة", callback_data="hadith_back_to_books"))
        markup.add(InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="back_to_main"))

        bot.edit_message_text("🕌 اختر طريقة عرض الحديث:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_random")
    def random_hadith(call):
        slug = user_sessions.get(call.from_user.id, {}).get("book")
        if not slug:
            return bot.answer_callback_query(call.id, "❌ لم يتم اختيار مصدر.")
        try:
            res = requests.get(f"{API_BASE}/books/{slug}/hadiths", headers=HEADERS, params={"apiKey": API_KEY, "language": "arabic", "page": 1})
            data = res.json()
            hadiths = data.get("hadiths", [])
            if not hadiths:
                return bot.send_message(call.message.chat.id, "❌ لا توجد أحاديث.")
            chosen = random.choice(hadiths)
            show_hadith(bot, call.message.chat.id, slug, chosen["hadithNumber"], call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR] random_hadith: {e}")
            bot.send_message(call.message.chat.id, "❌ تعذر عرض الحديث.")

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_by_number")
    def by_number(call):
        slug = user_sessions.get(call.from_user.id, {}).get("book")
        if not slug:
            return bot.answer_callback_query(call.id, "❌ لم يتم اختيار مصدر.")
        msg = bot.send_message(call.message.chat.id, "📩 أرسل رقم الحديث الذي تريد عرضه:")
        bot.register_next_step_handler(msg, handle_hadith_number)

    def handle_hadith_number(msg):
        slug = user_sessions.get(msg.from_user.id, {}).get("book")
        if not slug:
            return bot.send_message(msg.chat.id, "❌ لم يتم اختيار مصدر.")
        try:
            number = int(msg.text.strip())
            show_hadith(bot, msg.chat.id, slug, number)
        except ValueError:
            bot.send_message(msg.chat.id, "❌ الرقم غير صالح.")

    def fetch_hadith(slug, number):
        url = f"{API_BASE}/hadiths/{number}"
        params = {
            "apiKey": API_KEY,
            "book": slug,
            "language": "arabic"
        }
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        res.raise_for_status()
        return res.json().get("hadith", {})

    def show_hadith(bot, chat_id, slug, number, message_id=None, edit=False):
        try:
            hadith = fetch_hadith(slug, number)
            text = hadith.get("hadithArabic", "")
            if not text:
                return bot.send_message(chat_id, "❌ لا يوجد نص لهذا الحديث.")

            msg_text = f"{BOOKS.get(slug)}\n\n🆔 الحديث رقم {number}\n\n📜 {text}"

            markup = InlineKeyboardMarkup(row_width=2)
            if number > 1:
                markup.add(
                    InlineKeyboardButton("◀️ السابق", callback_data=f"hadith_nav:{slug}:{number-1}"),
                    InlineKeyboardButton("▶️ التالي", callback_data=f"hadith_nav:{slug}:{number+1}")
                )
            else:
                markup.add(InlineKeyboardButton("▶️ التالي", callback_data=f"hadith_nav:{slug}:{number+1}"))

            markup.add(InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{slug}:{number}"))
            markup.add(InlineKeyboardButton("🔙 الرجوع للقائمة السابقة", callback_data="hadith_back_to_books"))
            markup.add(InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="back_to_main"))

            if edit and message_id:
                bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, msg_text, reply_markup=markup)
        except Exception as e:
            print(f"[ERROR] show_hadith: {e}")
            bot.send_message(chat_id, "❌ تعذر عرض الحديث.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_nav:"))
    def navigate(call):
        try:
            _, slug, number = call.data.split(":")
            number = int(number)
            if number < 1:
                return bot.answer_callback_query(call.id, "❌ لا يوجد حديث قبل هذا.")
            show_hadith(bot, call.message.chat.id, slug, number, call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR] navigate: {e}")
            bot.answer_callback_query(call.id, "❌ تعذر التنقل.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def save_favorite(call):
        try:
            _, slug, number = call.data.split(":")
            number = int(number)
            hadith = fetch_hadith(slug, number)
            if not hadith:
                return bot.answer_callback_query(call.id, "❌ لم يتم العثور على الحديث.")
            content = {
                "type": "hadith",
                "book": BOOKS.get(slug, slug),
                "number": number,
                "text": hadith.get("hadithArabic", "")
            }
            add_to_fav(call.from_user.id, "hadith", content)
            bot.answer_callback_query(call.id, "✅ تم حفظ الحديث في المفضلة.")
        except Exception as e:
            print(f"[ERROR] fav_hadith: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_back_to_books")
    def back_books(call):
        show_hadith_menu(bot, call.message)

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
    def back_main(call):
        show_main_menu(bot, call.message)
