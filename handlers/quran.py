import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import get_user_reciter, set_user_reciter, add_to_fav

API_BASE = "https://api.quran.gading.dev"

def register(bot):
    @bot.message_handler(commands=['quran'])
    def handle_quran(msg):
        bot.send_message(msg.chat.id, "📖 اكتب رقم السورة (من 1 إلى 114):")
        bot.register_next_step_handler(msg, process_surah)

    def process_surah(msg):
        try:
            surah_num = int(msg.text.strip())
            if not (1 <= surah_num <= 114):
                raise ValueError
        except:
            bot.send_message(msg.chat.id, "❌ رقم السورة غير صحيح.")
            return
        send_ayah(bot, msg.chat.id, surah_num, 1)

    def send_ayah(bot, chat_id, surah_num, ayah_num):
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

        msg_text = f"📖 {surah_name} - {ayah['number']['inSurah']}\n\n{text}"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("⏮️ السابق", callback_data=f"prev:{surah_num}:{ayah_num}"),
            InlineKeyboardButton("⏭️ التالي", callback_data=f"next:{surah_num}:{ayah_num}")
        )
        markup.row(
            InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_ayah:{ayah['number']['inQuran']}:{text[:40]}")
        )

        bot.send_message(chat_id, msg_text, reply_markup=markup)
        bot.send_audio(chat_id, audio_url)

    @bot.callback_query_handler(func=lambda call: call.data.startswith(("prev:", "next:")))
    def navigate_ayah(call):
        parts = call.data.split(":")
        direction, surah, ayah = parts[0], int(parts[1]), int(parts[2])
        new_ayah = ayah - 1 if direction == "prev" else ayah + 1
        send_ayah(bot, call.message.chat.id, surah, new_ayah)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_ayah:"))
    def add_to_favorites(call):
        parts = call.data.split(":", 2)
        ayah_number = parts[1]
        snippet = parts[2]
        content = f"آية رقم {ayah_number}\n{snippet}..."
        add_to_fav(call.from_user.id, "ayah", content)
        bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")
