from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import (
    assign_user_to_khatmah,
    get_user_khatmah_info,
    is_khatmah_full,
    get_users_in_khatmah,
    get_part_text,
    mark_part_completed,
    is_part_completed
)
from utils.menu import show_main_menu

def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "menu:khatmah")
    def show_khatmah_entry(call):
        user_id = call.from_user.id
        info = get_user_khatmah_info(user_id)

        if not info:
            joined = assign_user_to_khatmah(user_id)
            if not joined:
                bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء الانضمام.")
                return
            info = get_user_khatmah_info(user_id)
            if is_khatmah_full(info["khatmah_id"]):
                notify_khatmah_filled(bot, info["khatmah_id"])

        show_khatmah_options(bot, call.message, user_id, info)

    @bot.callback_query_handler(func=lambda call: call.data == "khatmah:part")
    def show_my_part(call):
        user_id = call.from_user.id
        info = get_user_khatmah_info(user_id)
        text = get_part_text(info["juz"])
        bot.edit_message_text(
            f"📖 *جزءك رقم {info['juz']}*\n\n{text[:1000]}...",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("⬅️ الرجوع", callback_data="menu:khatmah")
            )
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("khatmah:play:"))
    def play_juz_audio(call):
        juz = int(call.data.split(":")[2])
        audio_url = f"https://verses.quran.com/alafasy/juz_{juz:02d}.mp3"
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_audio(
                call.message.chat.id,
                audio_url,
                caption=f"🔊 الاستماع إلى جزء {juz}",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("⬅️ العودة", callback_data="menu:khatmah")
                )
            )
        except:
            bot.send_message(call.message.chat.id, "❌ فشل في تحميل الصوت.")

    @bot.callback_query_handler(func=lambda call: call.data == "khatmah:status")
    def show_part_status(call):
        user_id = call.from_user.id
        info = get_user_khatmah_info(user_id)
        completed = is_part_completed(info["khatmah_id"], info["juz"])
        status = "✅ مكتمل" if completed else "⌛️ جاري القراءة"
        bot.answer_callback_query(call.id, f"📍 حالة الجزء: {status}", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "khatmah:complete")
    def mark_complete(call):
        user_id = call.from_user.id
        info = get_user_khatmah_info(user_id)
        mark_part_completed(info["khatmah_id"], info["juz"])
        bot.answer_callback_query(call.id, "✅ تم تأكيد إتمام الجزء.", show_alert=True)
        show_khatmah_options(bot, call.message, user_id, info)

def show_khatmah_options(bot, message, user_id, info):
    juz = info["juz"]
    khatmah_id = info["khatmah_id"]
    completed = is_part_completed(khatmah_id, juz)

    text = f"""📘 *ختمتي*

🔢 *الختمة:* `{khatmah_id}`
📖 *جزءك:* `{juz}`
📍 *الحالة:* {"✅ مكتمل" if completed else "⌛️ جاري القراءة"}
"""

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📖 جزئي", callback_data="khatmah:part"),
        InlineKeyboardButton("🔊 الاستماع", callback_data=f"khatmah:play:{juz}"),
        InlineKeyboardButton("📍 حالة الجزء", callback_data="khatmah:status")
    )
    if not completed:
        markup.add(InlineKeyboardButton("✅ إتمام الجزء", callback_data="khatmah:complete"))
    markup.add(InlineKeyboardButton("⬅️ الرجوع", callback_data="back_to_main"))

    try:
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

def notify_khatmah_filled(bot, khatmah_id):
    users = get_users_in_khatmah(khatmah_id)
    for user in users:
        try:
            bot.send_message(
                user["user_id"],
                f"""📘 *تم اكتمال الختمة رقم {khatmah_id}!*

⏳ لديك 24 ساعة لإتمام الجزء المخصص لك.

💡 لا تنس أن تؤكد إتمام الجزء من خلال الضغط على زر "✅ إتمام الجزء".

🌟 نسأل الله لك القبول!""",
                parse_mode="Markdown"
            )
        except:
            continue
