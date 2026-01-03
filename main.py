import telebot
from flask import Flask, request
from config import BOT_TOKEN, OWNER_ID
from handlers import prayers, quran, athkar, favorites, complaints, admin, hadith, settings, misbaha, khatmah
from tasks import reminders
from utils.db import is_admin, add_admin, register_user, set_bot_instance
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

# ======================
# إعدادات أساسية
# ======================
bot = telebot.TeleBot(BOT_TOKEN)
set_bot_instance(bot)

app = Flask(__name__)

# رابط Render (يتم أخذه من متغير البيئة)
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

# ======================
# Webhook
# ======================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def home():
    return "Bot is running with Webhook ✅"

# ======================
# القائمة الرئيسية
# ======================
def show_main_menu(bot, message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🕌 أوقات الصلاة", callback_data="menu:prayer"),
        InlineKeyboardButton("📖 القرآن الكريم", callback_data="menu:quran"),
        InlineKeyboardButton("📿 الأذكار", callback_data="menu:athkar"),
        InlineKeyboardButton("📜 الحديث", callback_data="menu:hadith"),
        InlineKeyboardButton("📿 المسبحة", callback_data="menu:misbaha"),
        InlineKeyboardButton("📘 ختمتي", callback_data="menu:khatmah"),
        InlineKeyboardButton("⭐ المفضلة", callback_data="menu:fav"),
        InlineKeyboardButton("📝 الشكاوى", callback_data="menu:complain"),
        InlineKeyboardButton("⚙️ الإعدادات", callback_data="menu:settings")
    )
    if is_admin(message.chat.id):
        markup.add(InlineKeyboardButton("🧑‍💼 المشرف", callback_data="menu:admin"))

    bot.edit_message_text(
        "🌙 مرحبًا بك في البوت الإسلامي!\nاختر أحد الخيارات:",
        message.chat.id,
        message.message_id,
        reply_markup=markup
    )

# ======================
# /start
# ======================
@bot.message_handler(commands=["start"])
def welcome(msg):
    register_user(msg.from_user)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🕌 أوقات الصلاة", callback_data="menu:prayer"),
        InlineKeyboardButton("📖 القرآن الكريم", callback_data="menu:quran"),
        InlineKeyboardButton("📿 الأذكار", callback_data="menu:athkar"),
        InlineKeyboardButton("📜 الحديث", callback_data="menu:hadith"),
        InlineKeyboardButton("📿 المسبحة", callback_data="menu:misbaha"),
        InlineKeyboardButton("📘 ختمتي", callback_data="menu:khatmah"),
        InlineKeyboardButton("⭐ المفضلة", callback_data="menu:fav"),
        InlineKeyboardButton("📝 الشكاوى", callback_data="menu:complain"),
        InlineKeyboardButton("⚙️ الإعدادات", callback_data="menu:settings")
    )
    if is_admin(msg.from_user.id):
        markup.add(InlineKeyboardButton("🧑‍💼 المشرف", callback_data="menu:admin"))

    bot.send_message(
        msg.chat.id,
        "🌙 مرحبًا بك في البوت الإسلامي!\nاختر أحد الخيارات:",
        reply_markup=markup
    )

# ======================
# Callback Menu
# ======================
@bot.callback_query_handler(func=lambda call: call.data.startswith("menu:") or call.data == "back_to_main")
def handle_main_menu(call):
    bot.answer_callback_query(call.id)
    action = call.data.split(":")[1] if ":" in call.data else "main"

    if action == "prayer":
        prayers.show_prayer_times(bot, call.message)

    elif action == "quran":
        quran.show_main_quran_menu(bot, call.message.chat.id, call.message.message_id)

    elif action == "athkar":
        athkar.show_athkar_menu(bot, call.message.chat.id, call.message.message_id)

    elif action == "hadith":
        hadith.show_hadith_menu(bot, call.message)

    elif action == "misbaha":
        misbaha.show_misbaha_menu(bot, call.message.chat.id, call.message.message_id)

    elif action == "fav":
        favorites.show_fav_main_menu(bot, call.message.chat.id, call.message.message_id)

    elif action == "complain":
        complaints.show_complaint_menu(bot, call.message.chat.id, call.message.message_id)

    elif action == "admin":
        if is_admin(call.from_user.id):
            admin.show_admin_menu(bot, call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(call.message.chat.id, "❌ هذا الخيار مخصص للمشرف فقط.")

    elif action == "settings":
        settings.show_settings_menu(bot, call.message.chat.id, call.message.message_id)

    elif action == "khatmah":
        khatmah.show_khatmah_menu_entry(bot, call.message)

    elif action == "main" or call.data == "back_to_main":
        show_main_menu(bot, call.message)

# ======================
# تسجيل الـ handlers
# ======================
prayers.register(bot)
quran.register(bot)
athkar.register(bot)
favorites.register(bot)
complaints.register(bot)
complaints.handle_callbacks(bot)
admin.register(bot)
hadith.register(bot)
settings.register(bot)
misbaha.register(bot)
khatmah.register(bot)

# ======================
# تشغيل السيرفر + Webhook
# ======================
if __name__ == "__main__":
    bot.remove_webhook()

    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"
        bot.set_webhook(url=webhook_url)

    reminders.start_reminders(bot)

    if not is_admin(OWNER_ID):
        add_admin(OWNER_ID)

    app.run(host="0.0.0.0", port=10000)
