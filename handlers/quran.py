import requests, random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import get_user_reciter, set_user_reciter, add_to_fav

def register(bot):
    @bot.message_handler(commands=['ayah'])
    def ayah_menu(msg):
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("📖 آية عشوائية", callback_data="random_ayah"),
            InlineKeyboardButton("📚 تصفح القرآن", callback_data="browse_quran")
        )
        bot.send_message(msg.chat.id, "📖 اختر ما تريد:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data in ["random_ayah", "browse_quran"])
    def handle_choice(c):
        if c.data == "random_ayah":
            send_random(c.message)
        else:
            ask_surah(c.message)

    def send_random(message):
        # 1) اختر سورة عشوائية
        surah = random.randint(1, 114)
        # 2) جلب السورة للحصول على عدد آيات
        s = requests.get(f"https://api.alquran.cloud/v1/surah/{surah}/ar").json()
        verses = s.get("data", {}).get("ayahs", [])
        if not verses:
            return bot.send_message(message.chat.id, "❌ خطأ في تصفح القرآن.")

        # 3) اختر آية عشوائية وجلبها
        ayah = random.choice(verses)
        show_ayah(message.chat.id, surah, ayah["numberInSurah"])

    def ask_surah(msg):
        bot.send_message(msg.chat.id, "📖 اكتب رقم السورة (1–114):")
        bot.register_next_step_handler(msg, browse_surah)

    def browse_surah(msg):
        try:
            num = int(msg.text.strip())
            if not 1 <= num <= 114: raise
        except:
            return bot.send_message(msg.chat.id, "❌ رقم غير صحيح.")
        show_ayah(msg.chat.id, num, 1)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("nav:"))
    def nav(c):
        _, sur, ay = c.data.split(":")
        show_ayah(c.message.chat.id, int(sur), int(ay))

    def show_ayah(chat_id, surah, ayah):
        r = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar").json()
        if r.get("status") != "OK":
            return bot.send_message(chat_id, "❌ فشل في جلب الآية.")
        d = r["data"]
        text = f"📖 سورة {d['surah']['name']} – آية {d['numberInSurah']}\n\n{d['text']}"

        rec = get_user_reciter(chat_id) or "yasser"
        recs = {
            "yasser": "Yasser_Ad-Dussary_64kbps",
            "mishary": "Mishari_Alafasy_64kbps",
            "basit": "Abdul_Basit_Mujawwad_64kbps",
            "massad": "Abdurrahmaan_As-Sudais_64kbps"
        }
        aucode = recs.get(rec, list(recs.values())[0])
        audio = f"https://verses.quran.com/{aucode}/{surah}_{ayah}.mp3"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("⏮️ السابق", callback_data=f"nav:{surah}:{max(ayah-1,1)}"),
            InlineKeyboardButton("⏭️ التالي", callback_data=f"nav:{surah}:{ayah+1}")
        )
        markup.row(
            InlineKeyboardButton("🎙️ تغيير القارئ", callback_data="choose_reciter"),
            InlineKeyboardButton("⭐ المفضلة", callback_data=f"fav_ayah:{surah}:{ayah}")
        )

        bot.send_message(chat_id, text, reply_markup=markup)
        bot.send_audio(chat_id, audio)

    @bot.callback_query_handler(func=lambda c: c.data == "choose_reciter")
    def pick_reciter(c):
        m = InlineKeyboardMarkup(row_width=2)
        for k,n in [("yasser","🎧 ياسر"),("mishary","🎧 مشاري"),("basit","🎧 عبدالباسط"),("massad","🎧 مسعد")]:
            m.add(InlineKeyboardButton(n, callback_data=f"reciter:{k}"))
        bot.edit_message_text("اختار قارئ:", c.message.chat.id, c.message.message_id, reply_markup=m)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("reciter:"))
    def save_reciter_call(c):
        key = c.data.split(":")[1]
        set_user_reciter(c.from_user.id, key)
        bot.answer_callback_query(c.id, "✅ حفظ التفضيل.")
        bot.edit_message_text("تم اختيار القارئ بنجاح.", c.message.chat.id, c.message.message_id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fav_ayah:"))
    def fav_ayah(c):
        sur, ay = c.data.split(":")[1:]
        add_to_fav(c.from_user.id, "ayah", f"{sur}:{ay}")
        bot.answer_callback_query(c.id, "✅ أضيف للمفضلة.")
