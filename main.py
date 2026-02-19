import random
import re
import logging
import os
import asyncio
import json
import threading
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask

# --- إعدادات Flask لضمان استمرارية البوت ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    web_app.run(host='0.0.0.0', port=os.getenv("PORT", 7860))

# --- الإعدادات الثابتة ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "bot_data.json"

# --- قاموس القوانين المحدث بناءً على الدستور الجديد ---
DETAILED_LAWS = {
    "قوائم": """⚖️ قوانين القوائم والنجم والحاسم:
1️⃣ يمنع كتابة النجم والحاسم في فوز القوائم.
2️⃣ إذا كان الحاسم For Free لا يحتسب، ويتم اختيار الشخص الذي قبله.
3️⃣ المنشن للحكم إلزامي (خلال 30 دقيقة)، وبدونه تعتبر القائمة لاغية.
4️⃣ يمنع جدولة القوائم (إرسالها والقائد غير متصل).""",

    "سكربت": """⚖️ قوانين السكربت:
⬆️ طاقات 92 أو أقل = سكربت (حتى لو ميسي).
⬆️ طاقات أعلى من 92 = ليس سكربت (باستثناء بدون وجه).
⬆️ الاعتراض في بداية المباراة فقط (خروج فوري مع دليل).
⬆️ تغيير الأسلوب أو أماكن اللاعبين في المنتصف لا يعتبر سكربت.""",

    "وقت": """⚖️ توقيت المواجهات:
⏰ الوقت الرسمي: 9 صباحاً حتى 1 صباحاً.
🔥 المواجهة العادية: 48 ساعة (يومين).
🔥 النهائي/الدوري: 72 ساعة (3 أيام).
🔥 التمديد: يوم واحد للأدوار العادية، يومين لنصف النهائي والنهائي.""",

    "تواجد": """⚖️ قوانين التواجد:
🤔 غياب 20 ساعة بدون اتفاق = تبديل مباشر.
🤔 وضع تفاعل (Reaction) على الموعد يعتبر اتفاقاً.
🤔 الرد خلال 10 دقائق بدون تحديد موعد يعتبر تهرباً (تبديل مباشر).""",

    "تصوير": """⚖️ قوانين التصوير (للآيفون):
1️⃣ التصوير في البداية فقط.
2️⃣ فيديو يشمل (روم المحادثة + الرقم التسلسلي من "حول الهاتف").
3️⃣ إرسال التصوير متاح في أي وقت (بداية أو نهاية).""",

    "انتقالات": """⚖️ قوانين الانتقالات:
📺 مسموحة فقط يومي (الخميس والجمعة).
🚫 أي انتقال في أيام أخرى يعتبر غير رسمي ويتم تبديل اللاعب فوراً.""",

    "عقود": """⚖️ قوانين العقود:
🤔 أقصى حد للمسؤولين: 8 قادة (التاسع وهمي ويطرد).
🤔 الفسخ حصراً من القادة المسجلين.
🤔 الاعتراض بعد المباراة: الخيار للخصم (سحب نقطة أو استكمال).""",
    
    "سب": """⚖️ قوانين السب:
🚫 سب الأهل/الكفر = طرد وحظر.
🚫 السب في الخاص أثناء المواجهة = تبديل وحظر (يتطلب دليل فيديو لليوزر والشات)."""
}

BAN_WORDS = ["كسمك", "كسمه", "كسختك"]

# مخازن البيانات
wars = {}
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}
original_msg_store = {}

def save_data():
    data = {"wars": wars, "clans_mgmt": clans_mgmt, "user_warnings": user_warnings, "admin_warnings": admin_warnings}
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e: print(f"Error saving: {e}")

def load_data():
    global wars, clans_mgmt, user_warnings, admin_warnings
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                wars = {int(k): v for k, v in data.get("wars", {}).items()}
                clans_mgmt = {int(k): v for k, v in data.get("clans_mgmt", {}).items()}
                user_warnings = {int(k): v for k, v in data.get("user_warnings", {}).items()}
                admin_warnings = {int(k): v for k, v in data.get("admin_warnings", {}).items()}
        except Exception as e: print(f"Error loading: {e}")

