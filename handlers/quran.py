import requests
import random
import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
from utils.menu import show_main_menu

# تهيئة اللوج
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE = "https://api.alquran.cloud/v1"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def register(bot):
    @bot.message_handler(commands=['quran', 'قرآن'])
    def cmd_quran(msg):
        show_main_quran_menu(bot, msg.chat.id, msg.message_id if hasattr(msg, 'message_id') else None)

    @bot.callback_query_handler(func=lambda call: call.data == "browse_quran")
    def ask_surah_number(call):
        try:
            bot.edit_message_text("📖 الرجاء إدخال رقم السورة (1-114):", call.message.chat.id, call.message.message_id)
            bot.register_next_step_handler(call.message, process_surah_number)
        except Exception as e:
            logger.error(f"Error asking surah number: {e}")
            bot.send_message(call.message.chat.id, "❌ حدث خطأ في طلب رقم السورة")

    def process_surah_number(msg):
        try:
            surah_num = int(msg.text.strip())
            if 1 <= surah_num <= 114:
                send_surah_info(msg.chat.id, surah_num)
            else:
                bot.send_message(msg.chat.id, "⚠️ رقم السورة يجب أن يكون بين 1 و114")
        except:
            bot.send_message(msg.chat.id, "❌ يرجى إدخال رقم صحيح")

    @bot.callback_query_handler(func=lambda call: call.data == "random_ayah")
    def send_random_verse(call):
        try:
            surah_num = random.randint(1, 114)
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy", headers=HEADERS, timeout=10)
            verses = res.json()['data']['ayahs']
            ayah = random.choice(verses)
            send_verse_details(call.message.chat.id, surah_num, ayah['numberInSurah'], call.message.message_id, edit=True)
        except Exception as e:
            logger.error(f"Error random ayah: {e}")
            bot.edit_message_text("❌ تعذر جلب آية", call.message.chat.id, call.message.message_id)

    def send_surah_info(chat_id, surah_num, message_id=None):
        try:
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy", headers=HEADERS, timeout=10)
            data = res.json()['data']
            first_ayah = data['ayahs'][0]
            text = f"📖 سورة {data['name']} ({data['englishName']})\nعدد الآيات: {data['numberOfAyahs']}\n\n"
            text += f"الآية 1:\n{first_ayah['text']}"

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("▶️ التالي", callback_data=f"nav_{surah_num}_2"),
                InlineKeyboardButton("🎧 استماع", callback_data=f"listen_audio:{surah_num}:1"),
                InlineKeyboardButton("⭐ حفظ", callback_data=f"fav_{surah_num}_1")
            )
            markup.row(InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))

            if message_id:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, text, reply_markup=markup)
        except Exception as e:
            logger.error(f"Error surah info: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ في عرض السورة")

    def send_verse_details(chat_id, surah_num, ayah_num, message_id=None, edit=False):
        try:
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy", headers=HEADERS, timeout=10)
            verses = res.json()['data']['ayahs']
            ayah = next((a for a in verses if a['numberInSurah'] == int(ayah_num)), None)
            if not ayah:
                return bot.send_message(chat_id, "❌ الآية غير موجودة")

            text = f"📖 {res.json()['data']['name']}\nالآية {ayah['numberInSurah']}:\n\n{ayah['text']}"

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🔁 آية أخرى", callback_data="random_ayah"),
                InlineKeyboardButton("🎧 استماع", callback_data=f"listen_audio:{surah_num}:{ayah['numberInSurah']}"),
                InlineKeyboardButton("⭐ حفظ", callback_data=f"fav_{surah_num}_{ayah['numberInSurah']}")
            )

            nav = []
            if ayah['numberInSurah'] > 1:
                nav.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"nav_{surah_num}_{ayah['numberInSurah'] - 1}"))
            if ayah['numberInSurah'] < len(verses):
                nav.append(InlineKeyboardButton("▶️ التالية", callback_data=f"nav_{surah_num}_{ayah['numberInSurah'] + 1}"))
            if nav:
                markup.row(*nav)

            markup.row(InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))

            if edit and message_id:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, text, reply_markup=markup)
        except Exception as e:
            logger.error(f"Error verse details: {e}")
            bot.send_message(chat_id, "❌ تعذر عرض الآية")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("listen_audio:"))
    def play_audio(call):
        try:
            _, surah_num, ayah_num = call.data.split(":")
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy", headers=HEADERS, timeout=10)
            verses = res.json()['data']['ayahs']
            verse = next((v for v in verses if v['numberInSurah'] == int(ayah_num)), None)
            if verse and verse.get("audio"):
                bot.send_audio(call.message.chat.id, verse['audio'])
            else:
                bot.answer_callback_query(call.id, "❌ لا يوجد تلاوة صوتية")
        except:
            bot.answer_callback_query(call.id, "❌ خطأ في تشغيل الصوت")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_"))
    def add_to_favorites(call):
        try:
            _, surah_num, ayah_num = call.data.split("_")
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy", headers=HEADERS, timeout=10)
            data = res.json()['data']
            verse = next((v for v in data['ayahs'] if v['numberInSurah'] == int(ayah_num)), None)
            if verse:
                content = f"سورة {data['name']} - آية {ayah_num}:\n\n{verse['text']}"
                add_to_fav(call.from_user.id, "ayah", content)
                bot.answer_callback_query(call.id, "✅ تمت الإضافة إلى المفضلة")
            else:
                bot.answer_callback_query(call.id, "❌ لم يتم العثور على الآية")
        except:
            bot.answer_callback_query(call.id, "❌ فشل الحفظ")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav_"))
    def nav_verses(call):
        try:
            _, surah_num, ayah_num = call.data.split("_")
            send_verse_details(call.message.chat.id, surah_num, ayah_num, call.message.message_id, edit=True)
        except:
            bot.answer_callback_query(call.id, "❌ فشل التنقل")

    @bot.callback_query_handler(func=lambda call: call.data == "main_menu")
    def return_home(call):
        show_main_menu(bot, call.message)

# ✅ قائمة القرآن الرئيسية
def show_main_quran_menu(bot, chat_id, message_id=None):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📖 تصفح السور", callback_data="browse_quran"),
        InlineKeyboardButton("🕋 آية عشوائية", callback_data="random_ayah")
    )
    markup.row(
        InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="main_menu")
    )

    if message_id:
        bot.edit_message_text("🌙 القرآن الكريم - اختر أحد الخيارات:", chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, "🌙 القرآن الكريم - اختر أحد الخيارات:", reply_markup=markup)

# لا شيء إضافي حالياً
def handle_callbacks(bot):
    pass
