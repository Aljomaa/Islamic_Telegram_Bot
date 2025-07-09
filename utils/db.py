from pymongo import MongoClient
from config import MONGO_URI, OWNER_ID
from bson import ObjectId
from datetime import datetime
from telebot import TeleBot

client = MongoClient(MONGO_URI)
db = client["islamic_bot"]

user_col = db["users"]
comp_col = db["complaints"]
admin_col = db["admins"]
khatmah_col = db["khatmah"]

# ✅ ربط كائن البوت لإرسال الرسائل لاحقًا
global_bot_instance: TeleBot = None
def set_bot_instance(bot):
    global global_bot_instance
    global_bot_instance = bot

# ✅ تسجيل المستخدم
def register_user(user):
    user_id = user.id if hasattr(user, 'id') else user
    full_name = user.full_name if hasattr(user, 'full_name') else "غير معروف"
    username = user.username if hasattr(user, 'username') else None
    user_col.update_one(
        {"_id": user_id},
        {
            "$set": {
                "full_name": full_name,
                "username": username,
                "notifications_enabled": True,
                "reminder_settings": {
                    "morning_adhkar": True,
                    "evening_adhkar": True,
                    "jumuah": True,
                    "prayer": True
                },
                "joined": datetime.utcnow()
            }
        },
        upsert=True
    )

# ⭐ المفضلة
def add_to_fav(user_id, type_, content):
    user_col.update_one(
        {"_id": user_id},
        {"$push": {"favorites": {"type": type_, "content": content}}},
        upsert=True
    )

