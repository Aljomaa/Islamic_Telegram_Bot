import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import get_user_reciter, set_user_reciter, add_to_fav

def register(bot):

    @bot.message_handler(commands=['ayah'])
    def ayah_menu(msg):
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🎲 آية عشوائية", callback_data="random_ayah"),
            InlineKeyboardButton("📚 تصفح القرآن", callback_data="browse_quran")
        )
        bot.send_message(msg.chat.id, "📖 اختر ما تود القيام به:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data in ["random_ayah", "browse_quran"])
    def handle_choice(call):
        if call.data == "random_ayah":
            send_random_ayah(call.message)
        elif call.data == "browse_quran":
            ask_surah(call.message)

    def send_random_ayah(message):
        try:
            res = requests.get("https://api.alquran.cloud/v1/ayah/random/ar", timeout=10)
            res.raise_for_status()
            data = res.json()
            if data["status"] != "OK":
                bot.send_message(message.chat.id, "❌ فشل في جلب آية عشوائية.")
                return

            ayah_data = data["data"]
            ayah_text = ayah_data["text"]
            surah_name = ayah_data["surah"]["englishName"]
            ayah_number = f"{ayah_data['surah']['number']}:{ayah_data['numberInSurah']}"

            text = f"📖 {surah_name} - {ayah_number}\n\n{ayah_text}"

            # تحضير صوت الآية
            reciter = get_user_reciter(message.from_user.id) or "yasser"
            reciters = {
                "yasser": "Yasser_Ad-Dussary_64kbps",
                "mishary": "Mishari_Alafasy_64kbps",
                "basit": "Abdul_Basit_Mujawwad_64kbps",
                "massad": "Abdurrahmaan_As-Sudais_64kbps"
            }
            reciter_code = reciters.get(reciter, reciters["yasser"])
            audio_url = f"https://verses.quran.com/{reciter_code}/{ayah_data['surah']['number']}_{ayah_data['numberInSurah']}.mp3"

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("📖 تفسير الآية", callback_data=f"tafsir:{ayah_number}"),
                InlineKeyboardButton("🎙️ اختيار القارئ", callback_data="choose_reciter")
            )
            markup.row(
                InlineKeyboardButton("🔁 آية أخرى", callback_data="random_ayah"),
                InlineKeyboardButton("⭐ إضافة إلى المفضلة", callback_data=f"fav_ayah:{ayah_text[:40]}")
            )

            bot.send_message(message.chat.id, text, reply_markup=markup)
            bot.send_audio(message.chat.id, audio_url)

        except Exception:
            bot.send_message(message.chat.id, "❌ فشل في جلب آية عشوائية. حاول لاحقاً.")

    @bot.callback_query_handler(func=lambda call: call.data == "choose_reciter")
    def choose_reciter(call):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🎧 ياسر الدوسري", callback_data="reciter:yasser"),
            InlineKeyboardButton("🎧 مشاري العفاسي", callback_data="reciter:mishary"),
            InlineKeyboardButton("🎧 عبد الباسط", callback_data="reciter:basit"),
            InlineKeyboardButton("🎧 عبد الرحمن مسعد", callback_data="reciter:massad")
        )
        bot.edit_message_text("🎙️ اختر القارئ المفضل:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reciter:"))
    def save_reciter(call):
        reciter_key = call.data.split(":")[1]
        set_user_reciter(call.from_user.id, reciter_key)
        bot.answer_callback_query(call.id, "✅ تم حفظ القارئ المفضل.")
        bot.edit_message_text("✅ تم تحديث القارئ المفضل بنجاح.", call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("tafsir:"))
    def tafsir(call):
        ayah_key = call.data.split(":")[1]
        try:
            tafsir_res = requests.get(f"https://api.quran.com/v4/tafsirs/131/verse/{ayah_key}", timeout=10)
            tafsir_res.raise_for_status()
            tafsir_data = tafsir_res.json()
            tafsir_text = tafsir_data.get("text") or "❌ لا يوجد تفسير."
        except:
            tafsir_text = "❌ تعذر جلب التفسير حالياً."
        bot.send_message(call.message.chat.id, f"📖 تفسير الآية {ayah_key}:\n\n{tafsir_text}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_ayah:"))
    def add_fav_ayah(call):
        content = call.data.split(":", 1)[1]
        add_to_fav(call.from_user.id, "ayah", content)
        bot.answer_callback_query(call.id, "✅ تم حفظ الآية في المفضلة.")

    def ask_surah(msg):
        bot.send_message(msg.chat.id, "📖 اكتب رقم السورة (1 إلى 114):")
        bot.register_next_step_handler(msg, browse_surah)

    def browse_surah(msg):
        try:
            surah = int(msg.text.strip())
            if not (1 <= surah <= 114):
                raise ValueError
        except:
            bot.send_message(msg.chat.id, "❌ رقم غير صحيح.")
            return
        show_ayah(msg.chat.id, surah, 1)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav:"))
    def navigate_ayah(call):
        _, surah, ayah = call.data.split(":")
        show_ayah(call.message.chat.id, int(surah), int(ayah))

    def show_ayah(chat_id, surah, ayah):
        try:
            res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar", timeout=10)
            res.raise_for_status()
            data = res.json()
        except:
            bot.send_message(chat_id, "❌ تعذر جلب الآية.")
            return

        if data["status"] != "OK":
            bot.send_message(chat_id, "❌ تعذر جلب الآية.")
            return

        ayah_data = data["data"]
        text = f"📖 {ayah_data['surah']['name']} - {ayah_data['numberInSurah']}\n\n{ayah_data['text']}"

        reciter = get_user_reciter(chat_id) or "yasser"
        reciters = {
            "yasser": "Yasser_Ad-Dussary_64kbps",
            "mishary": "Mishari_Alafasy_64kbps",
            "basit": "Abdul_Basit_Mujawwad_64kbps",
            "massad": "Abdurrahmaan_As-Sudais_64kbps"
        }
        reciter_code = reciters.get(reciter, reciters["yasser"])
        audio_url = f"https://verses.quran.com/{reciter_code}/{surah}_{ayah}.mp3"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("⏮️ السابق", callback_data=f"nav:{surah}:{ayah - 1 if ayah > 1 else 1}"),
            InlineKeyboardButton("⏭️ التالي", callback_data=f"nav:{surah}:{ayah + 1}")
        )
        markup.row(
            InlineKeyboardButton("📖 تفسير الآية", callback_data=f"tafsir:{surah}:{ayah}"),
            InlineKeyboardButton("⭐ إضافة إلى المفضلة", callback_data=f"fav_ayah:{ayah_data['text'][:40]}")
        )

        bot.send_message(chat_id, text, reply_markup=markup)
        bot.send_audio(chat_id, audio_url)
