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
    markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="main"))
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
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ رجوع", callback_data="main"))
            bot.edit_message_text(
                "*📖 ما هي ختمة؟*\n\n"
                "هي ختمة جماعية يشارك فيها 30 مسلم، كل واحد يقرأ جزء.\n"
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
                assigned = assign_juz_to_user(user_id)
                if assigned:
                    show_juz_menu(bot, call.message, assigned)
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
            khatmah_started = get_khatmah_status(user_id)
            if not khatmah_started:
                bot.edit_message_text(
                    "📌 لم تبدأ الختمة بعد.\n"
                    "سأخبرك عند اكتمال العدد لتبدأ التلاوة بإذن الله.",
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
                "✅ تم تسجيل ختم جزءك. جزاك الله خيرًا.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🏠 العودة إلى القائمة الرئيسية", callback_data="main")
                )
            )

        elif action == "status":
            kh_num = get_khatmah_number(user_id)
            users = get_users_in_khatmah(kh_num)
            done = sum(1 for u in users if u["status"] == "completed")
            total = len(users)
            bot.edit_message_text(
                f"📊 حالة الختمة:\n"
                f"📘 رقم الختمة: {kh_num}\n"
                f"✅ المكتمل: {done}/{total}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("⬅️ رجوع", callback_data="main")
                )
            )

        elif action == "mystatus":
            done = get_juz_status(user_id)
            msg = "✅ أنهيت الجزء." if done else "⏳ لم تنهِ بعد."
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

def show_juz_menu(bot, message, juz):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📖 جزئي", callback_data="khatmah:myjuz"),
        InlineKeyboardButton("📊 حالة الختمة", callback_data="khatmah:status"),
        InlineKeyboardButton("📌 حالة جزئي", callback_data="khatmah:mystatus")
    )
    markup.add(InlineKeyboardButton("🏠 العودة إلى القائمة الرئيسية", callback_data="main"))
    bot.edit_message_text(
        f"📘 الجزء المخصص لك هو: {juz}\n"
        "يمكنك الآن البدء بالتلاوة عندما تبدأ الختمة.",
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
        if index >= len(verses):
            index = len(verses) - 1
        set_last_ayah_index(user_id, index)

        ayah = verses[index]
        in_quran = ayah["number"]["inQuran"]
        ayah_no = ayah["number"]["inSurah"]
        text = ayah["text"]["arab"]
        ranges = get_surah_ranges()
        surah_name = get_surah_name(in_quran, ranges)

        msg = f"*📖 {surah_name}* [{ayah_no}]\n\n{text}"

        nav = InlineKeyboardMarkup(row_width=2)
        buttons = []
        if index > 0:
            buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data="khatmah:prev"))
        if index < len(verses) - 1:
            buttons.append(InlineKeyboardButton("التالي ➡️", callback_data="khatmah:next"))
        nav.add(*buttons)
        nav.add(InlineKeyboardButton("✅ أنهيت الجزء", callback_data="khatmah:complete"))
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
            f"❌ خطأ: {e}",
            message.chat.id,
            message.message_id
            )