def to_emoji(num):
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    return "".join(dic.get(c, c) for c in str(num))

def clean_text(text):
    if not text: return ""
    return text.lower().replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')

async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    cid, msg, mid, user = update.effective_chat.id, update.message.text, update.message.message_id, update.effective_user
    msg_cleaned = clean_text(msg)
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"
    
    original_msg_store[mid] = msg
    super_admins = ["mwsa_20", "levil_8"]
    is_referee = (user.username in super_admins)

    # --- التحقق من يوم الانتقالات ---
    if "انتقال" in msg_cleaned:
        current_day = datetime.now().strftime('%A') # الحصول على اسم اليوم بالإنجليزية
        if current_day not in ["Thursday", "Friday"] and not is_referee:
            await update.message.reply_text("⚠️ تنبيه: الانتقالات مسموحة فقط يومي الخميس والجمعة!")

    # --- الرد على القوانين ---
    if f"@{context.bot.username}" in msg or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id):
        for keyword, law_text in DETAILED_LAWS.items():
            if keyword in msg_cleaned:
                await update.message.reply_text(law_text, disable_web_page_preview=True)
                return

    # --- نظام الطرد الآلي ---
    for word in BAN_WORDS:
        if word in msg:
            if user.username not in super_admins:
                try: await context.bot.ban_chat_member(cid, user.id)
                except: pass
                await update.message.reply_text(f"🚫 طرد {u_tag} (سب/كفر).")
            return

    # --- بدء المواجهة ---
    if "CLAN" in msg.upper() and "VS" in msg.upper() and "+ 1" not in msg:
        parts = msg.upper().split(" VS ")
        c1_n = parts[0].replace("CLAN ", "").strip()
        c2_n = parts[1].replace("CLAN ", "").strip()
        wars[cid] = {"c1": {"n": c1_n, "s": 0, "p": [], "stats": [], "leader": None},
                     "c2": {"n": c2_n, "s": 0, "p": [], "stats": [], "leader": None},
                     "active": True, "mid": None, "matches": []}
        save_data()
        await update.message.reply_text(f"⚔️ بدأت الحرب: {c1_n} VS {c2_n}")
        return

    # --- تسجيل النقاط والنهاية ---
    if cid in wars and wars[cid]["active"]:
        w = wars[cid]
        if "+ 1" in msg.upper() or "+1" in msg.upper():
            players = re.findall(r'@\w+', msg)
            scores = re.findall(r'(\d+)', msg)
            win_k = "c1" if w["c1"]["n"].upper() in msg.upper() else ("c2" if w["c2"]["n"].upper() in msg.upper() else None)
            
            if win_k and len(players) >= 2 and len(scores) >= 2:
                u1, u2, sc1, sc2 = players[0], players[1], int(scores[0]), int(scores[1])
                p_win = u1 if sc1 > sc2 else u2
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2), "is_free": False})
                save_data()
                
                if w[win_k]["s"] >= 4:
                    w["active"] = False
                    real_p = [h for h in w[win_k]["stats"] if not h["is_free"]]
                    if real_p:
                        hasm = real_p[-1]["name"]
                        # النجم: أعلى فارق أهداف (سجل - استقبل)
                        star_data = max(real_p, key=lambda x: (x["goals"] - x["rec"]))
                        star = star_data["name"]
                        res = f"🎊 فوز {w[win_k]['n']} 🎊\n🎯 الحاسم: {hasm}\n⭐ النجم: {star} (سجل {star_data['goals']} استقبل {star_data['rec']})"
                    else: res = f"🎊 فوز إداري لـ {w[win_k]['n']}"
                    await update.message.reply_text(res)
                else:
                    await update.message.reply_text(f"✅ نقطة لـ {w[win_k]['n']}")

# --- تشغيل البوت ---
if __name__ == "__main__":
    load_data()
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    print("✅ البوت يعمل...")
    app.run_polling()
