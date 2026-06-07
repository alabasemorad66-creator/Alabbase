from pyrogram import Client, filters, idle
from pyrogram.types import Message, CallbackQuery, ForceReply, InlineKeyboardMarkup as Markup, InlineKeyboardButton as Button
from pyrogram.errors import (
    ApiIdInvalid, PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired,
    SessionPasswordNeeded, PasswordHashInvalid, UserNotParticipant,
    ChatWriteForbidden, PeerIdInvalid
)
import os
from pyrolistener import Listener, exceptions
from asyncio import create_task, sleep, get_event_loop
from datetime import datetime, timedelta
from pytz import timezone
from typing import Union
import json

# ---------- إعدادات البوت (استخدم متغيرات بيئة آمنة) ----------
# يفضل وضع القيم التالية في ملف .env وقراءتها، لكن للتبسيط نستخدم متغيرات مباشرة مع تحذير.
API_ID = 123456  # ضع الـ API ID الخاص بك
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"
OWNER_ID = 8310839908  # ايدي المالك

# ---------- تهيئة العميل ----------
app = Client("autoPost", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
listener = Listener(client=app)
loop = get_event_loop()

# ---------- المتغيرات العامة ----------
users_db = "users.json"
channels_db = "channels.json"
users = {}
channels = []

# قاموس لمنع تكرار رسالة الاشتراك (المفتاح: user_id, القيمة: timestamp آخر تحذير)
last_warning = {}

# قاموس لتتبع مهام النشر النشطة
active_tasks = {}

# ---------- دوال قراءة وكتابة JSON ----------
def write(fp, data):
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def read(fp):
    if not os.path.exists(fp):
        if fp == channels_db:
            write(fp, [])
        else:
            write(fp, {})
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)

# تحميل البيانات
users = read(users_db)
channels = read(channels_db)

# ---------- دالة الاشتراك الإجباري المحسنة (بدون تكرار) ----------
async def check_subscription(message: Message):
    """تعيد True إذا كان المستخدم مشتركاً في كل القنوات، وإلا تعيد اسم أول قناة غير مشترك فيها.
       مع آلية منع التكرار: إذا أرسل تحذير خلال آخر 5 دقائق، تعيد None."""
    user_id = message.from_user.id
    now = datetime.now().timestamp()
    # منع الإزعاج
    if user_id in last_warning and (now - last_warning[user_id]) < 300:
        return None
    for ch in channels:
        try:
            await app.get_chat_member(ch, user_id)
        except UserNotParticipant:
            last_warning[user_id] = now
            return ch
    return True

# ---------- الأزرار الرئيسية ----------
home_markup = Markup([
    [Button("- حسابك -", callback_data="account")],
    [Button("- السوبرات الحالية -", callback_data="currentSupers"), Button("- إضافة سوبر -", callback_data="newSuper")],
    [Button("- تعيين المدة بين كل نشر -", callback_data="waitTime"), Button("- تعيين كليشة النشر -", callback_data="newCaption")],
    [Button("- إيقاف النشر -", callback_data="stopPosting"), Button("- بدء النشر -", callback_data="startPosting")]
])

# ---------- أوامر المستخدم ----------
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    sub_status = await check_subscription(message)
    if sub_status is None:
        return  # تم إرسال تحذير مؤخراً، لا نرسل مجدداً
    if isinstance(sub_status, str):
        await message.reply(f"⚠️ عذيراً، عليك الاشتراك في القناة أولاً:\nhttps://t.me/{sub_status}\nثم أعد إرسال /start")
        return
    # التعامل مع المستخدمين
    if str(user_id) == str(OWNER_ID):
        if str(user_id) not in users:
            users[str(user_id)] = {"vip": True}
            write(users_db, users)
    elif str(user_id) not in users:
        users[str(user_id)] = {"vip": False}
        write(users_db, users)
        await message.reply(f"❌ لا يمكنك استخدام هذا البوت. تواصل مع [المطور](tg://user?id={OWNER_ID}) لتفعيل الاشتراك.")
        return
    elif not users[str(user_id)].get("vip", False):
        await message.reply(f"❌ انتهت صلاحية الاشتراك. راسل [المطور](tg://user?id={OWNER_ID}) للتجديد.")
        return
    # رسالة الترحيب
    fname = message.from_user.first_name
    await message.reply(f"- مرحباً [{fname}](tg://settings) في بوت النشر التلقائي.\nتحكم عبر الأزرار أدناه:", reply_markup=home_markup)

