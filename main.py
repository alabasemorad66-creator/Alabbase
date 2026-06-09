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
from typing import Union, List, Dict, Any, Optional
import json, random, re

# =================== إعدادات البوت ===================
app = Client(
    "autoPost",
    api_id="34923196",
    api_hash="b3f6e47ecd3231186f8f7e01ab41938e",
    bot_token='8832559640:AAGGV15XucCuMgQ20StPFGPv8LYANTnb0bc'
)
loop = get_event_loop()
listener = Listener(client=app)
owner = 8310839908

# =================== المتغيرات العامة ===================
active_tasks = set()
failed_groups = set()
privacy_protection_active = True

# =================== دوال مساعدة ===================
def get_home_markup(user_id: int) -> Markup:
    """إنشاء أزرار الصفحة الرئيسية"""
    user_data = users.get(str(user_id), {})
    delay_mode_text = "✅ تأخير ذكي مفعل" if user_data.get("smart_delay", True) else "❌ تأخير ذكي معطل"
    delete_mode_text = f"🗑️ حذف: {user_data.get('delete_after', 0)}ث" if user_data.get('delete_after', 0) > 0 else "🗑️ حذف: معطل"
    
    return Markup([
        [Button("- حسابك -", callback_data="account")],
        [Button("- السوبرات -", callback_data="currentSupers"), Button("➕ إضافة", callback_data="newSuper")],
        [Button("- المدة بين النشر -", callback_data="waitTime"), Button("- الكليشات -", callback_data="manageCaptions")],
        [Button("- طريقة التوزيع -", callback_data="distributionMethod")],
        [Button(delete_mode_text, callback_data="deleteTime")],
        [Button("⏹️ إيقاف", callback_data="stopPosting"), Button("▶️ بدء", callback_data="startPosting")],
        [Button(delay_mode_text, callback_data="toggleSmartDelay")]
    ])

def get_distribution_markup(user_id: int) -> Markup:
    """إنشاء أزرار طرق التوزيع الزمني"""
    current = users[str(user_id)].get("distribution_method", "random")
    methods = {
        "equal": "📏 متساوي",
        "random": "🎲 عشوائي", 
        "fibonacci": "📈 فيبوناتشي"
    }
    markup = []
    for key, name in methods.items():
        status = "✅ " if current == key else "❌ "
        markup.append([Button(f"{status}{name}", callback_data=f"setDist_{key}")])
    markup.append([Button("- الرئيسيه -", callback_data="toHome")])
    return Markup(markup)

def calculate_distributed_delays(num_groups: int, total_time: int, method: str = "random") -> List[float]:
    """حساب الفروق الزمنية بين المجموعات حسب الطريقة المختارة"""
    if num_groups <= 1:
        return [0]
    
    if method == "equal":
        # توزيع متساوي - كل مجموعة تنتظر نفس المدة
        delay_per_group = total_time / num_groups
        return [delay_per_group] * num_groups
    
    elif method == "fibonacci":
        # توزيع متزايد حسب تسلسل فيبوناتشي
        fib = [1, 1]
        for i in range(num_groups - 2):
            fib.append(fib[-1] + fib[-2])
        total_fib = sum(fib[:num_groups])
        return [(total_time * f / total_fib) for f in fib[:num_groups]]
    
    else:  # random
        # توزيع عشوائي
        delays = []
        remaining = total_time
        for i in range(num_groups - 1):
            max_delay = min(remaining - (num_groups - i - 1), remaining * 0.8)
            min_delay = max(1, remaining * 0.1)
            delay = random.uniform(min_delay, max_delay)
            delays.append(delay)
            remaining -= delay
        delays.append(remaining)
        random.shuffle(delays)
        return delays

# =================== حماية سياسة الخصوصية ===================
PRIVACY_RESPONSES = [
    "اسمي {name} من {country} عمري {age} سنة",
    "أنا {name} من {country}، عمري {age} سنة",
    "الاسم: {name}\nالعمر: {age}\nالبلد: {country}",
    "{name}\n{age} سنة\n{country}",
    "مرحباً، أنا {name}، {age} عام، من {country}",
    "أنا {name} - {age} سنة - من {country}"
]

