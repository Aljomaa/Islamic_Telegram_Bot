import requests
from telebot import types
from config import HADITH_API_KEY

BASE_URL = "https://api.sunnah.com/v1"
HEADERS = {"X-API-Key": HADITH_API_KEY}

def register(bot):
    @bot.message_handler(commands=['hadith'])
    def send_random_hadith(msg):
        books = ["bukhari", "muslim"]
        chosen = books[0]  # نختار البخاري مثلًا
        url = f"{BASE_URL}/collections/{chosen}/books/1/hadiths?limit=1"
        res = requests.get(url, headers=HEADERS).json()
        
        if "data" in res:
            h = res["data"][0]
            text = f"📜 حديث من صحيح {chosen.capitalize()}:\n\n{h['hadith'][0]['body']}"
            bot.send_message(msg.chat.id, text)
        else:
            bot.send_message(msg.chat.id, "❌ تعذر جلب الحديث.")

    @bot.message_handler(commands=['search_hadith'])
    def ask_search(msg):
        bot.send_message(msg.chat.id, "🔍 أرسل الكلمة التي تريد البحث عنها:")
        bot.register_next_step_handler(msg, do_search)

    def do_search(msg):
        query = msg.text.strip()
        url = f"{BASE_URL}/search?q={query}&limit=1"
        res = requests.get(url, headers=HEADERS).json()

        if "data" in res and res["data"]:
            h = res["data"][0]
            bot.send_message(msg.chat.id, f"📜 حديث:\n\n{h['body']}")
        else:
            bot.send_message(msg.chat.id, "❌ لم يتم العثور على نتائج.")