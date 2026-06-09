from pyrogram import Client, filters, idle
from pyrogram.types import (
    Message,
    CallbackQuery,
    ForceReply,
    InlineKeyboardMarkup as Markup,
    InlineKeyboardButton as Button
)
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    UserNotParticipant,
    ChatWriteForbidden,
    PeerIdInvalid,
    FloodWait
)
import os
os.system("pip install pyro-listener")
from pyrolistener import Listener, exceptions
from asyncio import create_task, sleep, get_event_loop, gather
from datetime import datetime, timedelta
from pytz import timezone
from typing import Union
import json, os, random, re

app = Client(
    "autoPost",
    api_id="34923196",
    api_hash="b3f6e47ecd3231186f8f7e01ab41938e",
    bot_token='8860124031:AAE2LpN2aoz9wTDtKEx_B9KtBgrSHWtfTrY'
)
loop = get_event_loop()
listener = Listener(client=app)
owner = 8310839908
_timezone = timezone("Asia/Baghdad")

# =================== دوال مساعدة ===================
def get_home_markup(user_id):
    user_data = users.get(str(user_id), {})
    delay_mode_text = "✅ تأخير ذكي مفعل" if user_data.get("smart_delay", True) else "❌ تأخير ذكي معطل"
    high_security_text = "🛡 وضع أمان عالي مفعل" if user_data.get("high_security", False) else "⚠ وضع أمان عادي"
    delete_after = user_data.get("delete_after", 0)
    delete_text = f"🗑 حذف بعد {delete_after} ثانية" if delete_after > 0 else "🗑 حذف تلقائي معطل"
    return Markup([
        [Button("- حسابك -", callback_data="account")],
        [Button("- السوبرات الحاليه -", callback_data="currentSupers"), Button("- إضافة سوبر -", callback_data="newSuper")],
        [Button("- تعيين المدة بين كل نشر -", callback_data="waitTime"), Button("- إدارة الكليشات -", callback_data="manageCaptions")],
        [Button(delete_text, callback_data="setDeleteAfter")],
        [Button(delay_mode_text, callback_data="toggleSmartDelay"), Button(high_security_text, callback_data="toggleHighSecurity")],
        [Button("- ايقاف النشر -", callback_data="stopPosting"), Button("- بدء النشر -", callback_data="startPosting")]
    ])

def randomize_caption(caption: str, user_mention: str = None) -> str:
    """إضافة متغيرات ديناميكية إلى الكليشة لتجنب التكرار"""
    now = datetime.now(_timezone)
    caption = caption.replace("{time}", now.strftime("%H:%M:%S"))
    caption = caption.replace("{date}", now.strftime("%Y-%m-%d"))
    caption = caption.replace("{random}", str(random.randint(100, 999)))
    caption = caption.replace("{random2}", str(random.randint(1000, 9999)))
    if user_mention:
        caption = caption.replace("{mention}", user_mention)
    return caption

def is_allowed_time(high_security: bool = False) -> bool:
    """التحقق من أن الوقت مناسب للنشر (8 صباحاً - 11 مساءً)"""
    if not high_security:
        return True
    now = datetime.now(_timezone)
    if now.hour < 8 or now.hour > 23:
        return False
    return True

async def simulate_typing(client, chat_id, high_security: bool = False):
    """محاكاة الكتابة البشرية"""
    if high_security:
        await sleep(random.uniform(1.5, 4.0))
    else:
        await sleep(random.uniform(0.5, 2.0))
    async with client.action(chat_id, "typing"):
        await sleep(random.uniform(0.5, 1.5))

def can_send_to_group(user_id_str: str, group_id: int) -> bool:
    """التحقق من عدم تجاوز الحد اليومي للرسائل للمجموعة"""
    today = datetime.now(_timezone).strftime("%Y-%m-%d")
    stats = users[user_id_str].get("group_stats", {}).get(str(group_id), {})
    last_reset = stats.get("last_reset")
    
    if last_reset != today:
        stats = {"count": 0, "last_reset": today}
    
    if stats["count"] >= 6:  # حد أقصى 6 رسائل يومياً لكل مجموعة
        return False
    
    stats["count"] += 1
    if "group_stats" not in users[user_id_str]:
        users[user_id_str]["group_stats"] = {}
    users[user_id_str]["group_stats"][str(group_id)] = stats
    write(users_db, users)
    return True