COUNTRIES = ["مصر", "السعودية", "الإمارات", "الكويت", "قطر", "عمان", "البحرين", "الأردن", "العراق", "سوريا", "لبنان", "فلسطين", "اليمن", "ليبيا", "تونس", "الجزائر", "المغرب", "السودان"]
NAMES = ["أحمد", "محمد", "علي", "حسن", "حسين", "عمر", "عثمان", "خالد", "يوسف", "إبراهيم", "محمود", "مصطفى", "كريم", "سعيد", "نبيل"]
AGES = list(range(18, 65))

async def handle_privacy_bot(client: Client, message: Message, user_id: int) -> bool:
    """معالجة رسائل بوت سياسة الخصوصية بشكل ذكي"""
    global privacy_protection_active
    
    if not privacy_protection_active:
        return False
    
    if not message.text:
        return False
        
    text = message.text.lower()
    
    # كشف نماذج الأسئلة
    privacy_keywords = [
        "tell me about yourself", "introduce yourself", "who are you",
        "what is your name", "how old are you", "where are you from",
        "your name", "your age", "your country", "tell us about you",
        "give me information", "personal information", "about you",
        "عرف نفسك", "من انت", "ما اسمك", "كم عمرك", "من اين انت",
        "اعرف عنك", "معلومات عنك", "الاسم", "العمر", "البلد"
    ]
    
    if any(kw in text for kw in privacy_keywords):
        await sleep(random.uniform(3, 8))
        
        response = random.choice(PRIVACY_RESPONSES).format(
            name=random.choice(NAMES),
            age=random.choice(AGES),
            country=random.choice(COUNTRIES)
        )
        
        try:
            await client.send_message(message.chat.id, response)
            return True
        except:
            pass
    
    return False

# =================== دالة الإرسال المحسنة ===================
async def send_to_group(client: Client, user_id: int, group_id: int, caption: str, invite_link: Optional[str] = None) -> bool:
    """إرسال رسالة إلى المجموعة مع حماية متكاملة"""
    user_id_str = str(user_id)
    global failed_groups
    
    if (user_id_str, group_id) in failed_groups:
        return False
    
    try:
        sent_msg = await client.send_message(group_id, caption)
        
        delete_after = users[user_id_str].get("delete_after", 0)
        if delete_after > 0:
            create_task(delete_message_after(sent_msg, delete_after))
        
        print(f"✅ تم الإرسال إلى المجموعة: {group_id}")
        return True
        
    except (PeerIdInvalid, ChatWriteForbidden, UserNotParticipant) as e:
        # محاولة الانضمام للمجموعة
        joined = False
        
        if invite_link:
            try:
                await client.join_chat(invite_link)
                joined = True
                print(f"✅ تم الانضمام عبر الرابط: {invite_link}")
            except Exception as join_err:
                print(f"فشل الانضمام عبر الرابط: {join_err}")
        
        if not joined:
            try:
                await client.join_chat(group_id)
                joined = True
                print(f"✅ تم الانضمام عبر المعرف: {group_id}")
            except Exception as join_err:
                print(f"فشل الانضمام عبر المعرف: {join_err}")
        
        if joined:
            try:
                sent_msg = await client.send_message(group_id, caption)
                delete_after = users[user_id_str].get("delete_after", 0)
                if delete_after > 0:
                    create_task(delete_message_after(sent_msg, delete_after))
                print(f"✅ تم الإرسال بعد الانضمام إلى: {group_id}")
                return True
            except Exception as send_err:
                print(f"فشل الإرسال بعد الانضمام: {send_err}")
        
        failed_groups.add((user_id_str, group_id))
        await app.send_message(user_id, f"❌ فشل الوصول إلى المجموعة {group_id}")
        return False
        
    except FloodWait as e:
        await app.send_message(user_id, f"⚠️ انتظر {e.value} ثانية")
        await sleep(e.value)
        return await send_to_group(client, user_id, group_id, caption, invite_link)
        
    except Exception as e:
        error_type = type(e).__name__
        print(f"⚠️ خطأ: {error_type} - {e}")
        return False

async def delete_message_after(message: Message, seconds: int):
    """حذف رسالة بعد وقت محدد"""
    await sleep(seconds)
    try:
        await message.delete()
    except:
        pass

