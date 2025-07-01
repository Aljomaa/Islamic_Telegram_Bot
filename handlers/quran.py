import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
import random

API_BASE = "https://api.quran.gading.dev"

def register(bot):
    @bot.message_handler(commands=['quran'])
    def handle_quran(msg):
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("📖 تصفح السور", callback_data="browse_quran"),
            InlineKeyboardButton("🕋 آية من القرآن", callback_data="random_ayah")
        )
        bot.send_message(msg.chat.id, "اختر ما تود فعله:", reply_markup=markup)

def handle_callbacks(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "browse_quran")
    def ask_surah_number(call):
        bot.send_message(call.message.chat.id, "📖 اكتب رقم السورة (من 1 إلى 114):")
        bot.register_next_step_handler(call.message, lambda msg: send_ayah(bot, msg.chat.id, int(msg.text.strip()), 1, msg))

    @bot.callback_query_handler(func=lambda call: call.data == "random_ayah")
    def random_ayah(call):
        try:
            res = requests.get(f"{API_BASE}/surah", timeout=10)
            res.raise_for_status()
            surahs = res.json()["data"]
            surah = random.choice(surahs)
            surah_num = int(surah["number"])
            total_ayahs = surah["numberOfVerses"]
            ayah_num = random.randint(1, total_ayahs)
            send_ayah(bot, call.message.chat.id, surah_num, ayah_num, call.message, edit=True)
        except:
            bot.send_message(call.message.chat.id, "❌ فشل في جلب آية عشوائية. حاول لاحقاً.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_ayah:"))
    def add_to_favorites(call):
        parts = call.data.split(":", 2)
        ayah_number = parts[1]
        snippet = parts[2]
        content = f"آية رقم {ayah_number}\n{snippet}..."
        add_to_fav(call.from_user.id, "ayah", content)
        bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")

def send_ayah(bot, chat_id, surah_num, ayah_num, message=None, edit=False):
    try:
        res = requests.get(f"{API_BASE}/surah/{surah_num}/{ayah_num}", timeout=10)
        data = res.json()
        if data["status"] != "OK":
            raise Exception("Bad response")
    except:
        bot.send_message(chat_id, "❌ تعذر جلب الآية.")
        return

    ayah = data["data"]
    surah_name = ayah["surah"]["name"]["short"]
    text = ayah["text"]["arab"]
    audio_url = ayah["audio"]["primary"]

    msg_text = f"📖 {surah_name} - الآية {ayah['number']['inSurah']}\n\n{text}"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔁 آية عشوائية أخرى", callback_data="random_ayah"))
    markup.add(InlineKeyboardButton("⭐ أضف إلى المفضلة", callback_data=f"fav_ayah:{ayah['number']['inQuran']}:{text[:40]}"))

    if edit and message:
        bot.edit_message_text(msg_text, chat_id, message.message_id, reply_markup=markup)
        bot.send_audio(chat_id, audio_url)
    else:
        bot.send_message(chat_id, msg_text, reply_markup=markup)
        bot.send_audio(chat_id, audio_url)
