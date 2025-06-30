from pymongo import MongoClient
from config import MONGO_URI
from datetime import datetime

client = MongoClient(MONGO_URI)
db = client["islamic_bot"]

# المجموعات
user_col = db["users"]        # بيانات المستخدمين
comp_col = db["complaints"]   # الشكاوى والاقتراحات

# ===============================
# 📍 إعداد الموقع والإشعارات
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
# 👤 تسجيل المستخدم
# ===============================

def register_user(user):
    user_col.update_one(
        {"_id": user.id},
        {
            "$setOnInsert": {
                "name": f"{user.first_name} {user.last_name or ''}".strip(),
                "username": user.username,
                "joined_at": datetime.utcnow(),
                "favorites": [],
                "notifications_enabled": False,
            },
            "$set": {
                "last_seen": datetime.utcnow()
            }
        },
        upsert=True
    )

# ===============================
# 📊 إحصائيات البوت
# ===============================

def get_bot_stats():
    total_users = user_col.count_documents({})
    with_notif = user_col.count_documents({"notifications_enabled": True})
    with_location = user_col.count_documents({"location": {"$exists": True}})
    total_complaints = comp_col.count_documents({})

    return {
        "total_users": total_users,
        "with_notif": with_notif,
        "with_location": with_location,
        "total_complaints": total_complaints
    }