async def delete_message_after_delay(client, chat_id, message_id, delay_seconds):
    """حذف رسالة بعد فترة زمنية معينة"""
    await sleep(delay_seconds)
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception:
        pass

async def check_account_status(user_id: int, client) -> tuple:
    """التحقق من أن الحساب غير محظور من SpamBot"""
    try:
        await client.send_message(user_id, "🔍")
        return True, None
    except FloodWait as e:
        return False, f"FloodWait: انتظر {e.value} ثانية"
    except Exception as e:
        error_msg = str(e)
        if "USER_BANNED" in error_msg or "restricted" in error_msg or "BANNED" in error_msg:
            return False, f"الحساب محظور: {error_msg[:100]}"
        return True, None

# =================== أوامر المستخدم ===================
@app.on_message(filters.command("start") & filters.private)
async def start(_: Client, message: Message):
    user_id = message.from_user.id
    subscribed = await subscription(message)
    if user_id == owner and users.get(str(user_id)) is None:
        users[str(user_id)] = {"vip": True, "smart_delay": True, "high_security": False, "captions": [], "delete_after": 0}
        write(users_db, users)
    elif isinstance(subscribed, str):
        return await message.reply(f"- عذرا عزيزي عليك الإشتراك بقناة البوت أولا لتتمكن استخدامه\n- القناه: @{subscribed}\n- اشترك ثم ارسل /start")
    elif (str(user_id) not in users):
        users[str(user_id)] = {"vip": False, "smart_delay": True, "high_security": False, "captions": [], "delete_after": 0}
        write(users_db, users)
        return await message.reply(f"لا يمكنك استخدام هذا البوت تواصل مع [المطور](tg://openmessage?user_id={owner}) لتفعيل الاشتراك")
    elif not users[str(user_id)]["vip"]:
        return await message.reply(f"لا يمكنك استخدام هذا البوت تواصل مع [المطور](tg://openmessage?user_id={owner}) لتفعيل الاشتراك")
    fname = message.from_user.first_name
    caption = f"- مرحبا بك عزيزي [{fname}](tg://settings) في بوت النشر التلقائي\n\n- يمكنك استخدام البوت في ارسال الرسائل بشكل متكرر في السوبرات\n- تحكم في البوت من الازرار التاليه:"
    await message.reply(caption, reply_markup=get_home_markup(user_id), reply_to_message_id=message.id)

