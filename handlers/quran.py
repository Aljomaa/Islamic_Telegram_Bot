import requests
import random
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
        # استدعاء بيانات الميتا لجلب عدد سور وآيات لكل سورة
        try:
            meta_res = requests.get("https://api.quran.com/api/v4/chapters").json()
            chapters = meta_res.get("chapters", [])
            if not chapters:
                bot.send_message(message.chat.id, "❌ خطأ في جلب بيانات القرآن.")
                return
            # اختيار سورة عشوائية
            surah = random.choice(chapters)
            surah_id = surah["id"]
            # جلب عدد آيات السورة
            ayah_count = surah["verses_count"]
            # اختيار آية عشوائية في السورة
            ayah_num = random.randint(1, ayah_count)
            show_ayah(message.chat.id, surah_id, ayah_num)
        except Exception:
            bot.send_message(message.chat.id, "❌ خطأ في جلب الآية العشوائية.")

    def ask_surah(msg):
        bot.send_message(msg.chat.id, "📖 اكتب رقم السورة (1 إلى 114):")
        bot.register_next_step_handler(msg, browse_surah)

    def browse_surah(msg):
        try:
            surah = int(msg.text.strip())
            if not (1 <= surah <= 114):
                raise ValueError
        except:
            bot.send_message(msg.chat.id, "❌ رقم غير صحيح. حاول مرة أخرى.")
            return
        show_ayah(msg.chat.id, surah, 1)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav:"))
    def navigate_ayah(call):
        _, surah, ayah = call.data.split(":")
        show_ayah(call.message.chat.id, int(surah), int(ayah))

    def show_ayah(chat_id, surah, ayah):
        # جلب الآية من API
        try:
            res = requests.get(f"https://api.quran.com/api/v4/verses/by_key/{surah}:{ayah}?language=ar").json()
            data = res.get("verse", None)
            if not data:
                bot.send_message(chat_id, "❌ تعذر جلب الآية.")
                return
        except:
            bot.send_message(chat_id, "❌ تعذر جلب الآية.")
            return

        ayah_text = data["text_uthmani"]
        surah_name = data["chapter"]["name_arabic"]
        ayah_number = f"{surah}:{ayah}"

        # الصوت حسب القارئ المفضل
        reciter = get_user_reciter(chat_id) or "yasser"
        reciters = {
            "yasser": "Yasser_Ad-Dussary_64kbps",
            "mishary": "Mishari_Alafasy_64kbps",
            "basit": "Abdul_Basit_Mujawwad_64kbps",
            "massad": "Abdurrahmaan_As-Sudais_64kbps"
        }
        reciter_code = reciters.get(reciter, reciters["yasser"])
        audio_url = f"https://verses.quran.com/{reciter_code}/{surah}_{ayah}.mp3"

        text = f"📖 {surah_name} - آية {ayah}\n\n{ayah_text}"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("⏮️ السابق", callback_data=f"nav:{surah}:{ayah - 1 if ayah > 1 else 1}"),
            InlineKeyboardButton("⏭️ التالي", callback_data=f"nav:{surah}:{ayah + 1}")
        )
        markup.row(
            InlineKeyboardButton("🎙️ اختيار القارئ", callback_data="choose_reciter"),
            InlineKeyboardButton("⭐ إضافة إلى المفضلة", callback_data=f"fav_ayah:{ayah_text[:40]}")
        )

        bot.send_message(chat_id, text, reply_markup=markup)
        bot.send_audio(chat_id, audio_url)

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

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_ayah:"))
    def add_fav_ayah(call):
        content = call.data.split(":", 1)[1]
        add_to_fav(call.from_user.id, "ayah", content + "...")
        bot.answer_callback_query(call.id, "✅ تم حفظ الآية في المفضلة.")
