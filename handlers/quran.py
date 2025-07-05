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
    "مشاري العفاسي": "ar.alafasy",
    "ماهر المعيقلي": "ar.mahermuaiqly",
    "عبدالباسط مجود": "ar.abdulbasitmurattal",
    "ناصر القطامي": "ar.nasser-alqatami",
    "أحمد طالب حميد": "ar.ahmad-talib-hameed",
    "عبدالله الجهني": "ar.abdullah-juhany"
}

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

    @bot.callback_query_handler(func=lambda c: c.data == "browse_quran")
    def ask_surah(c):
        bot.edit_message_text("📖 أرسل اسم السورة أو رقمها (1‑114):",
                              c.message.chat.id, c.message.message_id)
        bot.register_next_step_handler(c.message, process_surah_input)

    def process_surah_input(msg):
        text = msg.text.strip()
        if text.isdigit() and 1 <= int(text) <= 114:
            surah = int(text)
        elif text in SURAH_NAMES:
            surah = SURAH_NAMES.index(text)+1
        else:
            bot.send_message(msg.chat.id, "❌ لم أجد السورة. حاول مجدداً.")
            return
        send_verse(msg.chat.id, surah, 1)

    @bot.callback_query_handler(func=lambda c: c.data == "random_ayah")
    def rnd(c):
        surah = random.randint(1,114)
        send_verse(c.message.chat.id, surah, None, edit_id=c.message.message_id)

    def send_verse(chat_id, surah, ayah_num=None, edit_id=None):
        try:
            url = f"{API_BASE}/surah/{surah}/quran-uthmani"
            res = requests.get(url, headers=HEADERS, timeout=10).json()
            verses = res['data']['ayahs']
            ayah = verses[0] if ayah_num is None else next(v for v in verses if v['numberInSurah']==ayah_num)
            text = f"📖 سورة {res['data']['name']} الآية {ayah['numberInSurah']}:\n\n{ayah['text']}"
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton("🎧 استماع", callback_data=f"choose_rec:{surah}:{ayah['numberInSurah']}"),
                InlineKeyboardButton("⭐ حفظ", callback_data=f"fav:{surah}:{ayah['numberInSurah']}"),
                InlineKeyboardButton("🔁 عشوائي", callback_data="random_ayah")
            )
            nav = []
            num = ayah['numberInSurah']
            if num>1: nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"nav:{surah}:{num-1}"))
            if num<len(verses): nav.append(InlineKeyboardButton("التالي ▶️", callback_data=f"nav:{surah}:{num+1}"))
            if nav: kb.row(*nav)
            kb.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))

            if edit_id:
                bot.edit_message_text(text, chat_id, edit_id, reply_markup=kb)
            else:
                bot.send_message(chat_id, text, reply_markup=kb)

        except Exception as e:
            logger.error(f"❌ verse error: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ، حاول ثانية.")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("nav:"))
    def nav(c):
        _, s, n = c.data.split(":")
        send_verse(c.message.chat.id, int(s), int(n), edit_id=c.message.message_id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("choose_rec:"))
    def choose_rec(c):
        _, s, n = c.data.split(":")
        kb = InlineKeyboardMarkup()
        for name, code in RECITERS.items():
            kb.add(InlineKeyboardButton(name, callback_data=f"play:{code}:{s}:{n}"))
        kb.add(InlineKeyboardButton("↩️ رجوع", callback_data=f"nav:{s}:{n}"))
        bot.edit_message_text("🎧 اختر قارئ:", c.message.chat.id, c.message.message_id, reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("play:"))
    def play(c):
        _, rec, s, n = c.data.split(":")
        try:
            res = requests.get(f"{API_BASE}/surah/{s}/{rec}", headers=HEADERS, timeout=10).json()
            verse = next(v for v in res['data']['ayahs'] if v['numberInSurah']==int(n))
            if verse.get("audio"):
                bot.send_audio(c.message.chat.id, verse['audio'])
            else:
                bot.answer_callback_query(c.id, "❌ لا يوجد صوت هنا.")
        except Exception as e:
            logger.error(f"❌ play error: {e}")
            bot.answer_callback_query(c.id, "❌ فشل في التشغيل.")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fav:"))
    def fav(c):
        _, s, n = c.data.split(":")
        res = requests.get(f"{API_BASE}/surah/{s}/quran-uthmani", headers=HEADERS).json()
        verse = next(v for v in res['data']['ayahs'] if v['numberInSurah']==int(n))
        add_to_fav(c.from_user.id, "ayah", f"سورة {res['data']['name']} آية {n}:\n{verse['text']}")
        bot.answer_callback_query(c.id, "✅ تم الحفظ.")

    @bot.callback_query_handler(func=lambda c: c.data=="main_menu")
    def mn(c):
        show_main_menu(bot, c.message)

def show_main_quran_menu(bot, chat_id, m_id=None):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📖 تصفح", callback_data="browse_quran"),
        InlineKeyboardButton("🕋 آية عشوائية", callback_data="random_ayah")
    )
    kb.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
    text = "🌙 القرآن الكريم:"
    if m_id: bot.edit_message_text(text, chat_id, m_id, reply_markup=kb)
    else: bot.send_message(chat_id, text, reply_markup=kb)
