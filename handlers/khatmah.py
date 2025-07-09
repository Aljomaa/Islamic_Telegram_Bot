import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import (
    assign_juz_to_user,
    get_user_juz,
    get_users_in_khatmah,
    mark_juz_completed,
    get_khatmah_status,
    get_juz_status,
    get_khatmah_number,
    get_last_ayah_index,
    set_last_ayah_index
)
from utils.menu import show_main_menu

BASE_URL = "https://api.quran.gading.dev/juz/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ✅ استخراج أسماء السور
def get_surah_ranges():
    try:
        res = requests.get("https://api.quran.gading.dev/surah", headers=HEADERS)
        data = res.json()["data"]
        ranges = []
        pos = 1
        for surah in data:
            count = surah["numberOfVerses"]
            name = surah["name"]["short"]
            start = pos
            end = pos + count - 1
            ranges.append((start, end, name))
            pos = end + 1
        return ranges
    except:
        return []

def get_surah_name(in_quran_number, ranges):
    for start, end, name in ranges:
        if start <= in_quran_number <= end:
            return name
    return "❓سورة غير معروفة"

def show_khatmah_home(bot, message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("❓ ما هي ختمة؟", callback_data="khatmah:info"),
        InlineKeyboardButton("📥 الانضمام إلى ختمة", callback_data="khatmah:join")
    )
    markup.add(InlineKeyboardButton("🏠 العودة إلى القائمة الرئيسية", callback_data="main"))
    bot.edit_message_text(
        "📖 *أهلاً بك في ختمة القرآن الجماعية!*",
        message.chat.id,
        message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

def show_khatmah_menu_entry(bot, message):
    show_khatmah_home(bot, message)

def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("khatmah:"))
    def handle(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        action = call.data.split(":")[1]
        juz = get_user_juz(user_id)

        if action == "info":
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ رجوع", callback_data="main"))
            bot.edit_message_text(
                "*📖 ما هي ختمة؟*\n\n"
                "هي ختمة جماعية يشترك فيها 30 شخص، كل واحد يقرأ جزء.\n"
                "عند اكتمال العدد، تبدأ الختمة تلقائياً.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )

        elif action == "join":
            if juz:
                show_juz_menu(bot, call.message, juz)
            else:
                new_juz = assign_juz_to_user(user_id)
                if new_juz:
                    show_juz_menu(bot, call.message, new_juz)
                else:
                    bot.edit_message_text("❌ جميع الأجزاء محجوزة حالياً.", call.message.chat.id, call.message.message_id)

        elif action == "myjuz":
            if not juz:
                bot.edit_message_text("❌ لم يتم تخصيص جزء لك بعد.", call.message.chat.id, call.message.message_id)
                return
            index = get_last_ayah_index(user_id) or 0
            show_ayah(bot, call.message, user_id, juz, index)

        elif action == "next":
            index = get_last_ayah_index(user_id) or 0
            show_ayah(bot, call.message, user_id, juz, index + 1)

        elif action == "prev":
            index = get_last_ayah_index(user_id) or 0
            show_ayah(bot, call.message, user_id, juz, max(0, index - 1))

        elif action == "listen":
            if juz:
                audio_url = f"https://verses.quran.com/MisharyAlafasy/mp3/{juz:02}.mp3"
                bot.send_audio(call.message.chat.id, audio_url, caption=f"🎧 الجزء {juz} بصوت مشاري العفاسي")
            else:
                bot.answer_callback_query(call.id, "❌ لا يوجد جزء مخصص لك.")

        elif action == "complete":
            mark_juz_completed(user_id)
            bot.edit_message_text("✅ تم تسجيل ختم جزءك. جزاك الله خيرًا.", call.message.chat.id, call.message.message_id)

        elif action == "status":
            num = get_khatmah_number(user_id)
            users = get_users_in_khatmah(num)
            done = sum(1 for u in users if u["status"] == "completed")
            total = len(users)
            bot.edit_message_text(
                f"📊 حالة الختمة:\n📘 رقم الختمة: {num}\n✅ المكتمل: {done}/{total}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ رجوع", callback_data="main"))
            )

        elif action == "mystatus":
            done = get_juz_status(user_id)
            bot.edit_message_text(
                f"📌 حالة جزئك:\n{'✅ مكتمل' if done else '⏳ لم تكتمل بعد'}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ رجوع", callback_data="main"))
            )

        elif action == "main":
            show_main_menu(bot, call.message)

def show_juz_menu(bot, message, juz):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📖 جزئي", callback_data="khatmah:myjuz"),
        InlineKeyboardButton("🎧 سماع جزئي", callback_data="khatmah:listen"),
        InlineKeyboardButton("📊 حالة الختمة", callback_data="khatmah:status"),
        InlineKeyboardButton("📌 حالة جزئي", callback_data="khatmah:mystatus")
    )
    markup.add(InlineKeyboardButton("🏠 العودة إلى القائمة الرئيسية", callback_data="main"))
    bot.edit_message_text(
        f"📘 الجزء المخصص لك هو: {juz}",
        message.chat.id,
        message.message_id,
        reply_markup=markup
    )

def show_ayah(bot, message, user_id, juz, index):
    try:
        res = requests.get(BASE_URL + str(juz), headers=HEADERS)
        verses = res.json().get("data", {}).get("verses", [])
        if not verses:
            raise Exception("❌ لم يتم العثور على آيات.")
        if index >= len(verses): index = len(verses) - 1
        set_last_ayah_index(user_id, index)
        ayah = verses[index]
        num = ayah["number"]["inQuran"]
        ayah_num = ayah["number"]["inSurah"]
        text = ayah["text"]["arab"]
        surah = get_surah_name(num, get_surah_ranges())
        msg = f"*📖 {surah}* [{ayah_num}]\n\n{text}"

        nav = InlineKeyboardMarkup(row_width=2)
        row = []
        if index > 0:
            row.append(InlineKeyboardButton("⬅️ السابق", callback_data="khatmah:prev"))
        if index < len(verses) - 1:
            row.append(InlineKeyboardButton("التالي ➡️", callback_data="khatmah:next"))
        if row: nav.add(*row)
        nav.add(
            InlineKeyboardButton("🎧 سماع جزئي", callback_data="khatmah:listen"),
            InlineKeyboardButton("✅ أنهيت الجزء", callback_data="khatmah:complete")
        )
        nav.add(InlineKeyboardButton("🏠 العودة إلى القائمة الرئيسية", callback_data="main"))

        bot.edit_message_text(msg, message.chat.id, message.message_id, parse_mode="Markdown", reply_markup=nav)
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {e}", message.chat.id, message.message_id)
