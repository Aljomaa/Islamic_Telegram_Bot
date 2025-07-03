from pymongo import MongoClient
from config import MONGO_URI
from bson import ObjectId
from datetime import datetime

client = MongoClient(MONGO_URI)
db = client["islamic_bot"]

user_col = db["users"]
comp_col = db["complaints"]
admin_col = db["admins"]

# ✅ تسجيل المستخدم الجديد
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

# 🕌 الموقع والتوقيت
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

# 🔔 الإشعارات العامة
def user_notifications_enabled(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("notifications_enabled", True) if user else True

def enable_notifications(user_id):
    user_col.update_one({"_id": user_id}, {"$set": {"notifications_enabled": True}})

def disable_notifications(user_id):
    user_col.update_one({"_id": user_id}, {"$set": {"notifications_enabled": False}})

# 🔁 إعدادات التذكير المخصصة
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

# ⭐ نظام المفضلة
def add_to_fav(user_id, type_, content):
    user_col.update_one(
        {"_id": user_id},
        {"$push": {"favorites": {"type": type_, "content": content}}},
        upsert=True
    )

def get_user_favs(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("favorites", []) if user else []

# 🎧 القارئ المفضل
def get_user_reciter(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("reciter") if user else None

def set_user_reciter(user_id, reciter):
    user_col.update_one(
        {"_id": user_id},
        {"$set": {"reciter": reciter}},
        upsert=True
    )

# 🧾 الشكاوى والاقتراحات
def add_complaint(msg, type_):
    media_type = None
    file_id = None

    if msg.text:
        content = msg.text
        media_type = 'text'
    elif msg.photo:
        content = msg.caption or ""
        media_type = 'photo'
        file_id = msg.photo[-1].file_id
    elif msg.voice:
        content = msg.caption or ""
        media_type = 'voice'
        file_id = msg.voice.file_id
    elif msg.video:
        content = msg.caption or ""
        media_type = 'video'
        file_id = msg.video.file_id
    elif msg.sticker:
        content = ""
        media_type = 'sticker'
        file_id = msg.sticker.file_id
    else:
        return False

    comp_col.insert_one({
        "user_id": msg.from_user.id,
        "username": msg.from_user.username or "غير معروف",
        "full_name": msg.from_user.full_name or "غير معروف",
        "text": content,
        "media_type": media_type,
        "file_id": file_id,
        "status": "open",
        "type": type_,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    return True

def get_complaints():
    return list(comp_col.find({"status": "open"}))

def get_all_complaints(filter_by=None):
    query = {}
    if filter_by:
        query.update(filter_by)
    return list(comp_col.find(query).sort("_id", -1))

def update_complaint_status(comp_id, status="closed"):
    comp_col.update_one({"_id": ObjectId(comp_id)}, {"$set": {"status": status}})

def reply_to_complaint(comp_id, reply_text, bot=None):
    comp = comp_col.find_one({"_id": ObjectId(comp_id)})
    if not comp:
        return False
    user_id = comp["user_id"]
    try:
        message = f"📩 رد الإدارة على {'الشكوى' if comp['type'] == 'complaint' else 'الاقتراح'}:\n\n{reply_text}"
        if bot:
            bot.send_message(user_id, message)
        else:
            from loader import bot as default_bot
            default_bot.send_message(user_id, message)
        update_complaint_status(comp_id, "closed")
        return True
    except:
        return False

# 📊 إحصائيات البوت
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

# 📢 الرسائل الجماعية
def get_all_user_ids():
    return [doc["_id"] for doc in user_col.find({}, {"_id": 1})]

def broadcast_message(bot, message_text):
    for user_id in get_all_user_ids():
        try:
            bot.send_message(user_id, message_text)
        except:
            continue

# 👤 نظام المشرفين (Admins)
def is_admin(user_id_or_username):
    query = {"$or": [{"_id": user_id_or_username}, {"username": str(user_id_or_username)}]}
    admin = admin_col.find_one(query)
    return bool(admin)

def add_admin(identifier):
    try:
        if identifier.isdigit():
            _id = int(identifier)
            username = None
        else:
            _id = identifier
            username = identifier

        if admin_col.find_one({"_id": _id}):
            return False

        admin_col.insert_one({
            "_id": _id,
            "username": username
        })
        return True
    except:
        return False

def remove_admin(identifier):
    try:
        result = admin_col.delete_one({"$or": [{"_id": identifier}, {"username": identifier}]})
        return result.deleted_count > 0
    except:
        return False

def get_admins():
    return list(admin_col.find({}))