@app.on_callback_query(filters.regex("^toHome$"))
async def to_home_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if str(user_id) != str(OWNER_ID) and (str(user_id) not in users or not users[str(user_id)].get("vip")):
        await callback.answer("انتهت صلاحية الاشتراك أو غير مسجل.", show_alert=True)
        return
    await callback.message.edit_text("الصفحة الرئيسية:", reply_markup=home_markup)

# ------------------- حساب المستخدم -------------------
@app.on_callback_query(filters.regex("^account$"))
async def account_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_vip(user_id):
        await callback.answer("غير مصرح لك.", show_alert=True)
        return
    markup = Markup([
        [Button("- تسجيل حساب -", callback_data="login"), Button("- تغيير الحساب -", callback_data="changeAccount")],
        [Button("- العودة -", callback_data="toHome")]
    ])
    await callback.message.edit_text("قسم الحساب:", reply_markup=markup)

async def is_vip(user_id):
    return (str(user_id) == str(OWNER_ID)) or (str(user_id) in users and users[str(user_id)].get("vip"))

# ------------------- تسجيل الدخول -------------------
@app.on_callback_query(filters.regex("^(login|changeAccount)$"))
async def login_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_vip(user_id):
        await callback.answer("غير مصرح.", show_alert=True)
        return
    if callback.data == "changeAccount" and users[str(user_id)].get("session") is None:
        await callback.answer("لم تسجل دخول بعد.", show_alert=True)
        return
    await callback.message.delete()
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="📞 أرسل رقم هاتفك (مثال: +9647700000000)\nأو /cancel للإلغاء",
            reply_markup=ForceReply(selective=True, placeholder="+xxxxxxxxxx"),
            timeout=30
        )
    except exceptions.TimeOut:
        await callback.message.reply("⏰ انتهى الوقت.", reply_markup=Markup([[Button("- رجوع -", callback_data="account")]]))
        return
    if ask.text == "/cancel":
        await ask.reply("تم الإلغاء.", reply_to_message_id=ask.id)
        return
    create_task(perform_registration(ask))

