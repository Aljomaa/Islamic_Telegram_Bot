from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["islamic_bot"]

# المجموعات
user_col = db["users"]
comp_col = db["complaints"]

# ===============================
# 📌 الموقع الجغرافي + التنبيهات
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
    user_col.update_one({"_id": user_id}, {"$set": {"notifications_enabled": False}})

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
# 📊 الإحصائيات
# ===============================

def get_bot_stats():
    return {
        "total_users": user_col.count_documents({}),
        "total_favorites": user_col.aggregate([
            {"$project": {"count": {"$size": {"$ifNull": ["$favorites", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$count"}}}
        ]).next().get("total", 0),
        "total_complaints": comp_col.count_documents({})
    }

# ===============================
# 📬 نظام الشكاوى والاقتراحات
# ===============================

def save_complaint(user_id, text):
    comp_col.insert_one({"user_id": user_id, "text": text, "replied": False})

def get_complaints():
    return list(comp_col.find({"replied": False}))

def reply_to_complaint(complaint_id, reply_text):
    from bson.objectid import ObjectId
    complaint = comp_col.find_one({"_id": ObjectId(complaint_id)})
    if not complaint:
        return False

    user_id = complaint["user_id"]
    from loader import bot
    try:
        bot.send_message(user_id, f"📬 رد على شكواك:\n\n{reply_text}")
        comp_col.update_one({"_id": ObjectId(complaint_id)}, {"$set": {"replied": True}})
        return True
    except:
        return False

# ===============================
# 📢 إرسال جماعي
# ===============================

def get_all_users():
    return user_col.find({}, {"_id": 1})
