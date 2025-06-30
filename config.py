import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
HADITH_API_KEY = os.getenv("HADITH_API_KEY")
ADMIN_ID = 6849903309  # هذا رقمك