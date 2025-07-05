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

# القراء المتاحين
RECITERS = {
    "مشاري العفاسي": "ar.alafasy",
    "ياسر الدوسري": "ar.yasserad-dossari",
    "عبدالباسط": "ar.abdulbasitmurattal",
    "ماهر المعيقلي": "ar.mahermuaiqly",
    "عبدالرحمن مسعد": "ar.abdurrahman-mesud"
}

# أسماء السور العربية
SURAH_NAMES = [
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال",
    "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء",
    "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء",
    "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر",
    "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية",
    "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر",
    "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة",
    "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج",
    "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ",
    "النازعات", "عبس", "التكوير", "الانفطار", "المطففين", "الانشقاق", "البروج",
    "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس", "الليل", "الضحى",
    "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات", "القارعة",
    "التكاثر", "العصر", "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون",
    "النصر", "المسد", "الإخلاص", "الفلق", "الناس"
]

def register(bot):
    @bot.message_handler(commands=['quran', 'قرآن'])
    def cmd_quran(msg):
        show_main_quran_menu(bot, msg.chat.id, msg.message_id if hasattr(msg, 'message_id') else None)

    @bot.callback_query_handler(func=lambda call: call.data == "browse_quran")
    def ask_surah_name_or_number(call):
        bot.edit_message_text("📖 أرسل اسم السورة أو رقمها (1 - 114):", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, process_surah_input)

    def process_surah_input(msg):
        text = msg.text.strip()
        if text.isdigit() and 1 <= int(text) <= 114:
            send_surah_info(msg.chat.id, int(text))
        elif text in SURAH_NAMES:
            send_surah_info(msg.chat.id, SURAH_NAMES.index(text) + 1)
        else:
            bot.send_message(msg.chat.id, "❌ لم يتم العثور على السورة، تحقق من الاسم أو الرقم.")

    @bot.callback_query_handler(func=lambda call: call.data == "random_ayah")
    def send_random_verse(call):
        try:
            surah_num = random.randint(1, 114)
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy", headers=HEADERS, timeout=10)
            verses = res.json()['data']['ayahs']
            ayah = random.choice(verses)
            send_verse_details(bot, call.message.chat.id, surah_num, ayah['numberInSurah'], call.message.message_id, edit=True)
        except Exception as e:
            logger.error(f"[ERROR] Random Ayah: {e}")
            bot.edit_message_text("❌ تعذر جلب آية", call.message.chat.id, call.message.message_id)

    def send_surah_info(chat_id, surah_num, message_id=None):
        try:
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy", headers=HEADERS)
            data = res.json()['data']
            ayah = data['ayahs'][0]
            text = f"📖 سورة {data['name']} ({data['englishName']})\nعدد الآيات: {data['numberOfAyahs']}\n\n"
            text += f"الآية 1:\n{ayah['text']}"

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
            res = requests.get(f"{API_BASE}/surah/{surah_num}/ar.alafasy", headers=HEADERS)
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
        markup = InlineKeyboardMarkup()
        for name in RECITERS:
            markup.add(InlineKeyboardButton(name, callback_data=f"play_audio:{RECITERS[name]}:{surah}:{ayah}"))
        markup.add(InlineKeyboardButton("↩️ رجوع", callback_data=f"nav_{surah}_{ayah}"))
        bot.edit_message_text("🎧 اختر القارئ للاستماع للآية:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("play_audio:"))
    def play_audio(call):
        _, reciter, surah, ayah = call.data.split(":")
        try:
            res = requests.get(f"{API_BASE}/surah/{surah}/{reciter}", headers=HEADERS)
            verses = res.json()['data']['ayahs']
            verse = next((v for v in verses if v['numberInSurah'] == int(ayah)), None)
            if verse and verse.get("audio"):
                bot.send_audio(call.message.chat.id, verse['audio'])
            else:
                bot.answer_callback_query(call.id, "❌ لا يوجد تلاوة صوتية")
        except Exception as e:
            logger.error(f"[ERROR] Audio: {e}")
            bot.answer_callback_query(call.id, "❌ خطأ في تشغيل الصوت")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav:"))
    def add_to_favorites(call):
        try:
            _, surah, ayah = call.data.split(":")
            res = requests.get(f"{API_BASE}/surah/{surah}/ar.alafasy", headers=HEADERS)
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

def show_main_quran_menu(bot, chat_id, message_id=None):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📖 تصفح السور", callback_data="browse_quran"),
        InlineKeyboardButton("🕋 آية عشوائية", callback_data="random_ayah")
    )
    markup.add(InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="main_menu"))

    text = "🌙 القرآن الكريم - اختر أحد الخيارات:"
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)