async def perform_registration(msg: Message):
    user_id = msg.from_user.id
    number = msg.text.strip()
    status_msg = await msg.reply("جاري تسجيل الدخول...")
    re_markup = Markup([[Button("🔁 إعادة المحاولة", callback_data="login"), Button("🏠 الرئيسية", callback_data="toHome")]])
    client_temp = Client("reg_" + str(user_id), in_memory=True, api_id=API_ID, api_hash=API_HASH)
    await client_temp.connect()
    try:
        sent_code = await client_temp.send_code(number)
    except PhoneNumberInvalid:
        await status_msg.edit_text("❌ رقم الهاتف غير صحيح.", reply_markup=re_markup)
        return
    try:
        code_ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="📲 أرسل الكود الذي تلقيته:",
            reply_markup=ForceReply(selective=True, placeholder="1 2 3 4 5 6"),
            timeout=120
        )
    except exceptions.TimeOut:
        await status_msg.edit_text("⏰ انتهى وقت الكود.", reply_markup=re_markup)
        return
    try:
        await client_temp.sign_in(number, sent_code.phone_code_hash, code_ask.text.replace(" ", ""))
    except PhoneCodeInvalid:
        await code_ask.reply("❌ كود خاطئ.", reply_markup=re_markup, reply_to_message_id=code_ask.id)
        return
    except PhoneCodeExpired:
        await code_ask.reply("❌ الكود منتهي.", reply_markup=re_markup, reply_to_message_id=code_ask.id)
        return
    except SessionPasswordNeeded:
        try:
            pass_ask = await listener.listen(
                from_id=user_id, chat_id=user_id,
                text="🔐 أدخل كلمة مرور التحقق بخطوتين:",
                reply_markup=ForceReply(selective=True, placeholder="كلمة المرور"),
                timeout=180
            )
        except exceptions.TimeOut:
            await status_msg.edit_text("⏰ انتهى وقت كلمة المرور.", reply_markup=re_markup)
            return
        try:
            await client_temp.check_password(pass_ask.text)
        except PasswordHashInvalid:
            await pass_ask.reply("❌ كلمة مرور خاطئة.", reply_markup=re_markup, reply_to_message_id=pass_ask.id)
            return
    session_str = await client_temp.export_session_string()
    await client_temp.disconnect()
    # حفظ الجلسة
    if str(user_id) not in users:
        users[str(user_id)] = {"vip": False}
    users[str(user_id)]["session"] = session_str
    write(users_db, users)
    await app.send_message(user_id, "✅ تم تسجيل الدخول بنجاح!", reply_markup=Markup([[Button("الصفحة الرئيسية", callback_data="toHome")]]))

# ------------------- إدارة السوبرات -------------------
@app.on_callback_query(filters.regex("^newSuper$"))
async def new_super_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_vip(user_id):
        await callback.answer("غير مصرح.", show_alert=True)
        return
    await callback.message.delete()
    re_markup = Markup([[Button("🔁 إعادة", callback_data="newSuper"), Button("🏠 الرئيسية", callback_data="toHome")]])
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="📎 أرسل رابط المجموعة أو معرفها (مثال: @username أو -100123456):\nأو /cancel للإلغاء",
            reply_markup=ForceReply(selective=True, placeholder="رابط أو معرف"),
            timeout=60
        )
    except exceptions.TimeOut:
        await callback.message.reply("⏰ انتهى الوقت.", reply_markup=re_markup)
        return
    if ask.text == "/cancel":
        await ask.reply("تم الإلغاء.", reply_to_message_id=ask.id)
        return
    # تحليل المدخل
    text = ask.text.strip()
    group_id = None
    link = None
    if text.startswith("-") and text[1:].isdigit():
        group_id = int(text)
    elif "t.me/" in text:
        link = text
        try:
            chat = await app.get_chat(text.split("/")[-1])
            group_id = chat.id
        except:
            await ask.reply("❌ لم أجد المجموعة. تأكد من الرابط.", reply_markup=re_markup, reply_to_message_id=ask.id)
            return
    else:
        # معرف بدون علامة ناقص
        try:
            group_id = int(text)
        except:
            await ask.reply("❌ الرابط أو المعرف غير صالح.", reply_markup=re_markup, reply_to_message_id=ask.id)
            return
    if group_id is None:
        await ask.reply("❌ فشل التعرف.", reply_markup=re_markup, reply_to_message_id=ask.id)
        return
    # التحقق من التكرار
    groups = users[str(user_id)].get("groups", [])
    if any(g["id"] == group_id for g in groups):
        await ask.reply("⚠️ هذه المجموعة موجودة بالفعل في قائمتك.", reply_markup=re_markup, reply_to_message_id=ask.id)
        return
    groups.append({"id": group_id, "link": link})
    users[str(user_id)]["groups"] = groups
    write(users_db, users)
    await ask.reply("✅ تمت الإضافة.", reply_markup=Markup([[Button("🏠 الرئيسية", callback_data="toHome")]]), reply_to_message_id=ask.id)

