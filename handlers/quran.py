import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
import random

API_BASE = "https://api.quran.gading.dev"

def register(bot):
    @bot.message_handler(commands=['quran'])
    def show_main_quran_menu(msg):
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("📖 تصفح السور", callback_data="browse_quran"),
            InlineKeyboardButton("🕋 آية من القرآن", callback_data="random_ayah")
        )
        bot.send_message(msg.chat.id, "اختر ما تود فعله:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "browse_quran")
    def ask_surah_number(call):
        bot.send_message(call.message.chat.id, "📖 اكتب رقم السورة (من 1 إلى 114):")
        bot.register_next_step_handler(call.message, lambda msg: send_ayah(msg.chat.id, msg.text.strip(), 1, call.message))

    @bot.callback_query_handler(func=lambda call: call.data == "random_ayah")
    def random_ayah(call):
        try:
            surah_num = random.randint(1, 114)
            surah_res = requests.get(f"{API_BASE}/surah/{surah_num}", timeout=10)
            surah_data = surah_res.json()
            verses = surah_data["data"]["verses"]
            ayah = random.choice(verses)
            send_ayah(call.message.chat.id, surah_num, ayah["number"]["inSurah"], call.message, edit=True)
        except Exception as e:
            print(f"[ERROR] Random Ayah: {e}")
            bot.send_message(call.message.chat.id, "❌ فشل في جلب آية عشوائية. حاول لاحقاً.")

    def send_ayah(chat_id, surah_num, ayah_num, message=None, edit=False):
        try:
            surah_num = int(surah_num)
            ayah_num = int(ayah_num)
            
            if surah_num < 1 or surah_num > 114:
                raise ValueError("رقم السورة يجب أن يكون بين 1 و114")
                
            res = requests.get(f"{API_BASE}/surah/{surah_num}", timeout=10)
            data = res.json()

            if "data" not in data or "verses" not in data["data"]:
                raise Exception("Invalid response")

            verses = data["data"]["verses"]
            surah_name = data["data"]["name"]["short"]

            verse = next((v for v in verses if v["number"]["inSurah"] == ayah_num), None)
            if not verse:
                raise Exception("Ayah not found")

            text = verse["text"]["arab"]
            audio_url = verse["audio"]["primary"]

            msg_text = f"📖 {surah_name} - الآية {ayah_num}\n\n{text}"

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🔁 آية عشوائية أخرى", callback_data="random_ayah"),
                InlineKeyboardButton("⭐ أضف إلى المفضلة", callback_data=f"fav_ayah:{verse['number']['inQuran']}:{text[:40]}")
            )
            
            # أزرار التنقل بين الآيات
            markup.row(
                InlineKeyboardButton("◀️ السابقة", callback_data=f"nav_ayah:{surah_num}:{ayah_num-1}"),
                InlineKeyboardButton("▶️ التالية", callback_data=f"nav_ayah:{surah_num}:{ayah_num+1}")
            )

            if edit and message:
                bot.edit_message_text(msg_text, chat_id, message.message_id, reply_markup=markup)
                bot.send_audio(chat_id, audio_url)
            else:
                bot.send_message(chat_id, msg_text, reply_markup=markup)
                bot.send_audio(chat_id, audio_url)

        except ValueError:
            bot.send_message(chat_id, "❌ رقم السورة يجب أن يكون بين 1 و114")
        except Exception as e:
            print(f"[ERROR] Send Ayah: {e}")
            bot.send_message(chat_id, "❌ تعذر جلب الآية. تأكد من صحة رقم السورة والآية.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_ayah:"))
    def add_to_favorites(call):
        parts = call.data.split(":", 2)
        ayah_number = parts[1]
        snippet = parts[2]
        content = f"آية رقم {ayah_number}\n{snippet}..."
        add_to_fav(call.from_user.id, "ayah", content)
        bot.answer_callback_query(call.id, "✅ تم الحفظ في المفضلة.")
        
    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav_ayah:"))
    def navigate_ayah(call):
        _, surah_num, ayah_num = call.data.split(":")
        send_ayah(call.message.chat.id, surah_num, ayah_num, call.message, edit=True)

def handle_callbacks(bot):
    pass
