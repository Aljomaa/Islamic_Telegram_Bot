import requests
import random
import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
from utils.menu import show_main_menu

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE = "https://api.alquran.cloud/v1"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

RECITERS = {
    "مشاري العفاسي": "Alafasy",
    "ماهر المعيقلي": "MaherAlMuaiqly",
    "ياسر الدوسري": "Yasser_Ad-Dussary",
    "عبد الباسط مجود": "Abdul_Basit_Mujawwad",
    "ناصر القطامي": "Nasser_Alqatami",
    "أحمد العجمي": "Ahmed_ibn_Ali_al-Ajamy"
}

SURAH_NAMES = []

# Load Surah Names for name-based search
try:
    response = requests.get(f"{API_BASE}/surah", headers=HEADERS)
    if response.status_code == 200:
        SURAH_NAMES = [(s['englishName'].lower(), s['number']) for s in response.json()['data']]
except:
    pass

def register(bot):
    @bot.message_handler(commands=['quran', 'قرآن'])
    def cmd_quran(msg):
        show_main_quran_menu(bot, msg.chat.id, msg.message_id if hasattr(msg, 'message_id') else None)

    @bot.callback_query_handler(func=lambda call: call.data == "browse_quran")
    def ask_surah_number(call):
        bot.edit_message_text("📖 الرجاء إدخال رقم أو اسم السورة:", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, process_surah_input)

    def process_surah_input(msg):
        user_input = msg.text.strip()
        if user_input.isdigit():
            surah_num = int(user_input)
        else:
            name_match = next((num for name, num in SURAH_NAMES if user_input.lower() in name), None)
            surah_num = name_match

        if surah_num and 1 <= surah_num <= 114:
            send_surah_info(msg.chat.id, surah_num)
        else:
            bot.send_message(msg.chat.id, "❌ لم يتم العثور على السورة المطلوبة.")

    @bot.callback_query_handler(func=lambda call: call.data == "random_ayah")
    def send_random_verse(call):
        try:
            surah_num = random.randint(1, 114)
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar", headers=HEADERS, timeout=10)
            verses = res.json()['data']['ayahs']
            ayah = random.choice(verses)
            send_verse_details(bot, call.message.chat.id, surah_num, ayah['numberInSurah'], call.message.message_id, edit=True)
        except Exception as e:
            logger.error(f"[ERROR] Random Ayah: {e}")
            bot.edit_message_text("❌ تعذر جلب آية", call.message.chat.id, call.message.message_id)

    def send_surah_info(chat_id, surah_num, message_id=None):
        try:
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar", headers=HEADERS)
            data = res.json()['data']
            ayah = data['ayahs'][0]
            text = f"📖 سورة {data['name']}\nعدد الآيات: {data['numberOfAyahs']}\n\nالآية 1:\n{ayah['text']}"

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("▶️ التالي", callback_data=f"nav_{surah_num}_2"),
                InlineKeyboardButton("🎧 استماع", callback_data=f"choose_reciter:{surah_num}:1"),
                InlineKeyboardButton("⭐ حفظ", callback_data=f"fav:{surah_num}:{ayah['numberInSurah']}")
            )
            markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))

            if message_id:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, text, reply_markup=markup)
        except Exception as e:
            logger.error(f"[ERROR] Surah Info: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ في عرض السورة")

    def send_verse_details(bot, chat_id, surah_num, ayah_num, message_id=None, edit=False):
        try:
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar", headers=HEADERS)
            verses = res.json()['data']['ayahs']
            ayah = next((a for a in verses if a['numberInSurah'] == int(ayah_num)), None)
            if not ayah:
                bot.send_message(chat_id, "❌ لم يتم العثور على الآية.")
                return

            text = f"📖 سورة {res.json()['data']['name']}\nالآية {ayah['numberInSurah']}:\n\n{ayah['text']}"

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🔁 آية أخرى", callback_data="random_ayah"),
                InlineKeyboardButton("🎧 استماع", callback_data=f"choose_reciter:{surah_num}:{ayah['numberInSurah']}"),
                InlineKeyboardButton("⭐ حفظ", callback_data=f"fav:{surah_num}:{ayah['numberInSurah']}")
            )

            nav = []
            if ayah['numberInSurah'] > 1:
                nav.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"nav_{surah_num}_{ayah['numberInSurah'] - 1}"))
            if ayah['numberInSurah'] < len(verses):
                nav.append(InlineKeyboardButton("▶️ التالية", callback_data=f"nav_{surah_num}_{ayah['numberInSurah'] + 1}"))
            if nav:
                markup.row(*nav)

            markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))

            if edit and message_id:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, text, reply_markup=markup)
        except Exception as e:
            logger.error(f"[ERROR] Verse Details: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ في عرض الآية")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("choose_reciter:"))
    def choose_reciter(call):
        _, surah, ayah = call.data.split(":")
        markup = InlineKeyboardMarkup(row_width=1)
        for name, code in RECITERS.items():
            markup.add(InlineKeyboardButton(name, callback_data=f"recite:{code}:{surah}:{ayah}"))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data=f"nav_{surah}_{ayah}"))
        bot.edit_message_text("🎧 اختر القارئ للاستماع إلى الآية:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("recite:"))
    def send_audio(call):
        _, reciter, surah, ayah = call.data.split(":")
        try:
            audio_url = f"https://www.everyayah.com/data/{reciter}/{int(surah):03d}{int(ayah):03d}.mp3"
            bot.send_audio(call.message.chat.id, audio_url)
        except Exception as e:
            logger.error(f"[ERROR] Audio: {e}")
            bot.send_message(call.message.chat.id, "❌ فشل في تشغيل الصوت")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav:"))
    def add_to_favorites(call):
        try:
            _, surah, ayah = call.data.split(":")
            res = requests.get(f"{API_BASE}/surah/{surah}/ar", headers=HEADERS)
            data = res.json()['data']
            verse = next((v for v in data['ayahs'] if v['numberInSurah'] == int(ayah)), None)
            if verse:
                content = f"سورة {data['name']} - آية {ayah}:\n\n{verse['text']}"
                add_to_fav(call.from_user.id, "ayah", content)
                bot.answer_callback_query(call.id, "✅ تم حفظ الآية في المفضلة.")
            else:
                bot.answer_callback_query(call.id, "❌ لم يتم العثور على الآية.")
        except Exception as e:
            logger.error(f"[ERROR] Fav Ayah: {e}")
            bot.answer_callback_query(call.id, "❌ فشل الحفظ.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav_"))
    def nav_verses(call):
        try:
            _, surah, ayah = call.data.split("_")
            send_verse_details(bot, call.message.chat.id, surah, ayah, call.message.message_id, edit=True)
        except Exception as e:
            logger.error(f"[ERROR] Navigation: {e}")
            bot.answer_callback_query(call.id, "❌ فشل التنقل.")

    @bot.callback_query_handler(func=lambda call: call.data == "main_menu")
    def return_home(call):
        show_main_menu(bot, call.message)

# ✅ القائمة الرئيسية للقرآن

def show_main_quran_menu(bot, chat_id, message_id=None):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📖 تصفح السور", callback_data="browse_quran"),
        InlineKeyboardButton("🕋 آية عشوائية", callback_data="random_ayah")
    )
    markup.add(InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="main_menu"))

    if message_id:
        bot.edit_message_text("🌙 القرآن الكريم - اختر أحد الخيارات:", chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, "🌙 القرآن الكريم - اختر أحد الخيارات:", reply_markup=markup)

def handle_callbacks(bot):
    pass
            
