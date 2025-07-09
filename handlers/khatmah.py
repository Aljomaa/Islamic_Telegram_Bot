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
    get_khatmah_number,
    get_last_ayah_index,
    set_last_ayah_index
)
from utils.menu import show_main_menu

BASE_URL = "https://api.quran.gading.dev/juz/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

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
    def handle_khatmah_buttons(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        action_data = call.data.split(":")
        action = action_data[1]
        juz = get_user_juz(user_id)

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
                    InlineKeyboardButton("⬅️ رجوع", callback_data="menu:khatmah")
                )
            )

        elif action == "join":
            if juz:
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    InlineKeyboardButton("📖 جزئي", callback_data="khatmah:myjuz"),
                    InlineKeyboardButton("🎧 سماع جزئي", callback_data="khatmah:listen"),
                    InlineKeyboardButton("📊 حالة الختمة", callback_data="khatmah:status"),
                    InlineKeyboardButton("📌 حالة جزئي", callback_data="khatmah:mystatus"),
                    InlineKeyboardButton("🏠 العودة إلى القائمة الرئيسية", callback_data="main")
                )
                bot.edit_message_text(
                    f"📘 أنت بالفعل مشترك في ختمة.\n"
                    f"✅ الجزء المخصص لك: {juz}",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup
                )
            else:
                assigned = assign_juz_to_user(user_id)
                if assigned:
                    markup = InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        InlineKeyboardButton("📖 جزئي", callback_data="khatmah:myjuz"),
                        InlineKeyboardButton("🎧 سماع جزئي", callback_data="khatmah:listen"),
                        InlineKeyboardButton("📊 حالة الختمة", callback_data="khatmah:status"),
                        InlineKeyboardButton("📌 حالة جزئي", callback_data="khatmah:mystatus"),
                        InlineKeyboardButton("🏠 العودة إلى القائمة الرئيسية", callback_data="main")
                    )
                    bot.edit_message_text(
                        f"✅ تم تسجيلك بنجاح!\n"
                        f"📘 الجزء المخصص لك: {assigned}",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=markup
                    )
                else:
                    bot.edit_message_text(
                        "⚠️ جميع الأجزاء محجوزة حالياً.\n"
                        "📨 سيتم إعلامك عند بدء ختمة جديدة.",
                        call.message.chat.id,
                        call.message.message_id
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
            juz = get_user_juz(user_id)
            index = get_last_ayah_index(user_id) or 0
            show_ayah(bot, call.message, user_id, juz, index + 1)

        elif action == "prev":
            juz = get_user_juz(user_id)
            index = get_last_ayah_index(user_id) or 0
            show_ayah(bot, call.message, user_id, juz, max(0, index - 1))

        elif action == "listen":
            if juz:
                audio_url = f"https://verses.quran.com/MisharyAlafasy/mp3/{juz:02}.mp3"
                bot.send_audio(call.message.chat.id, audio_url, caption=f"🎧 الاستماع للجزء {juz}")
            else:
                bot.answer_callback_query(call.id, "❌ لا يوجد جزء مخصص لك.")

        elif action == "complete":
            mark_juz_completed(user_id)
            bot.edit_message_text(
                "✅ تم تحديد الجزء كمكتمل! جزاك الله خيرًا على مشاركتك.",
                call.message.chat.id,
                call.message.message_id
            )

        elif action == "status":
            kh_num = get_khatmah_number(user_id)
            users = get_users_in_khatmah(kh_num)
            completed = sum(1 for u in users if u["status"] == "completed")
            total = len(users)
            bot.edit_message_text(
                f"📊 حالة الختمة:\n"
                f"📘 ختمة رقم: {kh_num}\n"
                f"✅ المكتمل: {completed} من {total}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("⬅️ رجوع", callback_data="main")
                )
            )

        elif action == "mystatus":
            status = get_juz_status(user_id)
            msg = "✅ لقد أنهيت الجزء الخاص بك. أحسنت!" if status else "⏳ لم تكمل الجزء بعد. تابع التلاوة."
            bot.edit_message_text(
                f"📌 حالة جزئك:\n{msg}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("⬅️ رجوع", callback_data="main")
                )
            )

        elif action == "main":
            show_main_menu(bot, call.message)

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
        ranges = get_surah_ranges()
        surah_name = get_surah_name(number, ranges)

        msg = f"*📖 {surah_name}* [{ayah_number}]\n\n{text}"

        nav = InlineKeyboardMarkup(row_width=2)
        if index > 0:
            nav.add(InlineKeyboardButton("⬅️ السابق", callback_data="khatmah:prev"))
        if index < len(verses) - 1:
            nav.add(InlineKeyboardButton("التالي ➡️", callback_data="khatmah:next"))
        nav.add(
            InlineKeyboardButton("🎧 سماع جزئي", callback_data="khatmah:listen"),
            InlineKeyboardButton("✅ أنهيت الجزء", callback_data="khatmah:complete")
        )
        nav.add(InlineKeyboardButton("🏠 العودة إلى القائمة الرئيسية", callback_data="main"))

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