@app.on_callback_query(filters.regex("^currentSupers$"))
async def current_supers_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_vip(user_id):
        await callback.answer("غير مصرح.", show_alert=True)
        return
    groups = users[str(user_id)].get("groups", [])
    if not groups:
        await callback.answer("لا توجد سوبرات.", show_alert=True)
        return
    markup = []
    for g in groups:
        gid = g["id"]
        try:
            chat = await app.get_chat(gid)
            title = chat.title
        except:
            title = str(gid)
        markup.append([Button(title, callback_data=f"nosuper_{gid}"), Button("🗑", callback_data=f"delSuper_{gid}")])
    markup.append([Button("🏠 الرئيسية", callback_data="toHome")])
    await callback.message.edit_text("قائمة السوبرات:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^delSuper_(\d+)$"))
async def del_super_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_vip(user_id):
        await callback.answer("غير مصرح.", show_alert=True)
        return
    gid = int(callback.data.split("_")[1])
    groups = users[str(user_id)].get("groups", [])
    new_groups = [g for g in groups if g["id"] != gid]
    if len(new_groups) != len(groups):
        users[str(user_id)]["groups"] = new_groups
        write(users_db, users)
        await callback.answer("تم الحذف.")
    # تحديث العرض
    if not new_groups:
        await callback.message.edit_text("لا توجد سوبرات.", reply_markup=Markup([[Button("🏠 الرئيسية", callback_data="toHome")]]))
        return
    markup = []
    for g in new_groups:
        try:
            title = (await app.get_chat(g["id"])).title
        except:
            title = str(g["id"])
        markup.append([Button(title, callback_data=f"nosuper_{g['id']}"), Button("🗑", callback_data=f"delSuper_{g['id']}")])
    markup.append([Button("🏠 الرئيسية", callback_data="toHome")])
    await callback.message.edit_reply_markup(reply_markup=Markup(markup))

# ------------------- تعيين الكليشة والمدة -------------------
@app.on_callback_query(filters.regex("^newCaption$"))
async def new_caption_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_vip(user_id):
        await callback.answer("غير مصرح.", show_alert=True)
        return
    await callback.message.delete()
    re_markup = Markup([[Button("🔁 إعادة", callback_data="newCaption"), Button("🏠 الرئيسية", callback_data="toHome")]])
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="✏️ أرسل النص الجديد للكليشة (يمكنك استخدام HTML):\nأو /cancel للإلغاء",
            reply_markup=ForceReply(selective=True, placeholder="نص الكليشة"),
            timeout=120
        )
    except exceptions.TimeOut:
        await callback.message.reply("⏰ انتهى الوقت.", reply_markup=re_markup)
        return
    if ask.text == "/cancel":
        await ask.reply("تم الإلغاء.", reply_to_message_id=ask.id)
        return
    users[str(user_id)]["caption"] = ask.text
    write(users_db, users)
    await ask.reply("✅ تم حفظ الكليشة.", reply_markup=Markup([[Button("🏠 الرئيسية", callback_data="toHome")]]), reply_to_message_id=ask.id)

@app.on_callback_query(filters.regex("^waitTime$"))
async def wait_time_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_vip(user_id):
        await callback.answer("غير مصرح.", show_alert=True)
        return
    await callback.message.delete()
    re_markup = Markup([[Button("🔁 إعادة", callback_data="waitTime"), Button("🏠 الرئيسية", callback_data="toHome")]])
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="⏱️ أرسل المدة بين كل نشر (بالثواني):\nأو /cancel للإلغاء",
            reply_markup=ForceReply(selective=True, placeholder="مثال: 60"),
            timeout=120
        )
    except exceptions.TimeOut:
        await callback.message.reply("⏰ انتهى الوقت.", reply_markup=re_markup)
        return
    if ask.text == "/cancel":
        await ask.reply("تم الإلغاء.", reply_to_message_id=ask.id)
        return
    try:
        delay = int(ask.text)
        if delay < 5:
            await ask.reply("⚠️ المدة يجب أن تكون 5 ثوانٍ على الأقل.", reply_markup=re_markup, reply_to_message_id=ask.id)
            return
        users[str(user_id)]["waitTime"] = delay
        write(users_db, users)
        await ask.reply("✅ تم تعيين المدة.", reply_markup=Markup([[Button("🏠 الرئيسية", callback_data="toHome")]]), reply_to_message_id=ask.id)
    except ValueError:
        await ask.reply("❌ قيمة غير صحيحة.", reply_markup=re_markup, reply_to_message_id=ask.id)

