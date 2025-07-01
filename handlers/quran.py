import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_to_fav
import random
import logging

# تهيئة نظام تسجيل الأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تعريف API الأساسي
API_BASE = "https://api.quran.gading.dev"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def register(bot):
    @bot.message_handler(commands=['quran', 'قرآن'])
    def show_main_quran_menu(msg):
        """عرض القائمة الرئيسية للقرآن الكريم"""
        try:
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("📖 تصفح السور", callback_data="browse_quran"),
                InlineKeyboardButton("🕋 آية عشوائية", callback_data="random_ayah")
            )
            markup.row(
                InlineKeyboardButton("🔍 تفسير آية", callback_data="tafsir_menu"),
                InlineKeyboardButton("🗃 السور المفضلة", callback_data="favorite_surahs")
            )
            bot.send_message(msg.chat.id, "🌙 القرآن الكريم - اختر أحد الخيارات:", reply_markup=markup)
        except Exception as e:
            logger.error(f"Error in show_main_quran_menu: {e}")
            bot.send_message(msg.chat.id, "❌ حدث خطأ في عرض القائمة الرئيسية")

    @bot.callback_query_handler(func=lambda call: call.data == "browse_quran")
    def ask_surah_number(call):
        """طلب رقم السورة من المستخدم"""
        try:
            bot.send_message(call.message.chat.id, "📖 الرجاء إدخال رقم السورة (1-114):")
            bot.register_next_step_handler(call.message, process_surah_number)
        except Exception as e:
            logger.error(f"Error in ask_surah_number: {e}")
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
            logger.error(f"Error in process_surah_number: {e}")
            bot.send_message(msg.chat.id, "❌ حدث خطأ في معالجة رقم السورة")

    def send_surah_info(chat_id, surah_num, message_id=None):
        """إرسال معلومات السورة مع الآيات"""
        try:
            # التحقق من اتصال API أولاً
            test_res = requests.get(f"{API_BASE}/surah/1", timeout=5, headers=HEADERS)
            if test_res.status_code != 200:
                return bot.send_message(chat_id, "❌ خدمة القرآن غير متاحة حالياً، يرجى المحاولة لاحقاً")

            res = requests.get(f"{API_BASE}/surah/{surah_num}", timeout=15, headers=HEADERS)
            res.raise_for_status()
            data = res.json()

            if not data.get('data'):
                return bot.send_message(chat_id, "❌ لا توجد بيانات للسورة")

            surah = data['data']
            verses = surah['verses']
            first_ayah = verses[0]

            text = f"📖 سورة {surah['name']['arabic']} ({surah['name']['transliteration']})\n"
            text += f"عدد الآيات: {surah['numberOfVerses']}\n"
            text += f"النوع: {surah['revelation']['arabic']}\n\n"
            text += f"الآية 1:\n{first_ayah['text']['arab']}"

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🔢 اختر آية", callback_data=f"select_ayah:{surah_num}"),
                InlineKeyboardButton("🎧 استماع للسورة", callback_data=f"listen_surah:{surah_num}")
            )
            markup.row(
                InlineKeyboardButton("🔄 آية عشوائية من السورة", callback_data=f"random_from_surah:{surah_num}"),
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="quran_main_menu")
            )

            if message_id:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, text, reply_markup=markup)

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            bot.send_message(chat_id, "❌ تعذر الاتصال بخادم القرآن. حاول لاحقاً.")
        except Exception as e:
            logger.error(f"Error in send_surah_info: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ أثناء جلب بيانات السورة.")

    @bot.callback_query_handler(func=lambda call: call.data == "random_ayah")
    def send_random_ayah(call):
        """إرسال آية عشوائية من القرآن"""
        try:
            surah_num = random.randint(1, 114)
            res = requests.get(f"{API_BASE}/surah/{surah_num}", timeout=10, headers=HEADERS)
            res.raise_for_status()
            data = res.json()
            
            verses = data['data']['verses']
            ayah = random.choice(verses)
            
            send_ayah_details(
                call.message.chat.id,
                surah_num,
                ayah['number']['inSurah'],
                call.message.message_id,
                edit=True
            )
            
        except Exception as e:
            logger.error(f"Error in random_ayah: {e}")
            bot.send_message(call.message.chat.id, "❌ تعذر جلب آية عشوائية. حاول لاحقاً.")

    def send_ayah_details(chat_id, surah_num, ayah_num, message_id=None, edit=False):
        """إرسال تفاصيل آية معينة"""
        try:
            # التحقق من صحة المدخلات
            surah_num = int(surah_num)
            ayah_num = int(ayah_num)
            
            if not (1 <= surah_num <= 114):
                return bot.send_message(chat_id, "❌ رقم السورة يجب أن يكون بين 1 و114")

            # جلب بيانات السورة
            res = requests.get(f"{API_BASE}/surah/{surah_num}", timeout=15, headers=HEADERS)
            if res.status_code != 200:
                return bot.send_message(chat_id, "❌ تعذر جلب بيانات السورة")
                
            data = res.json()
            if not data.get('data'):
                return bot.send_message(chat_id, "❌ لا توجد بيانات للسورة")
                
            surah = data['data']
            verses = surah.get('verses', [])
            
            # البحث عن الآية المطلوبة
            found_ayah = None
            for ayah in verses:
                if int(ayah['number']['inSurah']) == ayah_num:
                    found_ayah = ayah
                    break
                    
            if not found_ayah:
                return bot.send_message(chat_id, f"❌ الآية رقم {ayah_num} غير موجودة في السورة")
                
            # إعداد الرسالة
            text = f"📖 {surah['name']['arabic']} - الآية {ayah_num}\n\n{found_ayah['text']['arab']}"
            
            # إعداد الأزرار
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🔁 عشوائي", callback_data="random_ayah"),
                InlineKeyboardButton("⭐ حفظ", callback_data=f"fav_{surah_num}:{ayah_num}")
            )
            
            # أزرار التنقل بين الآيات
            nav_buttons = []
            if ayah_num > 1:
                nav_buttons.append(InlineKeyboardButton("◀️ السابقة", callback_data=f"ayah_{surah_num}:{ayah_num-1}"))
            if ayah_num < len(verses):
                nav_buttons.append(InlineKeyboardButton("▶️ التالية", callback_data=f"ayah_{surah_num}:{ayah_num+1}"))
            
            if nav_buttons:
                markup.row(*nav_buttons)
            
            markup.row(InlineKeyboardButton("🏠 القائمة", callback_data="quran_main_menu"))
            
            # إرسال أو تعديل الرسالة
            if edit and message_id:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, text, reply_markup=markup)
                
            # إرسال الصوت
            bot.send_audio(chat_id, found_ayah['audio']['primary'])
                
        except ValueError:
            bot.send_message(chat_id, "❌ يجب إدخال أرقام صحيحة فقط")
        except Exception as e:
            logger.error(f"Error in send_ayah_details: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ غير متوقع أثناء جلب الآية")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fav_"))
    def add_favorite(call):
        """إضافة آية للمفضلة"""
        try:
            _, surah_num, ayah_num = call.data.split("_")
            surah_num = int(surah_num)
            ayah_num = int(ayah_num)
            
            res = requests.get(f"{API_BASE}/surah/{surah_num}", timeout=10, headers=HEADERS)
            res.raise_for_status()
            data = res.json()
            
            verse = next((v for v in data['data']['verses'] if v['number']['inSurah'] == ayah_num), None)
            
            if verse:
                content = f"{data['data']['name']['arabic']} - الآية {ayah_num}\n{verse['text']['arab'][:100]}"
                add_to_fav(call.from_user.id, "ayah", content)
                bot.answer_callback_query(call.id, "✅ تمت الإضافة إلى المفضلة")
            else:
                bot.answer_callback_query(call.id, "❌ تعذر العثور على الآية")
                
        except Exception as e:
            logger.error(f"Error in add_favorite: {e}")
            bot.answer_callback_query(call.id, "❌ فشلت الإضافة إلى المفضلة")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ayah_"))
    def navigate_ayah(call):
        """التنقل بين الآيات"""
        try:
            _, surah_num, ayah_num = call.data.split("_")
            send_ayah_details(
                call.message.chat.id,
                surah_num,
                ayah_num,
                call.message.message_id,
                edit=True
            )
        except Exception as e:
            logger.error(f"Error in navigate_ayah: {e}")
            bot.answer_callback_query(call.id, "❌ تعذر التنقل بين الآيات")

    @bot.callback_query_handler(func=lambda call: call.data == "quran_main_menu")
    def back_to_main(call):
        """العودة للقائمة الرئيسية"""
        try:
            show_main_quran_menu(call.message)
        except Exception as e:
            logger.error(f"Error in back_to_main: {e}")
            bot.send_message(call.message.chat.id, "❌ تعذر العودة للقائمة الرئيسية")

def handle_callbacks(bot):
    """معالجة الردود الإضافية"""
    pass
