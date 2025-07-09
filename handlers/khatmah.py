import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import (
    assign_juz_to_user,
    get_user_juz,
    get_users_in_khatmah,
    mark_juz_completed,
    get_khatmah_status,
    get_juz_status,
    start_khatmah,
    get_khatmah_number
)
from utils.menu import show_main_menu

BASE_URL = "https://api.quran.gading.dev/juz/"

# ✅ استخراج أسماء السور
def get_surah_ranges():
    try:
        res = requests.get("https://api.quran.gading.dev/surah")
        data = res.json()["data"]
        surah_ranges = []
        in_quran_counter = 1
        for surah in data:
            total_ayahs = surah["numberOfVerses"]
            name = surah["name"]["short"]
            start = in_quran_counter
            end = start + total_ayahs - 1
            surah_ranges.append((start, end, name))
            in_quran_counter = end + 1
        return surah_ranges
    except Exception:
        return []

def get_surah_name(in_quran_number, ranges):
    for start, end, name in ranges:
        if start <= in_quran_number <= end:
            return name
    return "❓سورة غير معروفة"

# ✅ عرض واجهة ختمة
def show_khatmah_home(bot, message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("❓ ما هي ختمة؟", callback_data="khatmah:info"),
        InlineKeyboardButton("📥 الانضمام إلى ختمة", callback_data="khatmah:join")
    )
    bot.edit_message_text(
        "📖 *أهلاً بك في ختمة القرآن الجماعية!*",
        message.chat.id,
        message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

# ✅ تشغيل الزر من القائمة الرئيسية
def show_khatmah_menu_entry(bot, message):
    show_khatmah_home(bot, message)

# ✅ تسجيل الكول باك الخاص بالختمة
def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("khatmah:"))
    def handle_khatmah_buttons(call):
        user_id = call.from_user.id
        action = call.data.split(":")[1]
        juz = get_user_juz(user_id)
        khatmah_num = get_khatmah_number(user_id)

        if action == "info":
            bot.edit_message_text(
                "*📖 ما هي ختمة؟*\n\n"
                "الختمة الجماعية تتيح لك ختم القرآن الكريم مع إخوة وأخوات لك في الله.\n\n"
                "✅ كل شخص يُكلف بقراءة جزء واحد.\n"
                "🔄 عند اكتمال الثلاثين جزءًا، نختم سويًا ونبدأ ختمة جديدة.\n"
                "🎯 الهدف: نشر الخير والارتباط بالقرآن الكريم يوميًا.\n"
                "🌟 بادر بالانضمام وكن من الذاكرين الله كثيرًا.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("⬅️ رجوع", callback_data="menu:khatmah")
                )
            )

        elif action == "join":
            if juz:
                bot.edit_message_text(
                    f"📘 لقد انضممت مسبقًا إلى ختمة رقم {khatmah_num}.\n"
                    f"✅ الجزء المخصص لك: {juz}",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("➡️ عرض الجزء", callback_data="khatmah:myjuz")
                    )
                )
            else:
                assigned = assign_juz_to_user(user_id)
                if assigned:
                    bot.edit_message_text(
                        f"📘 تم تسجيلك في ختمة جديدة!\n"
                        f"✅ الجزء المخصص لك: {assigned}\n\n"
                        "⏳ سيتم إشعارك عند بدء الختمة بإذن الله.\n"
                        "جزاك الله خيرًا على المشاركة 🌟",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")
                        )
                    )
                else:
                    bot.edit_message_text(
                        "❌ جميع الأجزاء محجوزة حاليًا.\n"
                        "✅ سيتم إشعارك عند بدء ختمة جديدة قريبًا.",
                        call.message.chat.id,
                        call.message.message_id
                    )

        elif action == "myjuz":
            if juz:
                show_user_juz(bot, call.message, user_id, juz)
            else:
                bot.edit_message_text(
                    "❌ لا يوجد جزء مخصص لك بعد.\n📥 انضم أولًا إلى ختمة.",
                    call.message.chat.id,
                    call.message.message_id
                )

        elif action == "complete":
            mark_juz_completed(user_id)
            bot.edit_message_text(
                "✅ تم تحديد الجزء كمكتمل! جزاك الله خيرًا على مشاركتك المباركة.",
                call.message.chat.id,
                call.message.message_id
            )

        elif action == "listen":
            if juz:
                audio_url = f"https://verses.quran.com/MisharyAlafasy/mp3/{juz:02}.mp3"
                bot.send_audio(call.message.chat.id, audio_url, caption=f"🎧 الاستماع للجزء {juz}")
            else:
                bot.answer_callback_query(call.id, "❌ لا يوجد جزء مخصص لك.")

        elif action == "main":
            show_main_menu(bot, call.message)

# ✅ عرض الجزء المخصص للمستخدم
def show_user_juz(bot, message, user_id, juz):
    try:
        res = requests.get(BASE_URL + str(juz))
        if res.status_code != 200:
            raise Exception("فشل في جلب الجزء.")
        data = res.json().get("data", {})
        ayahs = data.get("ayahs", [])
        ranges = get_surah_ranges()

        text = f"📘 *الجزء {juz}*\nعدد الآيات: {len(ayahs)}\n\n"
        for ayah in ayahs:
            num = ayah["number"]["inQuran"]
            surah_name = get_surah_name(num, ranges)
            ayah_number = ayah["number"]["inSurah"]
            ayah_text = ayah["text"]["arab"]
            text += f"*{surah_name}* [{ayah_number}]: {ayah_text}\n"

        khatmah_status = get_khatmah_status(user_id)
        juz_status = get_juz_status(user_id)

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📖 جزئي", callback_data="khatmah:myjuz"),
            InlineKeyboardButton("🎧 سماع جزئي", callback_data="khatmah:listen"),
        )
        markup.add(
            InlineKeyboardButton("✅ أنهيت الجزء", callback_data="khatmah:complete"),
            InlineKeyboardButton("🏠 العودة", callback_data="back_to_main")
        )
        markup.add(
            InlineKeyboardButton(f"📊 حالة الختمة: {'مكتملة ✅' if khatmah_status else 'قيد التنفيذ 🕓'}", callback_data="ignore"),
            InlineKeyboardButton(f"📌 حالة جزئي: {'تم ✅' if juz_status else 'قيد القراءة 📖'}", callback_data="ignore")
        )

        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ خطأ خلال جلب الجزء:\n{e}",
            message.chat.id,
            message.message_id
    )