@app.on_callback_query(filters.regex(r"^(toHome)$"))
async def toHome(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    fname = callback.from_user.first_name
    caption = f"- مرحبا بك عزيزي [{fname}](tg://settings) في بوت النشر التلقائي\n\n- يمكنك استخدام البوت في ارسال الرسائل بشكل متكرر في السوبرات\n- تحكم في البوت من الازرار التاليه:"
    await callback.message.edit_text(caption, reply_markup=get_home_markup(user_id))

@app.on_callback_query(filters.regex(r"^(toggleSmartDelay)$"))
async def toggle_smart_delay(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    current = users[str(user_id)].get("smart_delay", True)
    users[str(user_id)]["smart_delay"] = not current
    write(users_db, users)
    await callback.answer(f"تم {'تفعيل' if not current else 'تعطيل'} التأخير الذكي", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=get_home_markup(user_id))

@app.on_callback_query(filters.regex(r"^(toggleHighSecurity)$"))
async def toggle_high_security(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    current = users[str(user_id)].get("high_security", False)
    users[str(user_id)]["high_security"] = not current
    write(users_db, users)
    await callback.answer(f"تم {'تفعيل' if not current else 'تعطيل'} وضع الأمان العالي", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=get_home_markup(user_id))

@app.on_callback_query(filters.regex(r"^(setDeleteAfter)$"))
async def setDeleteAfter(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    await callback.message.delete()
    reMarkup = Markup([[Button("- العوده -", callback_data="toHome")]])
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- أرسل المدة الزمنية (بالثواني) لحذف الرسائل.\n- مثال: 1800 لنصف ساعة.\n- أرسل 0 لتعطيل الميزة.",
            reply_markup=ForceReply(selective=True, placeholder="المدة بالثواني"),
            timeout=120
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى وقت الاستلام.", reply_markup=reMarkup)
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء.", reply_markup=reMarkup)
    try:
        seconds = int(ask.text)
        if seconds < 0:
            raise ValueError
    except ValueError:
        return await ask.reply("- المدة يجب أن تكون رقماً صحيحاً غير سالب.", reply_markup=reMarkup)
    users[str(user_id)]["delete_after"] = seconds
    write(users_db, users)
    await ask.reply(f"- تم تعيين مدة الحذف إلى {seconds} ثانية.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(account)$"))
async def account(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    fname = callback.from_user.first_name
    caption = f"- مرحبا عزيزي [{fname}](tg://settings) في قسم الحساب\n\n- استخدم الازرار التاليه للتحكم بحسابك:"
    markup = Markup([
        [Button("- تسجيل حسابك -", callback_data="login"), Button("- تغيير الحساب -", callback_data="changeAccount")],
        [Button("- العوده -", callback_data="toHome")]
    ])
    await callback.message.edit_text(caption, reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(login|changeAccount)$"))
async def login(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    elif callback.data == "changeAccount" and users[str(user_id)].get("session") is None:
        return await callback.answer("- لم تقم بالتسجيل بعد.", show_alert=True)
    await callback.message.delete()
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- أرسل رقم الهاتف الخاص بك:\n\n- يمكنك ارسال /cancel للإلغاء.",
            reply_markup=ForceReply(selective=True, placeholder="+9647700000"), timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- نفد وقت الاستلام", reply_markup=Markup([[Button("- العوده -", callback_data="account")]]))
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء.")
    create_task(registration(ask))

async def registration(message: Message):
    user_id = message.from_user.id
    _number = message.text
    lmsg = await message.reply("- جارٍ تسجيل الدخول...")
    reMarkup = Markup([[Button("- إعادة المحاوله -", callback_data="login"), Button("- العوده -", callback_data="account")]])
    client = Client("registration", in_memory=True, api_id=app.api_id, api_hash=app.api_hash)
    await client.connect()
    try:
        p_code_hash = await client.send_code(_number)
    except PhoneNumberInvalid:
        return await lmsg.edit_text("- رقم الهاتف خاطئ", reply_markup=reMarkup)
    try:
        code = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- تم ارسال الكود. قم بإرساله.",
            timeout=120,
            reply_markup=ForceReply(selective=True, placeholder="1 2 3 4 5 6"))
    except exceptions.TimeOut:
        return await lmsg.edit_text("- نفذ وقت استلام الكود.", reply_markup=reMarkup)
    try:
        await client.sign_in(_number, p_code_hash.phone_code_hash, code.text.replace(" ", ""))
    except PhoneCodeInvalid:
        return await code.reply("- كود خاطئ.", reply_markup=reMarkup)
    except PhoneCodeExpired:
        return await code.reply("- الكود منتهي.", reply_markup=reMarkup)
    except SessionPasswordNeeded:
        try:
            password = await listener.listen(
                from_id=user_id, chat_id=user_id,
                text="- ادخل كلمة مرور التحقق بخطوتين.",
                reply_markup=ForceReply(selective=True, placeholder="PASSWORD"),
                timeout=180)
        except exceptions.TimeOut:
            return await lmsg.edit_text("- نفذ وقت استلام كلمة المرور.", reply_markup=reMarkup)
        try:
            await client.check_password(password.text)
        except PasswordHashInvalid:
            return await password.reply("- كلمة مرور خاطئه.", reply_markup=reMarkup)
    session = await client.export_session_string()
    await client.disconnect()
    if user_id == owner and users.get(str(user_id)) is None:
        users[str(user_id)] = {"vip": True, "session": session, "smart_delay": True, "high_security": False, "captions": [], "delete_after": 0}
    else:
        users[str(user_id)]["session"] = session
    write(users_db, users)
    await app.send_message(user_id, "- تم تسجيل الدخول بنجاح.", reply_markup=Markup([[Button("الصفحه الرئيسيه", callback_data="toHome")]]))

# =================== إدارة السوبرات ===================
@app.on_callback_query(filters.regex(r"^(newSuper)$"))
async def newSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك.", show_alert=True)
    await callback.message.delete()
    reMarkup = Markup([[Button("- حاول مره أخرى -", callback_data="newSuper"), Button("- العوده -", callback_data="toHome")]])
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- ارسل رابط السوبر أو ايديه.\n- ارسل /cancel للإلغاء.",
            reply_markup=ForceReply(selective=True, placeholder="رابط المجموعة أو معرفها"),
            timeout=60)
    except exceptions.TimeOut:
        return await callback.message.reply("نفذ وقت الاستلام", reply_markup=reMarkup)
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء.")
    
    input_text = ask.text.strip()
    group_id = None
    invite_link = None
    
    if input_text.startswith("-") and input_text.lstrip("-").isdigit():
        group_id = int(input_text)
    elif "t.me/" in input_text:
        invite_link = input_text
        try:
            chat = await app.get_chat(invite_link.split("/")[-1])
            group_id = chat.id
        except Exception:
            return await ask.reply("- لم يتم ايجاد السوبر.", reply_markup=reMarkup)
    else:
        try:
            group_id = int(input_text)
        except:
            return await ask.reply("- الرابط أو المعرف غير صالح.", reply_markup=reMarkup)
    
    if users[str(user_id)].get("groups") is None:
        users[str(user_id)]["groups"] = []
    users[str(user_id)]["groups"].append({"id": group_id, "link": invite_link})
    write(users_db, users)
    await ask.reply("- تمت اضافة السوبر.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(currentSupers)$"))
async def currentSupers(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك.", show_alert=True)
    groups_data = users[str(user_id)].get("groups", [])
    if not groups_data:
        return await callback.answer("- لم يتم إضافة اي سوبر", show_alert=True)
    markup = []
    for g in groups_data:
        gid = g["id"]
        try:
            title = (await app.get_chat(gid)).title
        except:
            title = str(gid)
        markup.append([Button(title, callback_data=f"super_{gid}"), Button("🗑", callback_data=f"delSuper_{gid}")])
    markup.append([Button("- الصفحه الرئيسيه -", callback_data="toHome")])
    await callback.message.edit_text("- السوبرات المضافه:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^delSuper_"))
async def delSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك.", show_alert=True)
    gid = int(callback.data.split("_")[1])
    users[str(user_id)]["groups"] = [g for g in users[str(user_id)].get("groups", []) if g["id"] != gid]
    write(users_db, users)
    await callback.answer("- تم الحذف", show_alert=True)
    await currentSupers(_, callback)

# =================== إدارة الكليشات ===================
@app.on_callback_query(filters.regex(r"^(manageCaptions)$"))
async def manageCaptions(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك.", show_alert=True)
    captions = users[str(user_id)].get("captions", [])
    markup = []
    for idx, cap in enumerate(captions):
        short = cap[:30] + "..." if len(cap) > 30 else cap
        markup.append([Button(short, callback_data=f"viewCaption_{idx}"), Button("🗑", callback_data=f"delCaption_{idx}")])
    markup.append([Button("- إضافة كليشه -", callback_data="addCaption")])
    markup.append([Button("- الصفحه الرئيسيه -", callback_data="toHome")])
    await callback.message.edit_text("📝 الكليشات:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addCaption)$"))
async def addCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك.", show_alert=True)
    await callback.message.delete()
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- أرسل النص الجديد.\n- استخدم /cancel للإلغاء.\n\n- المتغيرات المتاحة:\n{time} {date} {random} {mention}",
            reply_markup=ForceReply(selective=True, placeholder="نص الكليشة"),
            timeout=120)
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت.", reply_markup=Markup([[Button("- العوده -", callback_data="manageCaptions")]]))
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء.", reply_markup=Markup([[Button("- العوده -", callback_data="manageCaptions")]]))
    captions = users[str(user_id)].get("captions", [])
    captions.append(ask.text)
    users[str(user_id)]["captions"] = captions
    write(users_db, users)
    await ask.reply("- ✅ تم الإضافة.", reply_markup=Markup([[Button("- العوده -", callback_data="manageCaptions")]]))

@app.on_callback_query(filters.regex(r"^delCaption_"))
async def delCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    captions = users[str(user_id)].get("captions", [])
    if 0 <= idx < len(captions):
        captions.pop(idx)
        users[str(user_id)]["captions"] = captions
        write(users_db, users)
    await manageCaptions(_, callback)

@app.on_callback_query(filters.regex(r"^viewCaption_"))
async def viewCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    captions = users[str(user_id)].get("captions", [])
    if 0 <= idx < len(captions):
        await callback.answer("📄 معاينة:", show_alert=True)
        await callback.message.reply(f"**الكليشة:**\n{captions[idx]}\n\n**معاينة مع المتغيرات:**\n{randomize_caption(captions[idx])}")

# =================== تعيين المدة ===================
@app.on_callback_query(filters.regex(r"^(waitTime)$"))
async def waitTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك.", show_alert=True)
    await callback.message.delete()
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- أرسل مدة الانتظار (بالثواني).\n- استخدم /cancel للإلغاء.",
            reply_markup=ForceReply(selective=True, placeholder="المدة بالثواني"),
            timeout=120)
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت.", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء.")
    try:
        users[str(user_id)]["waitTime"] = int(ask.text)
        write(users_db, users)
        await ask.reply("- تم تعيين المدة.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))
    except ValueError:
        await ask.reply("- قيمة غير صالحة.")

# =================== بدء وإيقاف النشر ===================
active_tasks = set()
failed_groups = set()

@app.on_callback_query(filters.regex(r"^(startPosting)$"))
async def startPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = users.get(str(user_id), {})
    if user_id != owner and not user_data.get("vip"):
        return await callback.answer("- انتهت مدة الإشتراك.", show_alert=True)
    if not user_data.get("session"):
        return await callback.answer("- أضف حساباً أولاً.", show_alert=True)
    if not user_data.get("groups"):
        return await callback.answer("- أضف سوبرات أولاً.", show_alert=True)
    if not user_data.get("captions"):
        return await callback.answer("- أضف كليشة أولاً.", show_alert=True)
    if user_data.get("posting"):
        return await callback.answer("- النشر مفعل بالفعل.", show_alert=True)
    if str(user_id) in active_tasks:
        return await callback.answer("- يتم التشغيل بالفعل.", show_alert=True)
    
    users[str(user_id)]["posting"] = True
    write(users_db, users)
    task = create_task(posting(user_id))
    active_tasks.add(str(user_id))
    task.add_done_callback(lambda t: active_tasks.discard(str(user_id)))
    
    await callback.message.edit_text("- بدأ النشر التلقائي", reply_markup=Markup([[Button("- إيقاف النشر -", callback_data="stopPosting"), Button("- عوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(stopPosting)$"))
async def stopPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not users.get(str(user_id), {}).get("posting"):
        return await callback.answer("- النشر معطل بالفعل.", show_alert=True)
    users[str(user_id)]["posting"] = False
    write(users_db, users)
    await callback.message.edit_text("- تم إيقاف النشر", reply_markup=Markup([[Button("- بدء النشر -", callback_data="startPosting"), Button("- عوده -", callback_data="toHome")]]))

# =================== دوال النشر الرئيسية ===================
def get_delays_between_groups(num_groups: int, base_wait_time: int, high_security: bool = False) -> list:
    if num_groups <= 1:
        return []
    avg_interval = base_wait_time / num_groups
    variation = 0.4 if high_security else 0.3
    delays = []
    remaining = base_wait_time
    for i in range(num_groups - 1):
        var = random.uniform(-variation, variation) * avg_interval
        delay = max(3 if high_security else 1, avg_interval + var)
        if i == num_groups - 2:
            delay = max(3 if high_security else 1, remaining)
        else:
            remaining -= delay
        delays.append(delay)
    return delays

async def send_to_group(client, user_id, group_id, caption, invite_link, delete_after=0, high_security=False):
    user_id_str = str(user_id)
    global failed_groups
    
    if (user_id_str, group_id) in failed_groups:
        return None
    
    # محاكاة الكتابة
    await simulate_typing(client, group_id, high_security)
    
    # تأخير عشوائي إضافي
    jitter = random.uniform(2, 5) if high_security else random.uniform(1, 3)
    await sleep(jitter)
    
    try:
        msg = await client.send_message(group_id, caption)
        if delete_after > 0:
            create_task(delete_message_after_delay(client, group_id, msg.id, delete_after))
        return msg.id
        
    except PeerIdInvalid:
        joined = False
        if invite_link:
            try:
                await client.join_chat(invite_link)
                joined = True
            except:
                pass
        if not joined:
            try:
                await client.join_chat(group_id)
                joined = True
            except:
                pass
        if joined:
            try:
                msg = await client.send_message(group_id, caption)
                if delete_after > 0:
                    create_task(delete_message_after_delay(client, group_id, msg.id, delete_after))
                return msg.id
            except:
                pass
        users[user_id_str]["groups"] = [g for g in users[user_id_str].get("groups", []) if g["id"] != group_id]
        write(users_db, users)
        failed_groups.add((user_id_str, group_id))
        return None
        
    except FloodWait as e:
        wait_time = e.value + random.randint(5, 15)
        await app.send_message(int(user_id), f"⏳ تم حظر الإرسال لمدة {wait_time} ثانية.")
        await sleep(wait_time)
        return None
        
    except Exception as e:
        error_msg = str(e)
        if "USER_BANNED" in error_msg or "restricted" in error_msg:
            await app.send_message(int(user_id), f"🚨 **تم حظر حسابك!** راجع @SpamBot\nتم إيقاف النشر.")
            users[user_id_str]["posting"] = False
            write(users_db, users)
            return None
        elif "ChatWriteForbidden" in error_msg or "UserNotParticipant" in error_msg:
            users[user_id_str]["groups"] = [g for g in users[user_id_str].get("groups", []) if g["id"] != group_id]
            write(users_db, users)
            return None
        else:
            await app.send_message(int(user_id), f"⚠️ خطأ: {error_msg[:100]}")
            return None

async def posting(user_id):
    user_id_str = str(user_id)
    if not users.get(user_id_str, {}).get("posting"):
        return
    
    client = Client(user_id_str, api_id=app.api_id, api_hash=app.api_hash, session_string=users[user_id_str]["session"])
    await client.start()
    
    # التحقق من حالة الحساب
    is_ok, error = await check_account_status(user_id, client)
    if not is_ok:
        await app.send_message(user_id, f"🚨 {error}\nتم إيقاف النشر.")
        users[user_id_str]["posting"] = False
        write(users_db, users)
        await client.stop()
        return
    
    try:
        while users[user_id_str].get("posting"):
            wait_time = users[user_id_str].get("waitTime", 60)
            groups_data = users[user_id_str].get("groups", [])
            captions_list = users[user_id_str].get("captions", [])
            delete_after = users[user_id_str].get("delete_after", 0)
            high_security = users[user_id_str].get("high_security", False)
            
            if not captions_list:
                users[user_id_str]["posting"] = False
                write(users_db, users)
                await app.send_message(user_id, "- تم إيقاف النشر لعدم وجود كليشات.")
                break
            
            # التحقق من الوقت المناسب
            if not is_allowed_time(high_security):
                await sleep(600)
                continue
            
            smart_delay = users[user_id_str].get("smart_delay", True)
            num_groups = len(groups_data)
            
            # التحقق من الحد اليومي لكل مجموعة
            valid_groups = []
            for g in groups_data:
                if can_send_to_group(user_id_str, g["id"]):
                    valid_groups.append(g)
            
            if not valid_groups:
                await app.send_message(user_id, "⚠️ جميع المجموعات وصلت للحد اليومي (6 رسائل). انتظر 24 ساعة.")
                await sleep(3600)
                continue
            
            if smart_delay and num_groups > 1:
                delays = get_delays_between_groups(len(valid_groups), wait_time, high_security)
            else:
                delays = [0] * (len(valid_groups) - 1) if len(valid_groups) > 1 else []
            
            for idx, group_obj in enumerate(valid_groups):
                group_id = group_obj["id"]
                invite_link = group_obj.get("link")
                chosen_caption = random.choice(captions_list)
                # إضافة المتغيرات الديناميكية
                final_caption = randomize_caption(chosen_caption, f"@{users[user_id_str].get('username', 'user')}")
                
                await send_to_group(client, user_id, group_id, final_caption, invite_link, delete_after, high_security)
                
                if idx < len(delays):
                    await sleep(delays[idx])
            
            # انتظار إضافي بعد انتهاء الدورة
            extra_wait = random.uniform(5, 15) if high_security else random.uniform(2, 8)
            await sleep(wait_time + extra_wait)
            
    finally:
        await client.stop()

# =================== كشف رسائل SpamBot ===================
@app.on_message(filters.user("SpamBot") & filters.private)
async def spam_bot_warning(_, message: Message):
    user_id = message.chat.id
    text = message.text.lower()
    if any(word in text for word in ["ограничение", "restricted", "limited", "banned", "spam"]):
        if users.get(str(user_id), {}).get("posting"):
            users[str(user_id)]["posting"] = False
            write(users_db, users)
            await app.send_message(user_id, "🚨 **تم اكتشاف تحذير من SpamBot!**\nتم إيقاف النشر التلقائي لحماية حسابك.\nراجع @SpamBot للحصول على التفاصيل.")

# =================== قسم المالك ===================
async def Owner(_, __: Client, message: Message):
    return (message.from_user.id == owner)

isOwner = filters.create(Owner)

adminMarkup = Markup([
    [Button("- الغاء VIP -", callback_data="cancelVIP"), Button("- تفعيل VIP -", callback_data="addVIP")],
    [Button("- الاحصائيات -", callback_data="statics"), Button("- قنوات الإشتراك -", callback_data="channels")]
])

@app.on_message(filters.command("admin") & filters.private & isOwner)
@app.on_callback_query(filters.regex("toAdmin") & isOwner)
async def admin(_: Client, message: Union[Message, CallbackQuery]):
    fname = message.from_user.first_name
    caption = f"مرحبا عزيزي [{fname}](tg://settings) في لوحة المالك"
    func = message.reply if isinstance(message, Message) else message.message.edit_text
    await func(caption, reply_markup=adminMarkup)

@app.on_callback_query(filters.regex("addVIP") & isOwner)
async def addVIP(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    try:
        ask = await listener.listen(from_id=user_id, chat_id=user_id, text="- ارسل ايدي المستخدم",
                                    reply_markup=ForceReply(selective=True, placeholder="user id"), timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- نفذ الوقت.")
    try:
        _id = int(ask.text)
        await app.get_chat(_id)
    except:
        return await ask.reply("- مستخدم غير موجود.")
    try:
        limit = await listener.listen(from_id=user_id, chat_id=user_id, text="- أرسل عدد الأيام",
                                      reply_markup=ForceReply(selective=True, placeholder="عدد الأيام"), timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت.")
    try:
        _limit = int(limit.text)
    except ValueError:
        return await limit.reply("- رقم غير صالح.")
    vipDate = timeCalc(_limit)
    users[str(_id)] = {"vip": True, "smart_delay": True, "high_security": False, "captions": [], "delete_after": 0}
    users[str(_id)]["limitation"] = {"days": _limit, "startDate": vipDate["current_date"], "endDate": vipDate["end_date"], "endTime": vipDate["endTime"]}
    write(users_db, users)
    create_task(vipCanceler(_id))
    caption = f"- تم تفعيل VIP لمدة {_limit} يوم"
    await limit.reply(caption)
    try:
        await app.send_message(_id, f"- تم تفعيل VIP لك لمدة {_limit} يوم")
    except:
        pass

@app.on_callback_query(filters.regex(r"^(cancelVIP)$") & isOwner)
async def cancelVIP(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    try:
        ask = await listener.listen(from_id=user_id, chat_id=user_id, text="- ارسل ايدي المستخدم",
                                    reply_markup=ForceReply(selective=True, placeholder="user id"), timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- نفذ الوقت.")
    if users.get(ask.text) is None or not users[ask.text].get("vip"):
        return await ask.reply("- المستخدم ليس VIP.")
    users[ask.text]["vip"] = False
    write(users_db, users)
    await ask.reply("- تم إلغاء VIP.")

@app.on_callback_query(filters.regex(r"^(channels)$") & isOwner)
async def channelsControl(_: Client, callback: CallbackQuery):
    markup = [[Button(ch, url=f"https://t.me/{ch}"), Button("🗑", callback_data=f"removeChannel {ch}")] for ch in channels]
    markup.extend([[Button("- إضافة قناه -", callback_data="addChannel")], [Button("- الصفحه الرئيسيه -", callback_data="toAdmin")]])
    await callback.message.edit_text("قنوات الإشتراك:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addChannel)") & isOwner)
async def addChannel(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    try:
        ask = await listener.listen(from_id=user_id, chat_id=user_id, text="- ارسل معرف القناه بدون @",
                                    reply_markup=ForceReply(selective=True, placeholder="username"), timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- نفذ الوقت.")
    try:
        await app.get_chat(ask.text)
    except:
        return await callback.message.reply("- لم يتم ايجاد القناه.")
    channels.append(ask.text)
    write(channels_db, channels)
    await ask.reply("- تم الإضافة.", reply_markup=Markup([[Button("- العوده -", callback_data="channels")]]))

@app.on_callback_query(filters.regex(r"^(removeChannel)") & isOwner)
async def removeChannel(_: Client, callback: CallbackQuery):
    channel = callback.data.split()[1]
    if channel in channels:
        channels.remove(channel)
        write(channels_db, channels)
    await channelsControl(_, callback)

@app.on_callback_query(filters.regex(r"^(statics)$") & isOwner)
async def statics(_: Client, callback: CallbackQuery):
    total = len(users)
    vip = sum(1 for u in users.values() if u.get("vip"))
    await callback.message.edit_text(f"- المستخدمين: {total}\n- VIP: {vip}", reply_markup=Markup([[Button("- العوده -", callback_data="toAdmin")]]))

def timeCalc(limit):
    start_date = datetime.now(_timezone)
    end_date = start_date + timedelta(days=limit)
    return {"current_date": start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d"), "endTime": end_date.strftime("%H:%M"), "hours": limit * 24, "minutes": limit * 24 * 60}

async def vipCanceler(user_id):
    await sleep(60)
    while True:
        if str(user_id) not in users or not users[str(user_id)].get("vip"):
            break
        limitation = users[str(user_id)].get("limitation")
        if not limitation:
            break
        if datetime.now(_timezone).strftime("%Y-%m-%d %H:%M") >= f"{limitation['endDate']} {limitation['endTime']}":
            users[str(user_id)]["vip"] = False
            write(users_db, users)
            await app.send_message(user_id, "- انتهى اشتراك VIP.")
            break
        await sleep(60)

# =================== الإشتراك الإجباري ===================
async def subscription(message: Message):
    user_id = message.from_user.id
    for channel in channels:
        try:
            await app.get_chat_member(channel, user_id)
        except UserNotParticipant:
            return channel
    return True

# =================== إدارة التخزين ===================
def write(fp, data):
    with open(fp, "w") as file:
        json.dump(data, file, indent=2)

def read(fp):
    if not os.path.exists(fp):
        write(fp, {} if fp != channels_db else [])
    with open(fp) as file:
        return json.load(file)

users_db = "users.json"
channels_db = "channels.json"
users = read(users_db)
channels = read(channels_db)

async def reStartPosting():
    await sleep(30)
    for user in users:
        if users[user].get("posting") and str(user) not in active_tasks:
            task = create_task(posting(int(user)))
            active_tasks.add(str(user))
            task.add_done_callback(lambda t, uid=str(user): active_tasks.discard(uid))

async def reVipTime():
    for user in users:
        if int(user) != owner and users[user].get("vip"):
            create_task(vipCanceler(int(user)))

async def main():
    create_task(reStartPosting())
    create_task(reVipTime())
    await app.start()
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(main())
