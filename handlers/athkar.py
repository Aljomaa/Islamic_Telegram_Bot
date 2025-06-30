import requests
from telebot import types

API_URL = "https://adkar.hisnmuslim.com/api"

def register(bot):
    @bot.message_handler(commands=['athkar'])
    def list_categories(msg):
        res = requests.get(f"{API_URL}/categories").json()
        if "data" in res:
            categories = res["data"]
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for c in categories[:20]:  # نعرض أول 20 تصنيف فقط
                markup.add(types.KeyboardButton(c["title"]))
            bot.send_message(msg.chat.id, "📿 اختر نوع الأذكار:", reply_markup=markup)
            bot.register_next_step_handler(msg, send_athkar)
        else:
            bot.send_message(msg.chat.id, "❌ تعذر جلب الأذكار.")

    def send_athkar(msg):
        category = msg.text.strip()
        res = requests.get(f"{API_URL}/adkar?category={category}").json()

        if "data" in res and res["data"]:
            for z in res["data"]:
                text = f"📿 {z['content']}"
                if z.get("description"):
                    text += f"\n\n📌 {z['description']}"
                bot.send_message(msg.chat.id, text[:4096])
        else:
            bot.send_message(msg.chat.id, "❌ لم يتم العثور على أذكار لهذا التصنيف.", reply_markup=types.ReplyKeyboardRemove())