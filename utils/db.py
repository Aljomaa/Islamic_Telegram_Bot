from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["islamic_bot"]

# جداول/Collections
user_col = db["users"]        # المستخدمين والمفضلات
comp_col = db["complaints"]   # الشكاوى والاقتراحات