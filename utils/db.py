from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["islamic_bot"]

# المجموعات
user_col = db["users"]        # بيانات المستخدمين
comp_col = db["complaints"]   # الشكاوى والاقتراحات

# ===============================
# 📍 الموقع والتوقيت والإشعارات
# ===============================

def set_user_location(user_id, lat, lon, timezone="auto"):
    user_col.update_one(
        {"_id": user_id},
        {"$set": {
            "location.lat": lat,
            "location.lon": lon,
            "timezone": timezone,
            "notifications_enabled": True
        }},
        upsert=True
    )

def get_user_location(user_id):
    user = user_col.find_one({"_id": user_id})
    if user and "location" in user:
        return user["location"]["lat"], user["location"]["lon"]
    return None, None

def get_user_timezone(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("timezone", "auto") if user else "auto"

def user_notifications_enabled(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("notifications_enabled", False) if user else False

def disable_notifications(user_id):
    user_col.update_one(
        {"_id": user_id},
        {"$set": {"notifications_enabled": False}}
    )

# ===============================
# ⭐ نظام المفضلة
# ===============================

def add_to_fav(user_id, type_, content):
    user_col.update_one(
        {"_id": user_id},
        {"$push": {"favorites": {"type": type_, "content": content}}},
        upsert=True
    )

def get_user_favs(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("favorites", []) if user else []

# ===============================
# 🎧 القارئ المفضل
# ===============================

def get_user_reciter(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("reciter") if user and "reciter" in user else None

def set_user_reciter(user_id, reciter):
    user_col.update_one(
        {"_id": user_id},
        {"$set": {"reciter": reciter}},
        upsert=True
    )

# ===============================
# 🧾 الشكاوى والاقتراحات
# ===============================

def save_complaint(user_id, complaint):
    comp_col.insert_one({
        "user_id": user_id,
        "message": complaint,
        "replies": []
    })

def get_complaints():
    return list(comp_col.find())

def reply_to_complaint(complaint_id, reply):
    comp_col.update_one(
        {"_id": complaint_id},
        {"$push": {"replies": reply}}
    )

# ===============================
# 📊 الإحصائيات
# ===============================

def register_user(user_id):
    user_col.update_one(
        {"_id": user_id},
        {"$setOnInsert": {"favorites": []}},
        upsert=True
    )

def get_bot_stats():
    total_users = user_col.count_documents({})
    total_complaints = comp_col.count_documents({})
    return total_users, total_complaints

# ===============================
# 📢 الرسائل الجماعية (Broadcast)
# ===============================

def get_all_user_ids():
    return [u["_id"] for u in user_col.find({}, {"_id": 1})]

def broadcast_message(bot, text):
    user_ids = get_all_user_ids()
    for uid in user_ids:
        try:
            bot.send_message(uid, text)
        except:
            continue