# ------------------- بدء وإيقاف النشر -------------------
@app.on_callback_query(filters.regex("^startPosting$"))
async def start_posting_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_vip(user_id):
        await callback.answer("غير مصرح.", show_alert=True)
        return
    data = users.get(str(user_id))
    if not data or data.get("session") is None:
        await callback.answer("يجب تسجيل حساب أولاً.", show_alert=True)
        return
    if not data.get("groups"):
        await callback.answer("لا توجد سوبرات مضافة.", show_alert=True)
        return
    if data.get("posting", False):
        await callback.answer("النشر مفعل مسبقاً.", show_alert=True)
        return
    # منع مهمة مكررة
    if str(user_id) in active_tasks and not active_tasks[str(user_id)].done():
        await callback.answer("يوجد مهمة نشطة بالفعل.", show_alert=True)
        return
    data["posting"] = True
    write(users_db, users)
    task = create_task(posting_worker(user_id))
    active_tasks[str(user_id)] = task
    markup = Markup([[Button("⏹️ إيقاف النشر", callback_data="stopPosting"), Button("🏠 الرئيسية", callback_data="toHome")]])
    await callback.message.edit_text("▶️ بدأ النشر التلقائي.", reply_markup=markup)

@app.on_callback_query(filters.regex("^stopPosting$"))
async def stop_posting_cb(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_vip(user_id):
        await callback.answer("غير مصرح.", show_alert=True)
        return
    if not users.get(str(user_id), {}).get("posting", False):
        await callback.answer("النشر معطل مسبقاً.", show_alert=True)
        return
    users[str(user_id)]["posting"] = False
    write(users_db, users)
    markup = Markup([[Button("▶️ بدء النشر", callback_data="startPosting"), Button("🏠 الرئيسية", callback_data="toHome")]])
    await callback.message.edit_text("⏸️ تم إيقاف النشر.", reply_markup=markup)

# ------------------- دالة النشر الأساسية -------------------
async def posting_worker(user_id):
    try:
        user_id_str = str(user_id)
        while users.get(user_id_str, {}).get("posting", False):
            data = users[user_id_str]
            groups = data.get("groups", [])
            caption = data.get("caption")
            if not caption:
                users[user_id_str]["posting"] = False
                write(users_db, users)
                await app.send_message(user_id, "⛔ تم إيقاف النشر بسبب عدم وجود كليشة.", reply_markup=Markup([[Button("➕ تعيين كليشة", callback_data="newCaption")]]))
                break
            delay = data.get("waitTime", 60)
            # إنشاء عميل الجلسة
            client = Client(user_id_str, api_id=API_ID, api_hash=API_HASH, session_string=data["session"])
            await client.start()
            for group_obj in list(groups):
                if not users.get(user_id_str, {}).get("posting", False):
                    break
                gid = group_obj["id"]
                link = group_obj.get("link")
                try:
                    await client.send_message(gid, caption)
                except (ChatWriteForbidden, PeerIdInvalid, UserNotParticipant):
                    # محاولة الانضمام
                    joined = False
                    if link:
                        try:
                            await client.join_chat(link)
                            joined = True
                        except:
                            pass
                    if not joined:
                        try:
                            await client.join_chat(gid)
                            joined = True
                        except:
                            pass
                    if not joined:
                        try:
                            chat = await app.get_chat(gid)
                            if chat.invite_link:
                                await client.join_chat(chat.invite_link)
                                # تحديث الرابط
                                for idx, g in enumerate(users[user_id_str]["groups"]):
                                    if g["id"] == gid:
                                        users[user_id_str]["groups"][idx]["link"] = chat.invite_link
                                        write(users_db, users)
                                joined = True
                        except:
                            pass
                    if joined:
                        await client.send_message(gid, caption)
                    else:
                        await app.send_message(user_id, f"⚠️ تعذر الإرسال إلى {gid} أو الانضمام.")
                except Exception as e:
                    await app.send_message(user_id, f"❌ خطأ غير متوقع في {gid}: {e}")
            await client.stop()
            await sleep(delay)
    except Exception as e:
        print(f"Error in posting_worker for {user_id}: {e}")
    finally:
        if str(user_id) in active_tasks:
            del active_tasks[str(user_id)]
        if users.get(str(user_id), {}).get("posting"):
            users[str(user_id)]["posting"] = False
            write(users_db, users)

# ------------------- لوحة المالك (متقدمة) -------------------
def owner_only(func):
    async def wrapper(client, update):
        user_id = update.from_user.id if isinstance(update, (Message, CallbackQuery)) else None
        if user_id != OWNER_ID:
            await (update.reply if isinstance(update, Message) else update.answer)("👑 هذا الأمر خاص بالمالك فقط.", show_alert=True)
            return
        return await func(client, update)
    return wrapper

admin_markup = Markup([
    [Button("📊 الإحصائيات", callback_data="admin_stats"), Button("➕ تفعيل VIP", callback_data="admin_add_vip")],
    [Button("➖ إلغاء VIP", callback_data="admin_remove_vip"), Button("📢 إشعار عام", callback_data="admin_broadcast")],
    [Button("📋 قنوات الاشتراك", callback_data="admin_channels"), Button("⏱ المدة الافتراضية", callback_data="admin_default_delay")],
    [Button("🔁 إعادة تشغيل المهام", callback_data="admin_restart_tasks"), Button("🗑 مسح بيانات مستخدم", callback_data="admin_clear_user")],
    [Button("📜 سجل الأخطاء", callback_data="admin_logs"), Button("📈 تقرير النشاط", callback_data="admin_activity")],
    [Button("🔄 ترحيل الجلسات", callback_data="admin_migrate"), Button("🔐 حظر مستخدم", callback_data="admin_ban")],
    [Button("📋 نسخة احتياطية", callback_data="admin_backup"), Button("⚙️ إعدادات متقدمة", callback_data="admin_settings")],
    [Button("⏰ جدولة الإيقاف", callback_data="admin_schedule"), Button("📨 بث متعدد الوسائط", callback_data="admin_multibroadcast")],
    [Button("🗂 استيراد/تصدير", callback_data="admin_import_export"), Button("🔍 اختبار السوبرات", callback_data="admin_test_supers")],
    [Button("🛡 وضع الصيانة", callback_data="admin_maintenance"), Button("🔌 إيقاف البوت", callback_data="admin_stop")]
])

@app.on_message(filters.command("admin") & filters.private)
@owner_only
async def admin_panel(client: Client, message: Message):
    await message.reply("👑 لوحة تحكم المالك:", reply_markup=admin_markup)

@app.on_callback_query(filters.regex("^admin_"))
@owner_only
async def admin_callbacks(client: Client, callback: CallbackQuery):
    data = callback.data
    await callback.answer("جاري التنفيذ...", show_alert=False)
    if data == "admin_stats":
        total = len(users)
        vip = sum(1 for u in users.values() if u.get("vip"))
        await callback.message.edit_text(f"📊 الإحصائيات:\nإجمالي المستخدمين: {total}\nمستخدمي VIP: {vip}\nالقنوات المطلوبة: {len(channels)}", reply_markup=Markup([[Button("🔙 رجوع", callback_data="admin_back")]]))
    elif data == "admin_add_vip":
        await callback.message.delete()
        try:
            ask_id = await listener.listen(from_id=OWNER_ID, chat_id=OWNER_ID, text="أرسل ايدي المستخدم:", reply_markup=ForceReply(), timeout=30)
            uid = int(ask_id.text)
            ask_days = await listener.listen(from_id=OWNER_ID, chat_id=OWNER_ID, text="عدد الأيام:", reply_markup=ForceReply(), timeout=30)
            days = int(ask_days.text)
            # حساب التواريخ
            start = datetime.now()
            end = start + timedelta(days=days)
            users[str(uid)] = {"vip": True, "limitation": {"days": days, "startDate": start.strftime("%Y-%m-%d"), "endDate": end.strftime("%Y-%m-%d"), "endTime": end.strftime("%H:%M")}}
            write(users_db, users)
            await app.send_message(uid, "🎉 تم تفعيل اشتراك VIP لك.")
            await callback.message.reply("✅ تم التفعيل.", reply_markup=Markup([[Button("🏠 admin", callback_data="admin_back")]]))
        except:
            await callback.message.reply("❌ خطأ في الإدخال.", reply_markup=Markup([[Button("🔙 رجوع", callback_data="admin_back")]]))
    elif data == "admin_remove_vip":
        # مشابه
        await callback.message.edit_text("ميزة قيد التطوير", reply_markup=Markup([[Button("🔙 رجوع", callback_data="admin_back")]]))
    elif data == "admin_channels":
        markup = []
        for ch in channels:
            markup.append([Button(ch, url=f"https://t.me/{ch}"), Button("🗑", callback_data=f"admin_delch_{ch}")])
        markup.append([Button("➕ إضافة قناة", callback_data="admin_addch"), Button("🔙 رجوع", callback_data="admin_back")])
        await callback.message.edit_text("قنوات الاشتراك الإجباري:", reply_markup=Markup(markup))
    elif data.startswith("admin_delch_"):
        ch = data.split("_",2)[2]
        if ch in channels:
            channels.remove(ch)
            write(channels_db, channels)
        await callback.answer("تم الحذف.")
        await admin_callbacks(client, callback)  # إعادة تحميل القائمة
    elif data == "admin_addch":
        try:
            ask = await listener.listen(from_id=OWNER_ID, chat_id=OWNER_ID, text="أرسل معرف القناة (بدون @):", reply_markup=ForceReply(), timeout=30)
            ch = ask.text.strip()
            # التحقق من وجودها
            await app.get_chat(ch)
            if ch not in channels:
                channels.append(ch)
                write(channels_db, channels)
            await callback.message.reply("✅ تمت الإضافة.", reply_markup=Markup([[Button("🔙 رجوع", callback_data="admin_back")]]))
        except:
            await callback.message.reply("❌ فشل.", reply_markup=Markup([[Button("🔙 رجوع", callback_data="admin_back")]]))
    elif data == "admin_back":
        await callback.message.edit_text("👑 لوحة تحكم المالك:", reply_markup=admin_markup)
    elif data == "admin_stop":
        await callback.message.reply("🛑 إيقاف البوت...")
        await app.stop()
        exit(0)
    # باقي الأزرار يمكن تنفيذها بطريقة مماثلة

# ------------------- بدء التشغيل -------------------
async def restart_tasks():
    await sleep(30)
    for uid, data in users.items():
        if data.get("posting") and uid not in active_tasks:
            task = create_task(posting_worker(int(uid)))
            active_tasks[uid] = task

async def main():
    # تنظيف البيانات من أي تكرارات قديمة
    for uid, data in users.items():
        if "groups" in data and isinstance(data["groups"], list):
            unique = []
            seen = set()
            for g in data["groups"]:
                if g["id"] not in seen:
                    seen.add(g["id"])
                    unique.append(g)
            if len(unique) != len(data["groups"]):
                data["groups"] = unique
                write(users_db, users)
    # بدء المهام
    create_task(restart_tasks())
    await app.start()
    print("البوت يعمل...")
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(main())
