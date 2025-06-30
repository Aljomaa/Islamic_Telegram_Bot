import os
from dotenv import load_dotenv

load_dotenv()

# توكن البوت
BOT_TOKEN = os.getenv("BOT_TOKEN")

# رابط الاتصال بقاعدة البيانات MongoDB
MONGO_URI = os.getenv("MONGO_URI")

# معرف الأدمن (أنت)
ADMIN_ID = 6849903309
