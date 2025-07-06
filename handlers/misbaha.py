from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.menu import show_main_menu

# قائمة الأذكار
AZKAR_LIST = ["سبحان الله", "الحمد لله", "الله أكبر", "لا إله إلا الله", "لا حول ولا قوة إلا بالله"]

# لتخزين حالة كل مستخدم: {"user_id": {"dhikr": ..., "count": ...}}
user_counters = {}

def register(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "menu:misbaha")
    def open_misbaha_menu(call):
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for dhikr in AZKAR_LIST:
            markup.add(InlineKeyboardButton(dhikr, callback_data=f"misbaha:select:{dhikr}"))
        markup.add(InlineKeyboardButton("↩️ العودة", callback_data="main_menu"))

        bot.edit_message_text(
            "🧮 اختر نوع الذكر لبدء التسبيح:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("misbaha:select:"))
    def start_counting(call):
        dhikr = call.data.split(":")[2]
        user_counters[call.from_user.id] = {"dhikr": dhikr, "count": 0}
        send_counter_message(bot, call.message.chat.id, call.message.message_id, call.from_user.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("misbaha:count"))
    def increment_counter(call):
        user_id = call.from_user.id
        if user_id in user_counters:
            user_counters[user_id]["count"] += 1
        send_counter_message(bot, call.message.chat.id, call.message.message_id, user_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("misbaha:reset"))
    def reset_counter(call):
        user_id = call.from_user.id
        if user_id in user_counters:
            user_counters[user_id]["count"] = 0
        send_counter_message(bot, call.message.chat.id, call.message.message_id, user_id)

def send_counter_message(bot, chat_id, message_id, user_id):
    dhikr = user_counters[user_id]["dhikr"]
    count = user_counters[user_id]["count"]

    text = f"🧮 الذكر المختار: *{dhikr}*\n\n🔢 عدد التسبيحات: *{count}*"
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("➕ تسبيحة", callback_data="misbaha:count"),
        InlineKeyboardButton("♻️ إعادة", callback_data="misbaha:reset")
    )
    markup.add(InlineKeyboardButton("↩️ العودة", callback_data="menu:misbaha"))
    markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )
