import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import (
    assign_juz_to_user, get_user_juz, get_users_in_khatmah,
    mark_juz_completed, get_khatmah_status, get_juz_status,
    get_khatmah_number, get_last_ayah_index, set_last_ayah_index
)

BASE_URL = "https://api.quran.gading.dev/juz/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ✅ استخراج أسماء السور
def get_surah_ranges():
    try:
        res = requests.get("https://api.quran.gading.dev/surah", headers=HEADERS)
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
    except:
        return []

def get_surah_name(in_quran_number, ranges):
    for start, end, name in surah_ranges:
        if start <= in_quran_number <= end:
            return name
    return "❓سورة غير معروفة"

# ✅ عرض القائمة الرئيسية لختمة
def show_khatmah_home(bot, message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("❓ ما هي ختمة؟", callback_data="khatmah:info"),
        InlineKeyboardButton("📥 الانضمام إلى ختمة", callback_data="khatmah:join")
    )
    markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="main"))
    bot.edit_message_text(
        "📖 *أهلاً بك في ختمة القرآن الجماعية!*",
        message.chat.id,
        message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

# ✅ استدعاء من main.py
def show_khatmah_menu_entry(bot, message):
    show_khatmah_home(bot, message)

# ✅ تسجيل الأحداث
def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("khatmah:"))
    def handle_khatmah_buttons(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        action = call.data.split(":")[1]
        juz = get_user_juz(user_id)
        khatmah_started = get_khatmah_status(user_id)

        if action == "info":
            bot.edit_message_text(
                "*📖 ما هي ختمة؟*\n\n"
                "هي ختمة جماعية يتعاون فيها 30 مشترك كلٌ يقرأ جزءًا من القرآن.\n"
                "عند اكتمال الثلاثين، تبدأ الختمة.\n"
                "بمجرد انتهائها، تبدأ ختمة جديدة تلقائيًا بإذن الله.\n\n"
                "💡 فرصة رائعة لختم القرآن بجهد يسير وأجر عظيم!",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("⬅️ رجوع", callback_data="main")
                )
            )

        elif action == "join":
            if juz:
                bot.edit_message_text(
                    f"📘 أنت بالفعل مشترك في ختمة.\n"
                    f"✅ الجزء المخصص لك: {juz}",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📖 جزئي", callback_data="khatmah:myjuz")],
                        [InlineKeyboardButton("📊 حالة الختمة", callback_data="khatmah:status"),
                         InlineKeyboardButton("📌 حالة جزئي", callback_data="khatmah:mystatus")],
                        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main")]
                    ])
                )
            else:
                assigned = assign_juz_to_user(user_id)
                if assigned:
                    bot.edit_message_text(
                        f"✅ تم تسجيلك بنجاح!\n"
                        f"📘 الجزء المخصص لك: {assigned}\n"
                        "⏳ سيتم إشعارك عند بدء الختمة بإذن الله.",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton("🏠 الرئيسية", callback_data="main")
                        )
                    )
                else:
                    bot.edit_message_text(
                        "⚠️ جميع الأجزاء محجوزة حالياً.\n"
                        "📨 سيتم إعلامك عند بدء ختمة جديدة.",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton("🏠 الرئيسية", callback_data="main")
                        )
                    )

        elif action == "myjuz":
            if not juz:
                bot.edit_message_text(
                    "❌ لا يوجد جزء مخصص لك.\nانضم أولاً إلى الختمة.",
                    call.message.chat.id,
                    call.message.message_id
                )
                return
            index = get_last_ayah_index(user_id) or 0
            show_ayah(bot, call.message, user_id, juz, index)

        elif action == "next":
            index = get_last_ayah_index(user_id) or 0
            show_ayah(bot, call.message, user_id, juz, index + 1)

        elif action == "prev":
            index = get_last_ayah_index(user_id) or 0
            show_ayah(bot, call.message, user_id, juz, max(0, index - 1))

        elif action == "complete":
            mark_juz_completed(user_id)
            bot.edit_message_text(
                "✅ تم تحديد الجزء كمكتمل! جزاك الله خيرًا على مشاركتك.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="main")
                )
            )

        elif action == "status":
            participants = get_users_in_khatmah(get_khatmah_number(user_id))
            total = len(participants)
            completed = len([p for p in participants if p["status"] == "completed"])
            remaining = total - completed
            bot.edit_message_text(
                f"📊 حالة الختمة:\n\n"
                f"📌 عدد المشاركين: {total}\n"
                f"✅ أنجزوا أجزاءهم: {completed}\n"
                f"⏳ لم ينهوا بعد: {remaining}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("⬅️ رجوع", callback_data="main")
                )
            )

        elif action == "mystatus":
            status = get_juz_status(user_id)
            msg = "✅ لقد أتممت الجزء الخاص بك، أحسنت!" if status else "⏳ لم تُنهِ الجزء بعد."
            bot.edit_message_text(
                f"📌 حالة جزئي:\n\n{msg}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("⬅️ رجوع", callback_data="main")
                )
            )

# ✅ عرض آية واحدة
def show_ayah(bot, message, user_id, juz, index):
    try:
        res = requests.get(BASE_URL + str(juz), headers=HEADERS)
        verses = res.json().get("data", {}).get("verses", [])
        if not verses:
            raise Exception("الآيات غير متوفرة.")
        if index >= len(verses):
            index = len(verses) - 1
        set_last_ayah_index(user_id, index)

        ayah = verses[index]
        number = ayah["number"]["inQuran"]
        ayah_number = ayah["number"]["inSurah"]
        text = ayah["text"]["arab"]
        surah_ranges = get_surah_ranges()
        surah_name = get_surah_name(number, surah_ranges)

        msg = f"*📖 {surah_name}* [{ayah_number}]\n\n{text}"

        nav = InlineKeyboardMarkup(row_width=2)
        buttons = []
        if index > 0:
            buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data="khatmah:prev"))
        if index < len(verses) - 1:
            buttons.append(InlineKeyboardButton("التالي ➡️", callback_data="khatmah:next"))
        nav.row(*buttons)
        nav.add(
            InlineKeyboardButton("✅ أنهيت الجزء", callback_data="khatmah:complete")
        )
        nav.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="main"))

        bot.edit_message_text(
            msg,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=nav
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ خطأ:\n{e}",
            message.chat.id,
            message.message_id
            )