# =================== دالة النشر الرئيسية - الحل الصحيح ===================
async def posting(user_id: int):
    """نشر تلقائي متقدم - يرسل لجميع المجموعات"""
    user_id_str = str(user_id)
    
    if not users.get(user_id_str, {}).get("posting"):
        return
    
    # تشغيل عميل المستخدم
    client = Client(user_id_str, api_id=app.api_id, api_hash=app.api_hash, 
                    session_string=users[user_id_str]["session"])
    await client.start()
    
    try:
        while users[user_id_str].get("posting"):
            # قراءة الإعدادات
            total_time = users[user_id_str].get("waitTime", 60)
            groups_data = users[user_id_str].get("groups", []).copy()
            captions_list = users[user_id_str].get("captions", []).copy()
            distribution_method = users[user_id_str].get("distribution_method", "random")
            
            # التحققات
            if not captions_list:
                users[user_id_str]["posting"] = False
                write(users_db, users)
                await app.send_message(user_id, "❌ تم إيقاف النشر: لا توجد كليشات")
                break
            
            if not groups_data:
                users[user_id_str]["posting"] = False
                write(users_db, users)
                await app.send_message(user_id, "❌ تم إيقاف النشر: لا توجد مجموعات")
                break
            
            num_groups = len(groups_data)
            await app.send_message(user_id, f"🚀 بدء دورة نشر جديدة\n📊 عدد المجموعات: {num_groups}\n⏱️ المدة الإجمالية: {total_time} ثانية")
            
            # خلط المجموعات عشوائياً
            random.shuffle(groups_data)
            
            # حساب التوزيع الزمني
            delays = calculate_distributed_delays(num_groups, total_time, distribution_method)
            
            # إنشاء نسخة من الكليشات
            available_captions = captions_list.copy()
            
            # الإرسال لجميع المجموعات
            for idx, group_obj in enumerate(groups_data):
                if not users[user_id_str].get("posting"):
                    break
                
                group_id = group_obj["id"]
                invite_link = group_obj.get("link")
                
                # اختيار كليشة عشوائية
                if not available_captions:
                    available_captions = captions_list.copy()
                
                chosen_caption = random.choice(available_captions)
                available_captions.remove(chosen_caption)
                
                # إرسال الرسالة
                success = await send_to_group(client, user_id, group_id, chosen_caption, invite_link)
                
                if success:
                    await app.send_message(user_id, f"✅ تم الإرسال إلى المجموعة {idx+1}/{num_groups}")
                else:
                    await app.send_message(user_id, f"❌ فشل الإرسال إلى المجموعة {idx+1}/{num_groups}")
                
                # انتظار الفرق الزمني قبل المجموعة التالية (وليس بعدها)
                if idx < len(delays) - 1:
                    wait_time = delays[idx]
                    await app.send_message(user_id, f"⏳ انتظار {wait_time:.1f} ثانية قبل المجموعة التالية...")
                    await sleep(wait_time)
            
            # انتظار المدة الإجمالية قبل الدورة التالية
            await app.send_message(user_id, f"⏸️ اكتملت الدورة، انتظار {total_time} ثانية قبل الدورة التالية...")
            await sleep(total_time)
            
    except Exception as e:
        print(f"خطأ في النشر: {e}")
        await app.send_message(user_id, f"⚠️ حدث خطأ: {type(e).__name__}")
    finally:
        await client.stop()

# =================== أوامر المستخدم ===================
@app.on_message(filters.command("start") & filters.private)
async def start(_: Client, message: Message):
    user_id = message.from_user.id
    
    # التحقق من الإشتراك
    subscribed = await subscription(message)
    if isinstance(subscribed, str):
        return await message.reply(f"⚠️ عليك الإشتراك بقناة البوت أولاً\n📢 القناة: @{subscribed}\nاشترك ثم ارسل /start")
    
    # إنشاء حساب جديد
    if str(user_id) not in users:
        users[str(user_id)] = {
            "vip": True if user_id == owner else False,
            "smart_delay": True,
            "captions": [],
            "groups": [],
            "distribution_method": "random",
            "delete_after": 0,
            "waitTime": 60
        }
        write(users_db, users)
    
    # التحقق من الـ VIP
    if user_id != owner and not users[str(user_id)].get("vip", False):
        return await message.reply(f"⚠️ لا يمكنك استخدام هذا البوت\n👤 تواصل مع [المطور](tg://openmessage?user_id={owner}) لتفعيل الإشتراك")
    
    fname = message.from_user.first_name
    caption = f"✨ مرحبا [{fname}](tg://settings)\n🤖 بوت النشر التلقائي\n📝 استخدم الأزرار للتحكم:"
    await message.reply(caption, reply_markup=get_home_markup(user_id))