def get_user_favs(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("favorites", []) if user else []

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

# 🔔 الإشعارات
def user_notifications_enabled(user_id):
    user = user_col.find_one({"_id": user_id})
    return user.get("notifications_enabled", True) if user else True

def enable_notifications(user_id):
    user_col.update_one({"_id": user_id}, {"$set": {"notifications_enabled": True}})

def disable_notifications(user_id):
    user_col.update_one({"_id": user_id}, {"$set": {"notifications_enabled": False}})

# 🔁 إعدادات التذكير
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

# 📝 الشكاوى
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

def get_all_complaints(filter_by=None):
    query = {}
    if filter_by:
        query.update(filter_by)
    return list(comp_col.find(query).sort("_id", -1))

def update_complaint_status(comp_id, status="closed"):
    comp_col.update_one({"_id": ObjectId(comp_id)}, {"$set": {"status": status}})

# 👤 المشرفين
def is_admin(user_id_or_username):
    try:
        if str(user_id_or_username) == str(OWNER_ID):
            return True
        query = {
            "$or": [
                {"_id": int(user_id_or_username)} if str(user_id_or_username).isdigit() else {"_id": user_id_or_username},
                {"username": str(user_id_or_username)}
            ]
        }
        return admin_col.find_one(query) is not None
    except:
        return False

def add_admin(identifier):
    try:
        user_doc = None
        if identifier.isdigit():
            identifier = int(identifier)
            user_doc = user_col.find_one({"_id": identifier})
        else:
            user_doc = user_col.find_one({"username": identifier})

        if not user_doc or admin_col.find_one({"_id": user_doc["_id"]}):
            return False
        admin_col.insert_one({
            "_id": user_doc["_id"],
            "username": user_doc.get("username")
        })
        return True
    except:
        return False

def remove_admin(identifier):
    try:
        if str(identifier) == str(OWNER_ID):
            return False
        if identifier.isdigit():
            _id = int(identifier)
            result = admin_col.delete_one({"_id": _id})
        else:
            result = admin_col.delete_one({"username": identifier})
        return result.deleted_count > 0
    except:
        return False

def get_admins():
    return list(admin_col.find({}))

# ✅ المسبحة
def get_misbaha_count(user_id):
    user = db.misbaha.find_one({"user_id": user_id})
    return user["count"] if user and "count" in user else 0

def update_misbaha_count(user_id, count):
    db.misbaha.update_one(
        {"user_id": user_id},
        {"$set": {"count": count}},
        upsert=True
    )

def reset_misbaha(user_id):
    db.misbaha.update_one(
        {"user_id": user_id},
        {"$set": {"count": 0}},
        upsert=True
    )

# 📘 ختمة القرآن
def get_active_khatmah():
    return khatmah_col.find_one({"status": "active"})

def assign_juz_to_user(user_id):
    khatmah = get_active_khatmah()
    if not khatmah:
        khatmah_number = khatmah_col.count_documents({}) + 1
        khatmah = {
            "number": khatmah_number,
            "status": "active",
            "participants": [],
            "created_at": datetime.utcnow()
        }
        khatmah_col.insert_one(khatmah)
        khatmah = get_active_khatmah()

    participants = khatmah["participants"]
    if any(p["user_id"] == user_id for p in participants):
        return next(p["juz"] for p in participants if p["user_id"] == user_id)

    if len(participants) >= 30:
        khatmah_col.update_one({"_id": khatmah["_id"]}, {"$set": {"status": "full"}})
        return None

    juz_number = len(participants) + 1
    participant = {
        "user_id": user_id,
        "juz": juz_number,
        "status": "assigned",
        "joined_at": datetime.utcnow()
    }
    khatmah_col.update_one(
        {"_id": khatmah["_id"]},
        {"$push": {"participants": participant}}
    )

    if len(participants) + 1 == 30:
        khatmah_col.update_one({"_id": khatmah["_id"]}, {"$set": {"status": "full"}})
        start_khatmah()

    return juz_number

def start_khatmah():
    khatmah_number = khatmah_col.count_documents({}) + 1
    khatmah_col.insert_one({
        "number": khatmah_number,
        "status": "active",
        "participants": [],
        "created_at": datetime.utcnow()
    })
    notify_khatmah_started(khatmah_number)

def get_user_juz(user_id):
    khatmah = khatmah_col.find_one({"participants.user_id": user_id}, {"participants.$": 1})
    if khatmah and khatmah.get("participants"):
        return khatmah["participants"][0]["juz"]
    return None

def get_khatmah_number(user_id):
    khatmah = khatmah_col.find_one({"participants.user_id": user_id}, {"number": 1})
    return khatmah["number"] if khatmah else None

def get_khatmah_status(user_id):
    khatmah = khatmah_col.find_one({"participants.user_id": user_id}, {"participants.$": 1})
    if khatmah:
        return khatmah.get("status", "unknown") == "completed"
    return False

def get_juz_status(user_id):
    khatmah = khatmah_col.find_one({"participants.user_id": user_id}, {"participants.$": 1})
    if khatmah and khatmah.get("participants"):
        return khatmah["participants"][0]["status"] == "completed"
    return False

def mark_juz_completed(user_id):
    khatmah_col.update_one(
        {"participants.user_id": user_id},
        {"$set": {"participants.$.status": "completed"}}
    )
    khatmah = khatmah_col.find_one({"participants.user_id": user_id})
    if not khatmah:
        return

    participants = khatmah.get("participants", [])
    if all(p["status"] == "completed" for p in participants):
        khatmah_col.update_one({"_id": khatmah["_id"]}, {"$set": {"status": "completed"}})
        notify_khatmah_completed(khatmah["number"])

def get_users_in_khatmah(number):
    khatmah = khatmah_col.find_one({"number": number})
    return khatmah.get("participants", []) if khatmah else []

# ✅ إشعارات
def notify_khatmah_started(khatmah_number):
    khatmah = khatmah_col.find_one({"number": khatmah_number})
    if not khatmah or not khatmah.get("participants"):
        return

    for p in khatmah["participants"]:
        try:
            global_bot_instance.send_message(
                p["user_id"],
                f"📘 بدأت ختمة رقم {khatmah_number}\n"
                "نذكّركم بقراءة الجزء المخصص لكم بدءًا من الآن وحتى 24 ساعة كحد أقصى.\n"
                "وفقكم الله وبارك فيكم ❤️"
            )
        except:
            continue

def notify_khatmah_completed(khatmah_number):
    khatmah = khatmah_col.find_one({"number": khatmah_number})
    if not khatmah or not khatmah.get("participants"):
        return

    for p in khatmah["participants"]:
        try:
            global_bot_instance.send_message(
                p["user_id"],
                f"🎉 تهانينا! لقد أتممتم ختمة رقم {khatmah_number} بنجاح وفي وقت مثالي!\n"
                "🤲 نسأل الله أن يتقبل منكم، ويجعلكم من أهل القرآن وخاصته."
            )
        except:
            continue

# 📊 إحصائيات البوت
def get_bot_stats():
    return {
        "users": user_col.count_documents({}),
        "admins": admin_col.count_documents({}),
        "complaints": comp_col.count_documents({}),
        "khatmah": khatmah_col.count_documents({}),
        "active_khatmah": khatmah_col.count_documents({"status": "active"})
    }

# 🆔 جلب معرفات المستخدمين للبث الجماعي
def get_all_user_ids():
    return [user["_id"] for user in user_col.find({}, {"_id": 1})]
