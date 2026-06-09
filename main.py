from pyrogram import Client, filters, idle
from pyrogram.types import (
    Message,
    CallbackQuery,
    ForceReply,
    InlineKeyboardMarkup as Markup,
    InlineKeyboardButton as Button
)
from pyrogram.errors import (
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
from asyncio import create_task, sleep, get_event_loop
from datetime import datetime, timedelta
from pytz import timezone
from typing import Union
import json, random

# =================== إعدادات البوت ===================
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
    delete_after = user_data.get("delete_after", 0)
    delete_text = f"🗑 حذف بعد {delete_after} ثانية" if delete_after > 0 else "🗑 حذف معطل"
    return Markup([
        [Button("- حسابي -", callback_data="account")],
        [Button("- المجموعات -", callback_data="currentSupers"), Button("- إضافة مجموعة -", callback_data="newSuper")],
        [Button("- تعيين المدة -", callback_data="waitTime"), Button("- الكليشات -", callback_data="manageCaptions")],
        [Button(delete_text, callback_data="setDeleteAfter")],
        [Button("- إيقاف النشر -", callback_data="stopPosting"), Button("- بدء النشر -", callback_data="startPosting")]
    ])

async def delete_message_after_delay(client, chat_id, message_id, delay_seconds):
    await sleep(delay_seconds)
    try:
        await client.delete_messages(chat_id, message_id)
    except:
        pass

# =================== أوامر المستخدم ===================
@app.on_message(filters.command("start") & filters.private)
async def start(_: Client, message: Message):
    user_id = message.from_user.id
    
    # التحقق من الاشتراك
    if channels:
        for channel in channels:
            try:
                await app.get_chat_member(channel, user_id)
            except UserNotParticipant:
                return await message.reply(f"اشترك أولاً في قناة @{channel}")
    
    # إنشاء حساب جديد للمستخدم
    if str(user_id) not in users:
        users[str(user_id)] = {
            "vip": (user_id == owner),
            "captions": [],
            "groups": [],
            "waitTime": 60,
            "delete_after": 0,
            "posting": False
        }
        write(users_db, users)
    
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await message.reply("تواصل مع المطور لتفعيل الاشتراك")
    
    await message.reply(
        f"مرحباً {message.from_user.first_name}!\n\n"
        "أرسل /help للمساعدة",
        reply_markup=get_home_markup(user_id)
    )

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(_, message: Message):
    await message.reply(
        "📖 **دليل الاستخدام**\n\n"
        "1️⃣ أضف حسابك عبر زر 'حسابي'\n"
        "2️⃣ أضف المجموعات عبر 'إضافة مجموعة'\n"
        "3️⃣ أضف كليشات عبر 'الكليشات'\n"
        "4️⃣ اضغط 'بدء النشر'"
    )

@app.on_callback_query(filters.regex(r"^(toHome)$"))
async def toHome(_: Client, callback: CallbackQuery):
    await callback.message.edit_text("القائمة الرئيسية", reply_markup=get_home_markup(callback.from_user.id))

# =================== إدارة الحساب ===================
@app.on_callback_query(filters.regex(r"^(account)$"))
async def account(_: Client, callback: CallbackQuery):
    markup = Markup([
        [Button("- تسجيل الدخول -", callback_data="login")],
        [Button("- العودة -", callback_data="toHome")]
    ])
    if users[str(callback.from_user.id)].get("session"):
        markup = Markup([
            [Button("- تغيير الحساب -", callback_data="changeAccount")],
            [Button("- العودة -", callback_data="toHome")]
        ])
    await callback.message.edit_text("إدارة الحساب", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(login|changeAccount)$"))
async def login(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="أرسل رقم هاتفك مع رمز الدولة\nمثال: +9647700000000",
            reply_markup=ForceReply(),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("انتهى الوقت", reply_markup=Markup([[Button("- العودة -", callback_data="account")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("تم الإلغاء")
    
    await registration(ask)

async def registration(message: Message):
    user_id = message.from_user.id
    phone = message.text
    msg = await message.reply("جاري تسجيل الدخول...")
    
    client = Client("temp", in_memory=True, api_id=app.api_id, api_hash=app.api_hash)
    await client.connect()
    
    try:
        sent_code = await client.send_code(phone)
    except PhoneNumberInvalid:
        return await msg.edit("رقم الهاتف غير صحيح")
    
    try:
        code = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="أرسل الكود المرسل إليك",
            reply_markup=ForceReply(),
            timeout=120
        )
    except exceptions.TimeOut:
        return await msg.edit("انتهى الوقت")
    
    try:
        await client.sign_in(phone, sent_code.phone_code_hash, code.text)
    except PhoneCodeInvalid:
        return await code.reply("الكود غير صحيح")
    except PhoneCodeExpired:
        return await code.reply("الكود منتهي الصلاحية")
    except SessionPasswordNeeded:
        try:
            password = await listener.listen(
                from_id=user_id, chat_id=user_id,
                text="أدخل كلمة مرور التحقق بخطوتين",
                reply_markup=ForceReply(),
                timeout=60
            )
        except exceptions.TimeOut:
            return await msg.edit("انتهى الوقت")
        try:
            await client.check_password(password.text)
        except PasswordHashInvalid:
            return await password.reply("كلمة المرور غير صحيحة")
    
    session_string = await client.export_session_string()
    await client.disconnect()
    
    users[str(user_id)]["session"] = session_string
    write(users_db, users)
    
    await app.send_message(user_id, "✅ تم تسجيل الدخول بنجاح!", reply_markup=Markup([[Button("- الرئيسية -", callback_data="toHome")]]))

# =================== إدارة المجموعات ===================
@app.on_callback_query(filters.regex(r"^(newSuper)$"))
async def newSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="أرسل معرف المجموعة (يبدأ بـ -100) أو رابط الدعوة",
            reply_markup=ForceReply(),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("انتهى الوقت", reply_markup=Markup([[Button("- العودة -", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("تم الإلغاء")
    
    group_id = None
    link = None
    
    # محاولة استخراج المعرف
    if ask.text.startswith("-") and ask.text.lstrip("-").isdigit():
        group_id = int(ask.text)
    elif "t.me/" in ask.text:
        link = ask.text
        try:
            chat = await app.get_chat(ask.text.split("/")[-1])
            group_id = chat.id
        except:
            return await ask.reply("الرابط غير صالح")
    else:
        return await ask.reply("المعرف غير صالح")
    
    if "groups" not in users[str(user_id)]:
        users[str(user_id)]["groups"] = []
    
    users[str(user_id)]["groups"].append({"id": group_id, "link": link})
    write(users_db, users)
    
    await ask.reply("✅ تم إضافة المجموعة", reply_markup=Markup([[Button("- الرئيسية -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(currentSupers)$"))
async def currentSupers(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    groups = users[str(user_id)].get("groups", [])
    
    if not groups:
        return await callback.answer("لا توجد مجموعات", show_alert=True)
    
    markup = []
    for g in groups:
        gid = g["id"]
        try:
            chat = await app.get_chat(gid)
            name = chat.title
        except:
            name = str(gid)
        markup.append([Button(name[:30], callback_data=f"ignore"), Button("🗑", callback_data=f"delSuper_{gid}")])
    markup.append([Button("- الرئيسية -", callback_data="toHome")])
    
    await callback.message.edit_text("المجموعات المضافة:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^delSuper_"))
async def delSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    gid = int(callback.data.split("_")[1])
    users[str(user_id)]["groups"] = [g for g in users[str(user_id)].get("groups", []) if g["id"] != gid]
    write(users_db, users)
    await callback.answer("تم الحذف")
    await currentSupers(_, callback)

# =================== إدارة الكليشات ===================
@app.on_callback_query(filters.regex(r"^(manageCaptions)$"))
async def manageCaptions(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    captions = users[str(user_id)].get("captions", [])
    
    markup = []
    for idx, cap in enumerate(captions):
        short = cap[:25] + "..." if len(cap) > 25 else cap
        markup.append([Button(short, callback_data=f"ignore"), Button("🗑", callback_data=f"delCap_{idx}")])
    markup.append([Button("- إضافة جديدة -", callback_data="addCaption")])
    markup.append([Button("- الرئيسية -", callback_data="toHome")])
    
    if not captions:
        await callback.message.edit_text("لا توجد كليشات. أضف كليشة جديدة:", reply_markup=Markup([[Button("- إضافة -", callback_data="addCaption")], [Button("- الرئيسية -", callback_data="toHome")]]))
    else:
        await callback.message.edit_text("الكليشات:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addCaption)$"))
async def addCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="أرسل نص الكليشة الجديدة",
            reply_markup=ForceReply(),
            timeout=120
        )
    except exceptions.TimeOut:
        return await callback.message.reply("انتهى الوقت", reply_markup=Markup([[Button("- العودة -", callback_data="manageCaptions")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("تم الإلغاء")
    
    captions = users[str(user_id)].get("captions", [])
    captions.append(ask.text)
    users[str(user_id)]["captions"] = captions
    write(users_db, users)
    
    await ask.reply("✅ تم إضافة الكليشة", reply_markup=Markup([[Button("- العودة -", callback_data="manageCaptions")]]))

@app.on_callback_query(filters.regex(r"^delCap_"))
async def delCap(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    captions = users[str(user_id)].get("captions", [])
    if 0 <= idx < len(captions):
        captions.pop(idx)
        users[str(user_id)]["captions"] = captions
        write(users_db, users)
    await manageCaptions(_, callback)

# =================== الإعدادات ===================
@app.on_callback_query(filters.regex(r"^(waitTime)$"))
async def waitTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="أرسل المدة بين كل رسالة (بالثواني)\nمثال: 60",
            reply_markup=ForceReply(),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("انتهى الوقت", reply_markup=Markup([[Button("- العودة -", callback_data="toHome")]]))
    
    try:
        wait = int(ask.text)
        if wait < 10:
            return await ask.reply("المدة يجب أن تكون 10 ثوانٍ على الأقل")
        users[str(user_id)]["waitTime"] = wait
        write(users_db, users)
        await ask.reply(f"✅ تم تعيين المدة إلى {wait} ثانية", reply_markup=Markup([[Button("- الرئيسية -", callback_data="toHome")]]))
    except:
        await ask.reply("رقم غير صالح")

@app.on_callback_query(filters.regex(r"^(setDeleteAfter)$"))
async def setDeleteAfter(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="أرسل المدة لحذف الرسائل (بالثواني)\n0 لتعطيل الحذف\nمثال: 1800 لنصف ساعة",
            reply_markup=ForceReply(),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("انتهى الوقت", reply_markup=Markup([[Button("- العودة -", callback_data="toHome")]]))
    
    try:
        seconds = int(ask.text)
        if seconds < 0:
            raise ValueError
        users[str(user_id)]["delete_after"] = seconds
        write(users_db, users)
        await ask.reply(f"✅ تم تعيين مدة الحذف إلى {seconds} ثانية", reply_markup=Markup([[Button("- الرئيسية -", callback_data="toHome")]]))
    except:
        await ask.reply("رقم غير صالح")

# =================== بدء وإيقاف النشر ===================
active_tasks = set()

@app.on_callback_query(filters.regex(r"^(startPosting)$"))
async def startPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = users.get(str(user_id), {})
    
    # التحقق من وجود حساب
    if not user_data.get("session"):
        return await callback.answer("سجل دخولك أولاً!", show_alert=True)
    
    # التحقق من وجود مجموعات
    if not user_data.get("groups"):
        return await callback.answer("أضف مجموعة أولاً!", show_alert=True)
    
    # التحقق من وجود كليشات
    if not user_data.get("captions"):
        return await callback.answer("أضف كليشة أولاً!", show_alert=True)
    
    if user_data.get("posting"):
        return await callback.answer("النشر مفعل بالفعل", show_alert=True)
    
    if str(user_id) in active_tasks:
        return await callback.answer("يتم التشغيل", show_alert=True)
    
    users[str(user_id)]["posting"] = True
    write(users_db, users)
    
    task = create_task(posting(user_id))
    active_tasks.add(str(user_id))
    task.add_done_callback(lambda t: active_tasks.discard(str(user_id)))
    
    await callback.message.edit_text(
        "✅ **بدأ النشر التلقائي**\n\n"
        f"📊 عدد المجموعات: {len(user_data['groups'])}\n"
        f"📝 عدد الكليشات: {len(user_data['captions'])}\n"
        f"⏱ المدة بين الرسائل: {user_data['waitTime']} ثانية",
        reply_markup=Markup([[Button("- إيقاف النشر -", callback_data="stopPosting"), Button("- الرئيسية -", callback_data="toHome")]])
    )

@app.on_callback_query(filters.regex(r"^(stopPosting)$"))
async def stopPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not users.get(str(user_id), {}).get("posting"):
        return await callback.answer("النشر معطل بالفعل", show_alert=True)
    
    users[str(user_id)]["posting"] = False
    write(users_db, users)
    
    await callback.message.edit_text("⏹ **تم إيقاف النشر**", reply_markup=Markup([[Button("- الرئيسية -", callback_data="toHome")]]))

# =================== دالة النشر الرئيسية ===================
async def send_to_group(client, user_id, group_id, caption, delete_after, invite_link=None):
    """إرسال رسالة إلى مجموعة واحدة"""
    try:
        # محاولة الإرسال مباشرة
        msg = await client.send_message(group_id, caption)
        
        # جدولة الحذف إذا لزم الأمر
        if delete_after > 0:
            create_task(delete_message_after_delay(client, group_id, msg.id, delete_after))
        
        return True
        
    except (PeerIdInvalid, UserNotParticipant, ChatWriteForbidden):
        # محاولة الانضمام عبر الرابط إذا وجد
        if invite_link:
            try:
                await client.join_chat(invite_link)
                # المحاولة مرة أخرى بعد الانضمام
                msg = await client.send_message(group_id, caption)
                if delete_after > 0:
                    create_task(delete_message_after_delay(client, group_id, msg.id, delete_after))
                return True
            except:
                pass
        return False
        
    except FloodWait as e:
        # انتظار الوقت المطلوب
        await sleep(e.value + 5)
        return await send_to_group(client, user_id, group_id, caption, delete_after, invite_link)
        
    except Exception as e:
        # طباعة الخطأ للمطور فقط
        if user_id == owner:
            print(f"خطأ في المجموعة {group_id}: {e}")
        return False

async def posting(user_id):
    user_id_str = str(user_id)
    if not users.get(user_id_str, {}).get("posting"):
        return
    
    # إنشاء عميل الحساب
    client = Client(
        f"user_{user_id}",
        api_id=app.api_id,
        api_hash=app.api_hash,
        session_string=users[user_id_str]["session"]
    )
    
    try:
        await client.start()
        
        while users[user_id_str].get("posting"):
            wait_time = users[user_id_str].get("waitTime", 60)
            groups = users[user_id_str].get("groups", []).copy()
            captions = users[user_id_str].get("captions", [])
            delete_after = users[user_id_str].get("delete_after", 0)
            
            if not groups or not captions:
                users[user_id_str]["posting"] = False
                write(users_db, users)
                break
            
            # إرسال رسالة إلى كل مجموعة
            for group in groups:
                if not users[user_id_str].get("posting"):
                    break
                
                group_id = group["id"]
                invite_link = group.get("link")
                caption = random.choice(captions)  # اختيار كليشة عشوائية
                
                success = await send_to_group(client, user_id, group_id, caption, delete_after, invite_link)
                
                if success:
                    await app.send_message(user_id, f"✅ تم الإرسال إلى المجموعة {group_id}")
                else:
                    await app.send_message(user_id, f"❌ فشل الإرسال إلى {group_id}")
                
                # انتظار المدة المحددة قبل الإرسال التالي
                await sleep(wait_time)
            
            # بعد الانتهاء من جميع المجموعات، انتظر دورة كاملة
            await sleep(wait_time)
    
    except Exception as e:
        await app.send_message(user_id, f"⚠️ خطأ في البوت: {str(e)[:100]}")
    
    finally:
        await client.stop()
        users[user_id_str]["posting"] = False
        write(users_db, users)

# =================== قسم المالك ===================
@app.on_message(filters.command("admin") & filters.user(owner))
async def admin_panel(_, message: Message):
    markup = Markup([
        [Button("- تفعيل VIP -", callback_data="addVIP"), Button("- إلغاء VIP -", callback_data="cancelVIP")],
        [Button("- الإحصائيات -", callback_data="statics"), Button("- قنوات الاشتراك -", callback_data="channels")]
    ])
    await message.reply("لوحة التحكم", reply_markup=markup)

@app.on_callback_query(filters.user(owner) & filters.regex(r"^(addVIP|cancelVIP|statics|channels)$"))
async def admin_actions(_, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if callback.data == "statics":
        total = len(users)
        vip = sum(1 for u in users.values() if u.get("vip", False))
        posting = sum(1 for u in users.values() if u.get("posting", False))
        await callback.message.edit_text(
            f"📊 **الإحصائيات**\n\n"
            f"👥 إجمالي المستخدمين: {total}\n"
            f"⭐ مستخدمين VIP: {vip}\n"
            f"🔄 يعملون حالياً: {posting}",
            reply_markup=Markup([[Button("- العودة -", callback_data="toAdmin")]])
        )
        return
    
    elif callback.data == "channels":
        markup = []
        for ch in channels:
            markup.append([Button(ch, url=f"https://t.me/{ch}"), Button("🗑", callback_data=f"delchannel_{ch}")])
        markup.append([Button("- إضافة قناة -", callback_data="addChannel")])
        markup.append([Button("- العودة -", callback_data="toAdmin")])
        await callback.message.edit_text("قنوات الاشتراك الإجباري:", reply_markup=Markup(markup))
        return
    
    elif callback.data == "addChannel":
        await callback.message.delete()
        try:
            ask = await listener.listen(
                from_id=user_id, chat_id=user_id,
                text="أرسل معرف القناة بدون @",
                reply_markup=ForceReply(),
                timeout=30
            )
        except:
            return await callback.message.reply("انتهى الوقت")
        
        channels.append(ask.text)
        write(channels_db, channels)
        await ask.reply("✅ تم إضافة القناة", reply_markup=Markup([[Button("- العودة -", callback_data="channels")]]))
        return
    
    elif callback.data.startswith("delchannel_"):
        ch = callback.data.split("_")[1]
        if ch in channels:
            channels.remove(ch)
            write(channels_db, channels)
        await callback.answer("تم الحذف")
        await admin_actions(_, callback)  # إعادة عرض القنوات
    
    elif callback.data in ["addVIP", "cancelVIP"]:
        await callback.message.delete()
        try:
            ask = await listener.listen(
                from_id=user_id, chat_id=user_id,
                text="أرسل معرف المستخدم",
                reply_markup=ForceReply(),
                timeout=30
            )
        except:
            return await callback.message.reply("انتهى الوقت")
        
        target_id = ask.text
        
        if callback.data == "addVIP":
            try:
                days = await listener.listen(
                    from_id=user_id, chat_id=user_id,
                    text="أرسل عدد الأيام",
                    reply_markup=ForceReply(),
                    timeout=30
                )
                days_int = int(days.text)
            except:
                return await callback.message.reply("رقم غير صالح")
            
            if target_id not in users:
                users[target_id] = {"vip": True, "captions": [], "groups": [], "waitTime": 60}
            else:
                users[target_id]["vip"] = True
            
            # حساب تاريخ الانتهاء
            end_date = datetime.now(_timezone) + timedelta(days=days_int)
            users[target_id]["limitation"] = {
                "days": days_int,
                "endDate": end_date.strftime("%Y-%m-%d")
            }
            write(users_db, users)
            await ask.reply(f"✅ تم تفعيل VIP للمستخدم {target_id} لمدة {days_int} يوم")
            try:
                await app.send_message(int(target_id), f"🎉 تم تفعيل VIP لك لمدة {days_int} يوم!")
            except:
                pass
        
        else:  # cancelVIP
            if target_id in users:
                users[target_id]["vip"] = False
                write(users_db, users)
                await ask.reply(f"✅ تم إلغاء VIP للمستخدم {target_id}")
            else:
                await ask.reply("المستخدم غير موجود")

@app.on_callback_query(filters.regex(r"^(toAdmin)$"))
async def to_admin(_, callback: CallbackQuery):
    await callback.message.edit_text("لوحة التحكم", reply_markup=Markup([
        [Button("- تفعيل VIP -", callback_data="addVIP"), Button("- إلغاء VIP -", callback_data="cancelVIP")],
        [Button("- الإحصائيات -", callback_data="statics"), Button("- قنوات الاشتراك -", callback_data="channels")]
    ]))

# =================== إدارة التخزين ===================
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

users_db = "users.json"
channels_db = "channels.json"
users = read(users_db)
channels = read(channels_db)

# =================== إعادة تشغيل المهام ===================
async def reStartPosting():
    await sleep(30)
    for user_id, data in users.items():
        if data.get("posting") and str(user_id) not in active_tasks:
            task = create_task(posting(int(user_id)))
            active_tasks.add(str(user_id))
            task.add_done_callback(lambda t, uid=str(user_id): active_tasks.discard(uid))

@app.on_callback_query(filters.regex(r"^ignore$"))
async def ignore(_, callback: CallbackQuery):
    await callback.answer()

async def main():
    create_task(reStartPosting())
    await app.start()
    print("✅ البوت يعمل!")
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(main())
