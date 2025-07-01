import requests
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav

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

    @bot.callback_query_handler(func=lambda call: call.data == "browse_quran")
    def ask_surah(call):
        bot.send_message(call.message.chat.id, "📖 أرسل رقم السورة (من 1 إلى 114):")
        bot.register_next_step_handler(call.message, lambda msg: send_ayah(msg.chat.id, int(msg.text.strip()), 1, msg))

    @bot.callback_query_handler(func=lambda call: call.data == "random_ayah")
    def random_ayah(call):
        try:
            surah_data = requests.get(f"{API_BASE}/surah", timeout=10).json()["data"]
            surah = random.choice(surah_data)
            surah_num = int(surah["number"])
            total_ayahs = surah["numberOfVerses"]
            ayah_num = random.randint(1, total_ayahs)
            send_ayah(call.message.chat.id, surah_num, ayah_num, call.message, edit=True)
        except:
            bot.send_message(call.message.chat.id, "❌ تعذر جلب آية عشوائية.")

    def send_ayah(chat_id, surah_num, ayah_num, message=None, edit=False):
        try:
            res = requests.get(f"{API_BASE}/surah/{surah_num}/{ayah_num}", timeout=10)
            data = res.json()
            if data["status"] != "OK":
                raise Exception("Bad response")
        except:
            bot.send_message(chat_id, "❌ فشل في جلب الآية.")
            return

        ayah = data["data"]
        surah_name = ayah["surah"]["name"]["short"]
        ayah_text = ayah["text"]["arab"]
        audio_url = ayah["audio"]["primary"]
        msg_text = f"📖 {surah_name} - الآية {ayah['number']['inSurah']}\n\n{ayah_text}"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔁 آية أخرى", callback_data="random_ayah"))
        markup.add(InlineKeyboardButton("⭐ أضف للمفضلة", callback_data=f"fav_ayah:{ayah['number']['inQuran']}:{ayah_text[:40]}"))

        if edit and message:
            try:
                bot.edit_message_text(msg_text, chat_id, message.message_id, reply_markup=markup)
            except:
                bot.send_message(chat_id, msg_text, reply_markup=markup)
            bot.send_audio(chat_id, audio_url)
        else:
            bot.send_message(chat_id, msg_text, reply_markup=markup)
            bot.send_audio(chat_id, audio_url)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_ayah:"))
    def add_to_favorites(call):
        _, ayah_number, snippet = call.data.split(":", 2)
        content = f"آية رقم {ayah_number}\n{snippet}..."
        add_to_fav(call.from_user.id, "ayah", content)
        bot.answer_callback_query(call.id, "✅ تم حفظ الآية في المفضلة.")
