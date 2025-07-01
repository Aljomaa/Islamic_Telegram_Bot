import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
import random
import logging

# تهيئة نظام تسجيل الأخطاء
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تعريف API الأساسي (البديل الموثوق)
API_BASE = "https://api.alquran.cloud/v1"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def register(bot):
    @bot.message_handler(commands=['quran', 'قرآن'])
    def show_main_quran_menu(msg):
        """القائمة الرئيسية للقرآن الكريم"""
        try:
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("📖 تصفح السور", callback_data="browse_quran"),
                InlineKeyboardButton("🕋 آية عشوائية", callback_data="random_ayah")
            )
            markup.row(
                InlineKeyboardButton("🔍 تفسير آية", callback_data="tafsir_menu"),
                InlineKeyboardButton("🗃 المفضلة", callback_data="favorite_verses")
            )
            bot.send_message(msg.chat.id, "🌙 القرآن الكريم - اختر أحد الخيارات:", reply_markup=markup)
        except Exception as e:
            logger.error(f"Error in main menu: {str(e)}", exc_info=True)
            bot.send_message(msg.chat.id, "❌ حدث خطأ في عرض القائمة الرئيسية")

    @bot.callback_query_handler(func=lambda call: call.data == "browse_quran")
    def ask_surah_number(call):
        """طلب رقم السورة من المستخدم"""
        try:
            bot.send_message(call.message.chat.id, "📖 الرجاء إدخال رقم السورة (1-114):")
            bot.register_next_step_handler(call.message, process_surah_number)
        except Exception as e:
            logger.error(f"Error asking surah number: {str(e)}", exc_info=True)
            bot.send_message(call.message.chat.id, "❌ حدث خطأ في طلب رقم السورة")

    def process_surah_number(msg):
        """معالجة رقم السورة المدخل"""
        try:
            surah_num = int(msg.text.strip())
            if 1 <= surah_num <= 114:
                send_surah_info(msg.chat.id, surah_num)
            else:
                bot.send_message(msg.chat.id, "⚠️ رقم السورة يجب أن يكون بين 1 و114")
        except ValueError:
            bot.send_message(msg.chat.id, "❌ الرجاء إدخال رقم صحيح بين 1 و114")
        except Exception as e:
            logger.error(f"Error processing surah number: {str(e)}", exc_info=True)
            bot.send_message(msg.chat.id, "❌ حدث خطأ في معالجة رقم السورة")

    def send_surah_info(chat_id, surah_num, message_id=None):
        """إرسال معلومات السورة المحددة"""
        try:
            res = requests.get(
                f"{API_BASE}/surah/{surah_num}/ar.alafasy",
                headers=HEADERS,
                timeout=15
            )
            res.raise_for_status()
            data = res.json()

            if not data.get('data'):
                return bot.send_message(chat_id, "❌ لا توجد بيانات للسورة")

            surah = data['data']
            first_ayah = surah['ayahs'][0]

            text = f"📖 سورة {surah['name']} ({surah['englishName']})\n"
            text += f"عدد الآيات: {surah['numberOfAyahs']}\n"
            text += f"النوع: {surah['revelationType']}\n\n"
            text += f"الآية 1:\n{first_ayah['text']}"

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🔢 التالية", callback_data=f"select_ayah:{surah_num+1}"),
                InlineKeyboardButton("🎧 استماع", callback_data=f"listen:{surah_num}:1")
            )
            markup.row(
                InlineKeyboardButton("🔄 آية عشوائية", callback_data=f"random_surah:{surah_num}"),
                InlineKeyboardButton("🏠 الرئيسية", callback_data="quran_main")
            )

            if message_id:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, text, reply_markup=markup)

        except requests.exceptions.RequestException as e:
            logger.error(f"API Request failed: {str(e)}", exc_info=True)
            bot.send_message(chat_id, "❌ تعذر الاتصال بخادم القرآن. حاول لاحقاً.")
        except Exception as e:
            logger.error(f"Error showing surah info: {str(e)}", exc_info=True)
            bot.send_message(chat_id, "❌ حدث خطأ في عرض بيانات السورة")

    @bot.callback_query_handler(func=lambda call: call.data == "random_ayah")
    def send_random_verse(call):
        """إرسال آية عشوائية من القرآن"""
        try:
            surah_num = random.randint(1, 114)
            res = requests.get(
                f"{API_BASE}/surah/{surah_num}/ar.alafasy",
                headers=HEADERS,
                timeout=10
            )
            res.raise_for_status()
            data = res.json()
            
            verses = data['data']['ayahs']
            ayah = random.choice(verses)
            
            send_verse_details(
                chat_id=call.message.chat.id,
                surah_num=surah_num,
                ayah_num=ayah['numberInSurah'],
                message_id=call.message.message_id,
                edit=True
            )
            
        except Exception as e:
            logger.error(f"Error getting random verse: {str(e)}", exc_info=True)
            bot.send_message(call.message.chat.id, "❌ تعذر جلب آية عشوائية. حاول لاحقاً.")

    def send_verse_details(chat_id, surah_num, ayah_num, message_id=None, edit=False):
        """إرسال تفاصيل آية محددة"""
        try:
            # التحقق من المدخلات
            surah_num = int(surah_num)
            ayah_num = int(ayah_num)
            
            if not (1 <= surah_num <= 114):
                return bot.send_message(chat_id, "❌ رقم السورة يجب أن يكون بين 1 و114")

            # جلب بيانات السورة
            res = requests.get(
                f"{API_BASE}/surah/{surah_num}/ar.alafasy",
                headers=HEADERS,
                timeout=15
            )
            res.raise_for_status()
            data = res.json()
            
            if not data.get('data'):
                return bot.send_message(chat_id, "❌ لا توجد بيانات للسورة")
                
            surah = data['data']
            verses = surah['ayahs']
            
            # البحث عن الآية المطلوبة
            ayah = next((v for v in verses if v['numberInSurah'] == ayah_num), None)
            if not ayah:
                return bot.send_message(chat_id, f"❌ الآية رقم {ayah_num} غير موجودة في السورة")
            
            # إعداد نص الرسالة
            text = f"📖 {surah['name']} ({surah['englishName']})\n"
            text += f"الآية {ayah_num}\n\n{ayah['text']}"
            
            # إعداد الأزرار
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🔁 آية أخرى", callback_data="random_ayah"),
                InlineKeyboardButton("⭐ حفظ", callback_data=f"fav_{surah_num}_{ayah_num}")
            )
            
            # أزرار التنقل
            nav_buttons = []
            if ayah_num > 1:
                nav_buttons.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"nav_{surah_num}_{ayah_num-1}"))
            if ayah_num < len(verses):
                nav_buttons.append(InlineKeyboardButton("▶️ التالية", callback_data=f"nav_{surah_num}_{ayah_num+1}"))
            
            if nav_buttons:
                markup.row(*nav_buttons)
            
            markup.row(InlineKeyboardButton("🏠 الرئيسية", callback_data="quran_main"))
            
            # إرسال الرسالة
            if edit and message_id:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, text, reply_markup=markup)
                
            # إرسال الصوت
            bot.send_audio(chat_id, ayah['audio'])
                
        except ValueError:
            bot.send_message(chat_id, "❌ يجب إدخال أرقام صحيحة فقط")
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request failed: {str(e)}", exc_info=True)
            bot.send_message(chat_id, "❌ تعذر الاتصال بالخادم. حاول لاحقاً.")
        except Exception as e:
            logger.error(f"Error showing verse: {str(e)}", exc_info=True)
            bot.send_message(chat_id, "❌ حدث خطأ في عرض الآية")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_"))
    def add_to_favorites(call):
        """إضافة آية إلى المفضلة"""
        try:
            _, surah_num, ayah_num = call.data.split("_")
            surah_num = int(surah_num)
            ayah_num = int(ayah_num)
            
            res = requests.get(
                f"{API_BASE}/surah/{surah_num}/ar.alafasy",
                headers=HEADERS,
                timeout=10
            )
            res.raise_for_status()
            data = res.json()
            
            verse = next((v for v in data['data']['ayahs'] if v['numberInSurah'] == ayah_num), None)
            
            if verse:
                content = {
                    'type': 'verse',
                    'surah': data['data']['name'],
                    'number': ayah_num,
                    'text': verse['text'],
                    'audio': verse['audio']
                }
                add_to_fav(call.from_user.id, content)
                bot.answer_callback_query(call.id, "✅ تمت الإضافة إلى المفضلة")
            else:
                bot.answer_callback_query(call.id, "❌ تعذر العثور على الآية")
                
        except Exception as e:
            logger.error(f"Error adding favorite: {str(e)}", exc_info=True)
            bot.answer_callback_query(call.id, "❌ فشلت الإضافة إلى المفضلة")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("nav_"))
    def navigate_verses(call):
        """التنقل بين الآيات"""
        try:
            _, surah_num, ayah_num = call.data.split("_")
            send_verse_details(
                chat_id=call.message.chat.id,
                surah_num=surah_num,
                ayah_num=ayah_num,
                message_id=call.message.message_id,
                edit=True
            )
        except Exception as e:
            logger.error(f"Error navigating: {str(e)}", exc_info=True)
            bot.answer_callback_query(call.id, "❌ تعذر التنقل بين الآيات")

    @bot.callback_query_handler(func=lambda call: call.data == "quran_main")
    def back_to_main(call):
        """العودة للقائمة الرئيسية"""
        try:
            show_main_quran_menu(call.message)
        except Exception as e:
            logger.error(f"Error returning to main: {str(e)}", exc_info=True)
            bot.send_message(call.message.chat.id, "❌ تعذر العودة للقائمة الرئيسية")

def handle_callbacks(bot):
    """معالجة الردود الإضافية"""
    pass