@app.on_callback_query(filters.regex(r"^(toHome)$"))
async def toHome(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    fname = callback.from_user.first_name
    caption = f"✨ مرحبا [{fname}](tg://settings)\n🤖 بوت النشر التلقائي"
    await callback.message.edit_text(caption, reply_markup=get_home_markup(user_id))

# =================== إدارة الحساب ===================
@app.on_callback_query(filters.regex(r"^(account)$"))
async def account(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    has_session = users[str(user_id)].get("session") is not None
    status = "✅ مسجل" if has_session else "❌ غير مسجل"
    
    caption = f"👤 **الحساب**\n\nالحالة: {status}"
    markup = Markup([
        [Button("- تسجيل حساب -", callback_data="login")],
        [Button("- تغيير الحساب -", callback_data="changeAccount")] if has_session else [],
        [Button("- العوده -", callback_data="toHome")]
    ])
    await callback.message.edit_text(caption, reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(login|changeAccount)$"))
async def login(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="📱 أرسل رقم هاتفك مع رمز الدولة\nمثال: +966512345678\n/cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="account")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("✅ تم الإلغاء")
    
    await registration(ask)

async def registration(message: Message):
    user_id = message.from_user.id
    phone = message.text.strip()
    
    msg = await message.reply("🔄 جاري تسجيل الدخول...")
    
    client = Client("temp", in_memory=True, api_id=app.api_id, api_hash=app.api_hash)
    await client.connect()
    
    try:
        sent_code = await client.send_code(phone)
    except PhoneNumberInvalid:
        return await msg.edit("❌ رقم الهاتف غير صحيح")
    
    try:
        code = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="🔑 تم إرسال الكود. أرسله الآن:",
            reply_markup=ForceReply(selective=True),
            timeout=120
        )
    except exceptions.TimeOut:
        return await msg.edit("⏰ انتهى وقت الكود")
    
    try:
        await client.sign_in(phone, sent_code.phone_code_hash, code.text)
    except SessionPasswordNeeded:
        try:
            password = await listener.listen(
                from_id=user_id, chat_id=user_id,
                text="🔒 حسابك مفعل بالتحقق بخطوتين\nأرسل كلمة المرور:",
                reply_markup=ForceReply(selective=True),
                timeout=60
            )
        except exceptions.TimeOut:
            return await msg.edit("⏰ انتهى الوقت")
        await client.check_password(password.text)
    
    session = await client.export_session_string()
    await client.disconnect()
    
    users[str(user_id)]["session"] = session
    write(users_db, users)
    
    await app.send_message(user_id, "✅ تم تسجيل الدخول بنجاح", 
                          reply_markup=Markup([[Button("- الرئيسيه -", callback_data="toHome")]]))

# =================== إدارة السوبرات ===================
@app.on_callback_query(filters.regex(r"^(newSuper)$"))
async def newSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="➕ أرسل رابط أو معرف المجموعة\nمثال: @username أو https://t.me/username\n/cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("✅ تم الإلغاء")
    
    input_text = ask.text.strip()
    group_id = None
    invite_link = None
    
    # معالجة المعرف
    if input_text.startswith("@"):
        username = input_text[1:]
        try:
            chat = await app.get_chat(username)
            group_id = chat.id
            invite_link = input_text
        except:
            return await ask.reply("❌ لم يتم العثور على المجموعة")
    
    # معالجة الرابط
    elif "t.me/" in input_text:
        username = input_text.split("t.me/")[-1]
        try:
            chat = await app.get_chat(username)
            group_id = chat.id
            invite_link = input_text
        except:
            return await ask.reply("❌ رابط غير صالح")
    
    # معالجة الأيدي
    elif input_text.lstrip("-").isdigit():
        group_id = int(input_text)
    
    else:
        return await ask.reply("❌ صيغة غير صالحة")
    
    if group_id:
        if "groups" not in users[str(user_id)]:
            users[str(user_id)]["groups"] = []
        
        # التحقق من عدم التكرار
        existing = [g for g in users[str(user_id)]["groups"] if g["id"] == group_id]
        if existing:
            return await ask.reply("⚠️ هذه المجموعة موجودة بالفعل")
        
        users[str(user_id)]["groups"].append({"id": group_id, "link": invite_link})
        write(users_db, users)
        
        try:
            chat = await app.get_chat(group_id)
            title = chat.title
        except:
            title = str(group_id)
        
        await ask.reply(f"✅ تم إضافة المجموعة: {title}\n📊 العدد الحالي: {len(users[str(user_id)]['groups'])}",
                       reply_markup=Markup([[Button("- الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(currentSupers)$"))
async def currentSupers(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    groups = users[str(user_id)].get("groups", [])
    
    if not groups:
        return await callback.answer("📭 لا توجد مجموعات", show_alert=True)
    
    markup = []
    for g in groups:
        try:
            chat = await app.get_chat(g["id"])
            title = chat.title[:25]
        except:
            title = str(g["id"])[:25]
        markup.append([Button(f"📢 {title}", callback_data=f"super_{g['id']}"), 
                      Button("🗑️", callback_data=f"delSuper_{g['id']}")])
    
    markup.append([Button("- الرئيسيه -", callback_data="toHome")])
    await callback.message.edit_text(f"📋 **المجموعات ({len(groups)})**:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^delSuper_"))
async def delSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    gid = int(callback.data.split("_")[1])
    
    groups = users[str(user_id)].get("groups", [])
    users[str(user_id)]["groups"] = [g for g in groups if g["id"] != gid]
    write(users_db, users)
    
    await callback.answer("✅ تم الحذف", show_alert=True)
    await currentSupers(_, callback)

# =================== إدارة الكليشات ===================
@app.on_callback_query(filters.regex(r"^(manageCaptions)$"))
async def manageCaptions(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    captions = users[str(user_id)].get("captions", [])
    
    markup = []
    for idx, cap in enumerate(captions):
        short = cap[:20] + "..." if len(cap) > 20 else cap
        markup.append([Button(f"📝 {short}", callback_data=f"viewCap_{idx}"), 
                      Button("🗑️", callback_data=f"delCap_{idx}")])
    
    markup.append([Button("➕ إضافة كليشة", callback_data="addCaption")])
    markup.append([Button("- الرئيسيه -", callback_data="toHome")])
    
    count = len(captions)
    if count == 0:
        await callback.message.edit_text("📭 **لا توجد كليشات**\n➕ أضف كليشة جديدة:", reply_markup=Markup(markup))
    else:
        await callback.message.edit_text(f"📝 **الكليشات ({count})**:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addCaption)$"))
async def addCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="📝 أرسل نص الكليشة الجديدة\n/cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=120
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="manageCaptions")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("✅ تم الإلغاء")
    
    captions = users[str(user_id)].get("captions", [])
    captions.append(ask.text)
    users[str(user_id)]["captions"] = captions
    write(users_db, users)
    
    await ask.reply(f"✅ تم إضافة الكليشة\n📊 العدد الحالي: {len(captions)}",
                   reply_markup=Markup([[Button("- العوده -", callback_data="manageCaptions")]]))

@app.on_callback_query(filters.regex(r"^delCap_"))
async def delCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    
    captions = users[str(user_id)].get("captions", [])
    if 0 <= idx < len(captions):
        captions.pop(idx)
        users[str(user_id)]["captions"] = captions
        write(users_db, users)
        await callback.answer("✅ تم الحذف", show_alert=True)
    
    await manageCaptions(_, callback)

@app.on_callback_query(filters.regex(r"^viewCap_"))
async def viewCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    
    captions = users[str(user_id)].get("captions", [])
    if 0 <= idx < len(captions):
        await callback.answer("📄 معاينة:", show_alert=True)
        await callback.message.reply(f"**نص الكليشة:**\n{captions[idx]}", 
                                    reply_markup=Markup([[Button("- العوده -", callback_data="manageCaptions")]]))

# =================== إعدادات النشر ===================
@app.on_callback_query(filters.regex(r"^(waitTime)$"))
async def waitTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    current = users[str(user_id)].get("waitTime", 60)
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text=f"⏱️ **المدة الحالية:** {current} ثانية\n\nأرسل المدة الجديدة (بالثواني)\nالحد الأدنى: 10 ثوانٍ\n/cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("✅ تم الإلغاء")
    
    try:
        wait = int(ask.text)
        if wait < 10:
            return await ask.reply("⚠️ المدة يجب أن تكون 10 ثوانٍ على الأقل")
        users[str(user_id)]["waitTime"] = wait
        write(users_db, users)
        await ask.reply(f"✅ تم تعيين المدة: {wait} ثانية", 
                       reply_markup=Markup([[Button("- الرئيسيه -", callback_data="toHome")]]))
    except ValueError:
        await ask.reply("❌ أرسل رقماً صحيحاً")

@app.on_callback_query(filters.regex(r"^(deleteTime)$"))
async def deleteTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    current = users[str(user_id)].get("delete_after", 0)
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text=f"🗑️ **مدة الحذف الحالية:** {current if current > 0 else 'معطل'}\n\nأرسل المدة الجديدة (بالثواني)\n0 = تعطيل الحذف\n/cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("✅ تم الإلغاء")
    
    try:
        delete_after = int(ask.text)
        if delete_after < 0:
            return await ask.reply("⚠️ أدخل قيمة 0 أو أكثر")
        users[str(user_id)]["delete_after"] = delete_after
        write(users_db, users)
        status = "معطل" if delete_after == 0 else f"{delete_after} ثانية"
        await ask.reply(f"✅ تم تعيين مدة الحذف: {status}", 
                       reply_markup=Markup([[Button("- الرئيسيه -", callback_data="toHome")]]))
    except ValueError:
        await ask.reply("❌ أرسل رقماً صحيحاً")

@app.on_callback_query(filters.regex(r"^(distributionMethod)$"))
async def distributionMethod(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text("📊 **اختر طريقة توزيع الفروق الزمنية:**", 
                                    reply_markup=get_distribution_markup(user_id))

@app.on_callback_query(filters.regex(r"^setDist_"))
async def setDistribution(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    method = callback.data.split("_")[1]
    
    users[str(user_id)]["distribution_method"] = method
    write(users_db, users)
    
    method_names = {"equal": "المتساوي", "random": "العشوائي", "fibonacci": "فيبوناتشي"}
    await callback.answer(f"✅ تم تعيين طريقة {method_names[method]}", show_alert=True)
    await distributionMethod(_, callback)

@app.on_callback_query(filters.regex(r"^(toggleSmartDelay)$"))
async def toggleSmartDelay(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    current = users[str(user_id)].get("smart_delay", True)
    users[str(user_id)]["smart_delay"] = not current
    write(users_db, users)
    await callback.answer(f"✅ تم {'تفعيل' if not current else 'تعطيل'} التأخير الذكي", show_alert=True)
    await toHome(_, callback)

# =================== بدء وإيقاف النشر ===================
@app.on_callback_query(filters.regex(r"^(startPosting)$"))
async def startPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not users[str(user_id)].get("session"):
        return await callback.answer("❌ يجب تسجيل حساب أولاً", show_alert=True)
    
    if not users[str(user_id)].get("groups"):
        return await callback.answer("❌ يجب إضافة مجموعات أولاً", show_alert=True)
    
    if not users[str(user_id)].get("captions"):
        return await callback.answer("❌ يجب إضافة كليشات أولاً", show_alert=True)
    
    if users[str(user_id)].get("posting"):
        return await callback.answer("⚠️ النشر مفعل بالفعل", show_alert=True)
    
    users[str(user_id)]["posting"] = True
    write(users_db, users)
    
    task = create_task(posting(user_id))
    active_tasks.add(str(user_id))
    task.add_done_callback(lambda t: active_tasks.discard(str(user_id)))
    
    groups_count = len(users[str(user_id)]["groups"])
    captions_count = len(users[str(user_id)]["captions"])
    wait_time = users[str(user_id)].get("waitTime", 60)
    
    await callback.message.edit_text(
        f"🚀 **بدء النشر التلقائي**\n\n"
        f"📊 المجموعات: {groups_count}\n"
        f"📝 الكليشات: {captions_count}\n"
        f"⏱️ المدة: {wait_time} ثانية\n\n"
        f"✅ سيتم الإرسال لجميع المجموعات",
        reply_markup=Markup([[Button("⏹️ إيقاف", callback_data="stopPosting"), 
                             Button("🏠 الرئيسيه", callback_data="toHome")]])
    )

@app.on_callback_query(filters.regex(r"^(stopPosting)$"))
async def stopPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not users[str(user_id)].get("posting"):
        return await callback.answer("⚠️ النشر معطل بالفعل", show_alert=True)
    
    users[str(user_id)]["posting"] = False
    write(users_db, users)
    
    await callback.message.edit_text("🛑 **تم إيقاف النشر التلقائي**", 
                                    reply_markup=Markup([[Button("▶️ بدء", callback_data="startPosting"), 
                                                         Button("🏠 الرئيسيه", callback_data="toHome")]]))

# =================== قسم المالك ===================
async def isOwner(_, __, message: Message) -> bool:
    return message.from_user.id == owner

owner_filter = filters.create(isOwner)

@app.on_message(filters.command("admin") & filters.private & owner_filter)
async def adminPanel(_: Client, message: Message):
    await message.reply("👑 **لوحة تحكم المالك**", reply_markup=Markup([
        [Button("➕ تفعيل VIP", callback_data="addVIP"), Button("➖ الغاء VIP", callback_data="cancelVIP")],
        [Button("📊 الاحصائيات", callback_data="statics"), Button("📢 قنوات الإشتراك", callback_data="channels")],
        [Button("🛡️ حماية الخصوصية", callback_data="privacyProtection")]
    ]))

@app.on_callback_query(filters.regex("addVIP") & owner_filter)
async def addVIP(_: Client, callback: CallbackQuery):
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=owner, chat_id=owner,
            text="👤 أرسل ايدي المستخدم",
            reply_markup=ForceReply(selective=True),
            timeout=30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت")
    
    try:
        user_id = int(ask.text)
    except:
        return await ask.reply("❌ ايدي غير صالح")
    
    try:
        days = await listener.listen(
            from_id=owner, chat_id=owner,
            text="📅 أرسل عدد الأيام",
            reply_markup=ForceReply(selective=True),
            timeout=30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت")
    
    try:
        limit_days = int(days.text)
    except:
        return await days.reply("❌ أرسل رقماً صحيحاً")
    
    if str(user_id) not in users:
        users[str(user_id)] = {"vip": True, "smart_delay": True, "captions": [], "groups": [], "waitTime": 60}
    else:
        users[str(user_id)]["vip"] = True
    
    end_date = datetime.now(_timezone) + timedelta(days=limit_days)
    users[str(user_id)]["limitation"] = {
        "days": limit_days,
        "endDate": end_date.strftime("%Y-%m-%d"),
        "endTime": end_date.strftime("%H:%M")
    }
    write(users_db, users)
    
    await days.reply(f"✅ تم تفعيل VIP للمستخدم {user_id}\n📅 المدة: {limit_days} يوم",
                    reply_markup=Markup([[Button("- العوده -", callback_data="admin")]]))

@app.on_callback_query(filters.regex("cancelVIP") & owner_filter)
async def cancelVIP(_: Client, callback: CallbackQuery):
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=owner, chat_id=owner,
            text="👤 أرسل ايدي المستخدم",
            reply_markup=ForceReply(selective=True),
            timeout=30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت")
    
    user_id = ask.text
    if user_id in users:
        users[user_id]["vip"] = False
        write(users_db, users)
        await ask.reply(f"✅ تم الغاء VIP للمستخدم {user_id}",
                       reply_markup=Markup([[Button("- العوده -", callback_data="admin")]]))
    else:
        await ask.reply("❌ المستخدم غير موجود")

@app.on_callback_query(filters.regex("statics") & owner_filter)
async def statics(_: Client, callback: CallbackQuery):
    total = len(users)
    vip = sum(1 for u in users.values() if u.get("vip", False))
    posting = sum(1 for u in users.values() if u.get("posting", False))
    total_groups = sum(len(u.get("groups", [])) for u in users.values())
    total_captions = sum(len(u.get("captions", [])) for u in users.values())
    
    await callback.message.edit_text(
        f"📊 **الإحصائيات**\n\n"
        f"👥 إجمالي المستخدمين: {total}\n"
        f"⭐ مستخدمي VIP: {vip}\n"
        f"🚀 النشر مفعل: {posting}\n"
        f"📢 إجمالي المجموعات: {total_groups}\n"
        f"📝 إجمالي الكليشات: {total_captions}",
        reply_markup=Markup([[Button("- العوده -", callback_data="admin")]])
    )

@app.on_callback_query(filters.regex("channels") & owner_filter)
async def channelsControl(_: Client, callback: CallbackQuery):
    markup = []
    for ch in channels:
        markup.append([Button(f"📢 @{ch}", url=f"https://t.me/{ch}"), 
                      Button("🗑️", callback_data=f"removeChannel_{ch}")])
    markup.append([Button("➕ إضافة قناة", callback_data="addChannel")])
    markup.append([Button("- العوده -", callback_data="admin")])
    
    await callback.message.edit_text("📢 **قنوات الإشتراك الإجباري**", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex("addChannel") & owner_filter)
async def addChannel(_: Client, callback: CallbackQuery):
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=owner, chat_id=owner,
            text="📢 أرسل معرف القناة (بدون @)\nمثال: channelusername",
            reply_markup=ForceReply(selective=True),
            timeout=30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت")
    
    channel = ask.text.strip()
    channels.append(channel)
    write(channels_db, channels)
    
    await ask.reply(f"✅ تم إضافة قناة @{channel}",
                   reply_markup=Markup([[Button("- العوده -", callback_data="channels")]]))

@app.on_callback_query(filters.regex("removeChannel_") & owner_filter)
async def removeChannel(_: Client, callback: CallbackQuery):
    channel = callback.data.split("_")[1]
    if channel in channels:
        channels.remove(channel)
        write(channels_db, channels)
        await callback.answer("✅ تم الحذف", show_alert=True)
    await channelsControl(_, callback)

@app.on_callback_query(filters.regex("privacyProtection") & owner_filter)
async def privacyProtection(_: Client, callback: CallbackQuery):
    global privacy_protection_active
    privacy_protection_active = not privacy_protection_active
    
    status = "مفعلة ✅" if privacy_protection_active else "معطلة ❌"
    await callback.answer(f"حماية الخصوصية {status}", show_alert=True)
    await callback.message.edit_text(
        f"🛡️ **حماية سياسة الخصوصية**\n\n"
        f"الحالة: {status}\n\n"
        f"عند التفعيل، يقوم البوت بالرد تلقائياً على أسئلة بوتات الخصوصية\n"
        f"بإجابات عشوائية تحاكي المستخدمين الحقيقيين.",
        reply_markup=Markup([[Button("- العوده -", callback_data="admin")]])
    )

# =================== الإشتراك الإجباري ===================
async def subscription(message: Message) -> Union[bool, str]:
    user_id = message.from_user.id
    for channel in channels:
        try:
            await app.get_chat_member(channel, user_id)
        except UserNotParticipant:
            return channel
    return True

# =================== إدارة التخزين ===================
def write(file_path: str, data: Any):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def read(file_path: str) -> Any:
    if not os.path.exists(file_path):
        write(file_path, {} if "users" in file_path else [])
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# =================== دوال إعادة التشغيل ===================
async def restartPosting():
    await sleep(30)
    for user_id, data in users.items():
        if data.get("posting") and str(user_id) not in active_tasks:
            task = create_task(posting(int(user_id)))
            active_tasks.add(str(user_id))
            task.add_done_callback(lambda t, uid=str(user_id): active_tasks.discard(uid))

async def checkVIPExpiry():
    while True:
        now = datetime.now(_timezone)
        for user_id, data in users.items():
            if data.get("vip") and "limitation" in data:
                end_date_str = f"{data['limitation']['endDate']} {data['limitation']['endTime']}"
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M")
                end_date = _timezone.localize(end_date)
                
                if now >= end_date:
                    data["vip"] = False
                    write(users_db, users)
                    try:
                        await app.send_message(int(user_id), "⚠️ انتهت صلاحية الاشتراك VIP")
                    except:
                        pass
        await sleep(3600)

# =================== التشغيل الرئيسي ===================
_timezone = timezone("Asia/Baghdad")
users_db = "users.json"
channels_db = "channels.json"
users = read(users_db)
channels = read(channels_db)

async def main():
    print("🤖 تشغيل البوت...")
    create_task(restartPosting())
    create_task(checkVIPExpiry())
    await app.start()
    print("✅ البوت يعمل بنجاح!")
    print(f"👑 المطور: {owner}")
    print(f"📊 المستخدمين: {len(users)}")
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(main())
