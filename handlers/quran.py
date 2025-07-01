import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav, get_user_reciter

def register(bot):
    @bot.message_handler(commands=['quran'])
    def show_surah_list(msg):
        res = requests.get("https://api.quran.gading.dev/surah")
        if res.status_code != 200:
            bot.send_message(msg.chat.id, "❌ تعذر جلب قائمة السور.")
            return

        surahs = res.json()["data"]
        markup = InlineKeyboardMarkup(row_width=2)
        for surah in surahs:
            markup.add(InlineKeyboardButton(
                f"{surah['number']}. {surah['name']['short']} ({surah['name']['transliteration']['ar']})",
                callback_data=f"quran_surah:{surah['number']}:1"
            ))
        bot.send_message(msg.chat.id, "📖 اختر السورة:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("quran_surah:"))
    def navigate_ayahs(call):
        parts = call.data.split(":")
        surah_num = int(parts[1])
        ayah_num = int(parts[2])

        res = requests.get(f"https://api.quran.gading.dev/surah/{surah_num}/{ayah_num}")
        if res.status_code != 200:
            bot.answer_callback_query(call.id, "❌ تعذر جلب الآية.")
            return

        ayah_data = res.json()["data"]
        text = f"📖 {ayah_data['surah']['name']['short']} - آية {ayah_data['number']['inSurah']}\n\n{ayah_data['text']['arab']}"

        reciter = get_user_reciter(call.from_user.id) or "yasser"
        reciters = {
            "yasser": "Yasser_Ad-Dussary_64kbps",
            "mishary": "Mishari_Alafasy_64kbps",
            "basit": "Abdul_Basit_Mujawwad_64kbps",
            "massad": "Abdurrahmaan_As-Sudais_64kbps"
        }
        reciter_code = reciters.get(reciter, reciters["yasser"])
        audio_url = f"https://verses.quran.com/{reciter_code}/{surah_num}_{ayah_num}.mp3"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("⏮️ السابق", callback_data=f"quran_surah:{surah_num}:{ayah_num - 1 if ayah_num > 1 else 1}"),
            InlineKeyboardButton("⏭️ التالي", callback_data=f"quran_surah:{surah_num}:{ayah_num + 1}")
        )
        markup.row(
            InlineKeyboardButton("⭐ أضف للمفضلة", callback_data=f"fav_quran:{ayah_data['text']['arab'][:40]}")
