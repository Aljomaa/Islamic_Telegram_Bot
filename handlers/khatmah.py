import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import assign_juz_to_user, get_user_juz, get_users_in_khatmah, mark_juz_completed
from utils.menu import show_main_menu

BASE_URL = "https://api.quran.gading.dev/juz/"

# ✅ الحصول على اسم السورة من خلال ترتيبها داخل المصحف
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
    except Exception as e:
        return []

def get_surah_name(in_quran_number, ranges):
    for start, end, name in ranges:
        if start <= in_quran_number <= end:
            return name
    return "❓سورة غير معروفة"

def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "menu:khatmah")
    def show_khatmah_menu(call):
        user_id = call.from_user.id
        juz = get_user_juz(user_id)

        if juz:
            show_user_juz(bot, call.message, user_id, juz)
        else:
            assigned = assign_juz_to_user(user_id)
            if assigned:
                show_user_juz(bot, call.message, user_id, assigned)
            else:
                bot.edit_message_text(
                    "❌ تم إكمال هذه الختمة. سيتم إشعارك عند بدء ختمة جديدة بإذن الله.",
                    call.message.chat.id,
                    call.message.message_id
                )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("khatmah:"))
    def handle_khatmah_buttons(call):
        user_id = call.from_user.id
        juz = get_user_juz(user_id)
        action = call.data.split(":")[1]

        if action == "complete":
            mark_juz_completed(user_id)
            bot.edit_message_text(
                "✅ تم تحديد الجزء كمكتمل! جزاك الله خيرًا على إسهامك في الختمة.",
                call.message.chat.id,
                call.message.message_id
            )
        elif action == "main":
            show_main_menu(bot, call.message)
        elif action == "listen":
            audio_url = f"https://verses.quran.com/MisharyAlafasy/mp3/{juz:02}.mp3"
            bot.send_audio(call.message.chat.id, audio_url, caption=f"🎧 الاستماع للجزء {juz}")
        elif action == "myjuz":
            show_user_juz(bot, call.message, user_id, juz)

def show_user_juz(bot, message, user_id, juz):
    try:
        res = requests.get(BASE_URL + str(juz))
        if res.status_code != 200:
            raise Exception("فشل في جلب الجزء.")

        data = res.json()["data"]
        ayahs = data["ayahs"]
        ranges = get_surah_ranges()

        text = f"📘 *تم استلام الجزء {juz}، عدد الآيات: {len(ayahs)}*\n\n"
        for ayah in ayahs:
            num = ayah["number"]["inQuran"]
            surah_name = get_surah_name(num, ranges)
            ayah_number = ayah["number"]["inSurah"]
            ayah_text = ayah["text"]["arab"]
            text += f"*{surah_name}* [{ayah_number}]: {ayah_text}\n"

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📖 جزئي", callback_data="khatmah:myjuz"),
            InlineKeyboardButton("🎧 الاستماع له", callback_data="khatmah:listen"),
        )
        markup.add(
            InlineKeyboardButton("✅ إكمال الجزء", callback_data="khatmah:complete"),
            InlineKeyboardButton("🏠 العودة", callback_data="khatmah:main")
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
