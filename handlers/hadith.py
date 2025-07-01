import os
import requests
import random
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from utils.db import add_to_fav

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

def show_hadith_menu(bot, msg):
    markup = InlineKeyboardMarkup(row_width=2)
    for slug, name in BOOKS.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"hadith_book:{slug}"))
    bot.send_message(msg.chat.id, "📚 اختر مصدر الحديث:", reply_markup=markup)

def register(bot):
    user_sessions = {}  # {chat_id: {'slug': ..., 'hadiths': [...], 'index': int, 'page': int}}

    @bot.message_handler(commands=['hadith', 'حديث'])
    def hadith_command(msg):
        show_hadith_menu(bot, msg)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("hadith_book:"))
    def select_book(call):
        slug = call.data.split(":")[1]
        page = 1
        try:
            hadiths = fetch_hadiths(slug, page)
            if not hadiths:
                bot.send_message(call.message.chat.id, "❌ لا توجد أحاديث في هذا الكتاب.")
                return
            user_sessions[call.message.chat.id] = {'slug': slug, 'hadiths': hadiths, 'index': 0, 'page': page}
            send_method_menu(bot, call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"[ERROR] load_hadiths: {e}")
            bot.send_message(call.message.chat.id, "❌ حدث خطأ أثناء تحميل الأحاديث.")

    def fetch_hadiths(slug, page=1):
        url = f"{API_BASE}/hadiths"
        params = {
            "apiKey": API_KEY,
            "book": slug,
            "language": "arabic",
            "limit": 25,
            "page": page
        }
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data['hadiths']['data']

    def send_method_menu(bot, chat_id, message_id):
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📖 حديث عشوائي", callback_data="random_hadith"),
            InlineKeyboardButton("🔢 حديث برقم", callback_data="get_by_number")
        )
        markup.add(
            InlineKeyboardButton("🔍 بحث بكلمة", callback_data="search_hadith"),
            InlineKeyboardButton("🏠 العودة للقائمة", callback_data="hadith_back_to_menu")
        )
        bot.edit_message_text("🛍 اختر طريقة عرض الحديث:", chat_id, message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "random_hadith")
    def random_hadith(call):
        session = user_sessions.get(call.message.chat.id)
        if not session:
            return show_hadith_menu(bot, call.message)
        index = random.randint(0, len(session['hadiths']) - 1)
        session['index'] = index
        show_hadith(bot, call.message.chat.id, session, call.message.message_id, edit=True)

    @bot.callback_query_handler(func=lambda call: call.data == "get_by_number")
    def ask_for_number(call):
        bot.send_message(call.message.chat.id, "📥 أرسل رقم الحديث الذي تريد عرضه:", reply_markup=ForceReply())

    @bot.message_handler(func=lambda msg: msg.reply_to_message and "أرسل رقم الحديث" in msg.reply_to_message.text)
    def get_by_number(msg):
        session = user_sessions.get(msg.chat.id)
        if not session:
            return show_hadith_menu(bot, msg)
        try:
            number = int(msg.text)
            slug = session['slug']
            page = (number - 1) // 25 + 1
            index = (number - 1) % 25
            hadiths = fetch_hadiths(slug, page)
            if not (0 <= index < len(hadiths)):
                return bot.send_message(msg.chat.id, "❌ الحديث غير موجود في هذه الصفحة.")
            user_sessions[msg.chat.id] = {'slug': slug, 'hadiths': hadiths, 'index': index, 'page': page}
            show_hadith(bot, msg.chat.id, user_sessions[msg.chat.id])
        except:
            bot.send_message(msg.chat.id, "❌ الرقم غير صحيح.")

    @bot.callback_query_handler(func=lambda call: call.data == "search_hadith")
    def ask_for_keyword(call):
        bot.send_message(call.message.chat.id, "🔍 أرسل الكلمة التي تريد البحث عنها في الأحاديث:", reply_markup=ForceReply())

    @bot.message_handler(func=lambda msg: msg.reply_to_message and "الكلمة التي تريد البحث" in msg.reply_to_message.text)
    def search_hadith(msg):
        keyword = msg.text
        try:
            url = f"{API_BASE}/hadiths/search"
            params = {
                "apiKey": API_KEY,
                "language": "arabic",
                "keyword": keyword
            }
            res = requests.get(url, headers=HEADERS, params=params, timeout=10)
            data = res.json()
            results = data['hadiths']['data']
            if not results:
                return bot.send_message(msg.chat.id, "❌ لا توجد نتائج.")
            slug = results[0]['book']['bookSlug']
            user_sessions[msg.chat.id] = {'slug': slug, 'hadiths': results, 'index': 0, 'page': 1}
            show_hadith(bot, msg.chat.id, user_sessions[msg.chat.id])
        except Exception as e:
            print(f"[ERROR] search_hadith: {e}")
            bot.send_message(msg.chat.id, "❌ فشل البحث.")

    def show_hadith(bot, chat_id, session, message_id=None, edit=False):
        try:
            index = session['index']
            slug = session['slug']
            hadith = session['hadiths'][index]
            number = hadith.get("hadithNumber", index + 1)
            text = hadith.get("hadithArabic", "❌ لا يوجد نص")

            msg = f"{BOOKS.get(slug)}\n\n🆔 الحديث رقم {number}\n\n{text}"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_hadith:{slug}:{number}"))

            nav = []
            if index > 0:
                nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"nav_hadith:{index - 1}"))
            if index < len(session['hadiths']) - 1:
                nav.append(InlineKeyboardButton("▶️ التالي", callback_data=f"nav_hadith:{index + 1}"))
            if nav:
                markup.row(*nav)
            markup.add(InlineKeyboardButton("🏠 العودة للقائمة", callback_data="hadith_back_to_menu"))

            if edit and message_id:
                bot.edit_message_text(msg, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, msg, reply_markup=markup)
        except Exception as e:
            print(f"[ERROR] show_hadith: {e}")
            bot.send_message(chat_id, "❌ تعذر عرض الحديث.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav_hadith:"))
    def navigate(call):
        try:
            new_index = int(call.data.split(":")[1])
            session = user_sessions.get(call.message.chat.id)
            if not session:
                return show_hadith_menu(bot, call.message)

            if not (0 <= new_index < len(session['hadiths'])):
                return bot.answer_callback_query(call.id, "❌ حديث غير موجود.")

            session['index'] = new_index
            show_hadith(bot, call.message.chat.id, session, call.message.message_id, edit=True)
        except Exception as e:
            print(f"[ERROR] navigate_hadith: {e}")
            bot.answer_callback_query(call.id, "❌ خطأ في التنقل.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_hadith:"))
    def add_to_favorites(call):
        try:
            _, slug, number = call.data.split(":")
            content = f"{BOOKS.get(slug)} - رقم {number}"
            add_to_fav(call.from_user.id, "hadith", content)
            bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")
        except Exception as e:
            print(f"[ERROR] add_to_fav: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")

    @bot.callback_query_handler(func=lambda call: call.data == "hadith_back_to_menu")
    def back_to_menu(call):
        show_hadith_menu(bot, call.message)
