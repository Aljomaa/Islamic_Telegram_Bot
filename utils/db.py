from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["islamic_bot"]

user_col = db["users"]
comp_col = db["complaints"]

# ===============================
# ✅ تسجيل المستخدم الجديد
# ===============================
def register_user(user):
    user_id = user.id if hasattr(user, 'id') else user
    if not user_col.find_one({"_id": user_id}):
        user_col.insert_one({
            "_id": user_id,
            "notifications_enabled": True,
            "reminder_settings": {
                "morning_adhkar": True,
                "evening_adhkar": True,
                "jumuah": True,
                "prayer": True
            }
        })

# ===============================
# 🕌 الموقع والتوقيت
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
        return user["location"].get("lat"), user["location"].get("lon")
    return None, None

def get_user_timezone(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("timezone", "auto") if user else "auto"

# ===============================
# 🔔 الإشعارات العامة
# ===============================
def user_notifications_enabled(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("notifications_enabled", True) if user else True

def enable_notifications(user_id):
    user_col.update_one({"_id": user_id}, {"$set": {"notifications_enabled": True}})

def disable_notifications(user_id):
    user_col.update_one({"_id": user_id}, {"$set": {"notifications_enabled": False}})

# ===============================
# 🔁 إعدادات التذكير المخصصة
# ===============================
def get_user_reminder_settings(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("reminder_settings", {
        "morning_adhkar": True,
        "evening_adhkar": True,
        "jumuah": True,
        "prayer": True
    })

def update_reminder_setting(user_id, key, value: bool):
    user_col.update_one(
        {"_id": user_id},
        {"$set": {f"reminder_settings.{key}": value}},
        upsert=True
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
    return user.get("reciter") if user else None

def set_user_reciter(user_id, reciter):
    user_col.update_one(
        {"_id": user_id},
        {"$set": {"reciter": reciter}},
        upsert=True
    )

# ===============================
# 🧾 الشكاوى والاقتراحات
# ===============================
def get_complaints():
    return list(comp_col.find({"status": "open"}))

def reply_to_complaint(comp_id, reply_text, bot=None):
    comp = comp_col.find_one({"_id": comp_id})
    if not comp:
        return False
    user_id = comp["user_id"]
    try:
        if bot:
            bot.send_message(user_id, f"📩 رد الإدارة على شكواك:\n\n{reply_text}")
        else:
            from loader import bot as default_bot
            default_bot.send_message(user_id, f"📩 رد الإدارة على شكواك:\n\n{reply_text}")
        comp_col.update_one({"_id": comp_id}, {"$set": {"status": "closed"}})
        return True
    except:
        return False

# ===============================
# 📊 الإحصائيات
# ===============================
def get_bot_stats():
    total_favorites_agg = list(user_col.aggregate([
        {"$project": {"count": {"$size": {"$ifNull": ["$favorites", []]}}}},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}}
    ]))
    total_favorites = total_favorites_agg[0]["total"] if total_favorites_agg else 0

    return {
        "total_users": user_col.count_documents({}),
        "total_favorites": total_favorites,
        "total_complaints": comp_col.count_documents({})
    }

# ===============================
# 📢 الرسائل الجماعية
# ===============================
def get_all_user_ids():
    return [doc["_id"] for doc in user_col.find({}, {"_id": 1})]

def broadcast_message(bot, message_text):
    for user_id in get_all_user_ids():
        try:
            bot.send_message(user_id, message_text)
        except:
            continue
