import requests

def register(bot):
    @bot.message_handler(commands=['quran'])
    def ask_surah(msg):
        bot.send_message(msg.chat.id, "📖 اكتب رقم السورة (1 إلى 114):")
        bot.register_next_step_handler(msg, get_surah)

    def get_surah(msg):
        try:
            surah_number = int(msg.text.strip())
            if 1 <= surah_number <= 114:
                url = f"https://api.alquran.cloud/v1/surah/{surah_number}/ar"
                res = requests.get(url).json()

                if res["status"] == "OK":
                    surah = res["data"]
                    text = f"📖 سورة {surah['englishName']} ({surah['name']})\n\n"

                    for ayah in surah['ayahs']:
                        text += f"{ayah['numberInSurah']}. {ayah['text']}\n"

                    # Telegram message max length = 4096
                    for i in range(0, len(text), 4000):
                        bot.send_message(msg.chat.id, text[i:i+4000])
                else:
                    bot.send_message(msg.chat.id, "❌ تعذر جلب السورة من API.")
            else:
                bot.send_message(msg.chat.id, "❌ رقم السورة يجب أن يكون بين 1 و114.")
        except:
            bot.send_message(msg.chat.id, "❌ يرجى إرسال رقم صحيح للسورة.")

    @bot.message_handler(commands=['ayah'])
    def ask_ayah(msg):
        bot.send_message(msg.chat.id, "📖 اكتب الآية بصيغة `سورة:آية` (مثال: 2:255)")
        bot.register_next_step_handler(msg, get_ayah)

    def get_ayah(msg):
        try:
            parts = msg.text.strip().split(":")
            surah, ayah = int(parts[0]), int(parts[1])
            url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar"
            res = requests.get(url).json()

            if res["status"] == "OK":
                ayah_data = res["data"]
                text = f"📖 {ayah_data['surah']['name']} - {ayah_data['numberInSurah']}\n\n"
                text += f"{ayah_data['text']}\n\n"
                audio = ayah_data['audio']
                bot.send_message(msg.chat.id, text)
                bot.send_audio(msg.chat.id, audio)
            else:
                bot.send_message(msg.chat.id, "❌ لم يتم العثور على الآية.")
        except:
            bot.send_message(msg.chat.id, "❌ تأكد من كتابة الآية بصيغة صحيحة مثل 2:255")