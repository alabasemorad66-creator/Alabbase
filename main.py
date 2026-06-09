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
    delete_mode_text = f"🗑️ حذف تلقائي: {user_data.get('delete_after', 0)}ث" if user_data.get('delete_after', 0) > 0 else "🗑️ حذف تلقائي: معطل"
    
    return Markup([
        [Button("- حسابك -", callback_data="account")],
        [Button("- السوبرات الحاليه -", callback_data="currentSupers"), Button("- إضافة سوبر -", callback_data="newSuper")],
        [Button("- تعيين المدة بين كل نشر -", callback_data="waitTime"), Button("- إدارة الكليشات -", callback_data="manageCaptions")],
        [Button("- طريقة التوزيع الزمني -", callback_data="distributionMethod")],
        [Button(delete_mode_text, callback_data="deleteTime")],
        [Button("- ايقاف النشر -", callback_data="stopPosting"), Button("- بدء النشر -", callback_data="startPosting")],
        [Button(delay_mode_text, callback_data="toggleSmartDelay")]
    ])

def get_distribution_markup(user_id: int) -> Markup:
    """إنشاء أزرار طرق التوزيع الزمني"""
    current = users[str(user_id)].get("distribution_method", "random")
    methods = {
        "equal": "📏 متساوي",
        "random": "🎲 عشوائي", 
        "fibonacci": "📈 متزايد (فيبوناتشي)"
    }
    markup = []
    for key, name in methods.items():
        status = "✅ " if current == key else "❌ "
        markup.append([Button(f"{status}{name}", callback_data=f"setDist_{key}")])
    markup.append([Button("- العوده للرئيسيه -", callback_data="toHome")])
    return Markup(markup)

def calculate_distributed_delays(num_groups: int, total_time: int, method: str = "random") -> List[float]:
    """حساب الفروق الزمنية بين المجموعات حسب الطريقة المختارة"""
    if num_groups <= 1:
        return []
    
    if method == "equal":
        # توزيع متساوي
        delay = total_time / num_groups
        return [delay] * num_groups
    
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
    
    text = message.text.lower() if message.text else ""
    
    # كشف نماذج الأسئلة
    privacy_keywords = [
        "tell me about yourself", "introduce yourself", "who are you",
        "what is your name", "how old are you", "where are you from",
        "your name", "your age", "your country", "tell us about you",
        "give me information", "personal information", "about you"
    ]
    
    # كلمات عربية
    arabic_keywords = [
        "عرف نفسك", "من انت", "ما اسمك", "كم عمرك", "من اين انت",
        "اعرف عنك", "معلومات عنك", "الاسم", "العمر", "البلد", "الموطن"
    ]
    
    is_privacy_question = any(kw in text for kw in privacy_keywords) or any(kw in text for kw in arabic_keywords)
    
    if is_privacy_question:
        # تأخير طبيعي لمحاكاة البشر
        await sleep(random.uniform(5, 15))
        
        # إنشاء رد عشوائي
        response_template = random.choice(PRIVACY_RESPONSES)
        response = response_template.format(
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

# =================== دالة الإرسال المحسنة مع الحماية ===================
async def send_to_group(client: Client, user_id: int, group_id: int, caption: str, invite_link: Optional[str] = None) -> bool:
    """إرسال رسالة إلى المجموعة مع حماية متكاملة"""
    user_id_str = str(user_id)
    global failed_groups
    
    # التحقق من المجموعة الفاشلة
    if (user_id_str, group_id) in failed_groups:
        return False
    
    try:
        # محاولة الإرسال
        sent_msg = await client.send_message(group_id, caption)
        
        # حذف الرسالة بعد المدة المحددة
        delete_after = users[user_id_str].get("delete_after", 0)
        if delete_after > 0:
            create_task(delete_message_after(sent_msg, delete_after))
        
        return True
        
    except PeerIdInvalid:
        # محاولة الانضمام للمجموعة
        await app.send_message(user_id, f"⚠️ الحساب ليس عضواً في المجموعة. جاري محاولة الانضمام...")
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
                sent_msg = await client.send_message(group_id, caption)
                delete_after = users[user_id_str].get("delete_after", 0)
                if delete_after > 0:
                    create_task(delete_message_after(sent_msg, delete_after))
                await app.send_message(user_id, f"✅ تم الانضمام والإرسال إلى المجموعة")
                return True
            except:
                pass
        
        failed_groups.add((user_id_str, group_id))
        await app.send_message(user_id, f"❌ فشل الانضمام إلى المجموعة. يرجى إضافة الحساب يدوياً.")
        return False
        
    except (ChatWriteForbidden, UserNotParticipant):
        # نفس منطق الانضمام أعلاه
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
                sent_msg = await client.send_message(group_id, caption)
                delete_after = users[user_id_str].get("delete_after", 0)
                if delete_after > 0:
                    create_task(delete_message_after(sent_msg, delete_after))
                await app.send_message(user_id, f"✅ تم الانضمام والإرسال إلى المجموعة")
                return True
            except:
                pass
        await app.send_message(user_id, f"❌ لا توجد صلاحية كتابة في المجموعة")
        failed_groups.add((user_id_str, group_id))
        return False
        
    except FloodWait as e:
        await app.send_message(user_id, f"⚠️ انتظر {e.value} ثانية بسبب الفيض")
        await sleep(e.value)
        return await send_to_group(client, user_id, group_id, caption, invite_link)
        
    except Exception as e:
        error_type = type(e).__name__
        if "FloodWait" not in error_type:
            await app.send_message(user_id, f"⚠️ خطأ: {error_type}")
        return False

async def delete_message_after(message: Message, seconds: int):
    """حذف رسالة بعد وقت محدد"""
    await sleep(seconds)
    try:
        await message.delete()
    except:
        pass

# =================== دالة النشر الرئيسية المتطورة ===================
async def posting(user_id: int):
    """نشر تلقائي متقدم مع توزيع ذكي وحماية"""
    user_id_str = str(user_id)
    
    if not users.get(user_id_str, {}).get("posting"):
        return
    
    # تشغيل عميل المستخدم
    client = Client(user_id_str, api_id=app.api_id, api_hash=app.api_hash, 
                    session_string=users[user_id_str]["session"])
    await client.start()
    
    # تمكين حماية الخصوصية
    client.add_handler(handle_privacy_bot)
    
    try:
        while users[user_id_str].get("posting"):
            # قراءة الإعدادات
            total_time = users[user_id_str].get("waitTime", 60)
            groups_data = users[user_id_str].get("groups", []).copy()
            captions_list = users[user_id_str].get("captions", []).copy()
            distribution_method = users[user_id_str].get("distribution_method", "random")
            
            # التحقق من وجود كليشات
            if not captions_list:
                users[user_id_str]["posting"] = False
                write(users_db, users)
                await app.send_message(user_id, "- تم إيقاف النشر بسبب عدم وجود كليشات.")
                break
            
            # التحقق من وجود مجموعات
            if not groups_data:
                users[user_id_str]["posting"] = False
                write(users_db, users)
                await app.send_message(user_id, "- تم إيقاف النشر بسبب عدم وجود مجموعات.")
                break
            
            # خلط المجموعات عشوائياً
            random.shuffle(groups_data)
            
            # حساب التوزيع الزمني
            num_groups = len(groups_data)
            delays = calculate_distributed_delays(num_groups, total_time, distribution_method)
            
            # إنشاء نسخة من الكليشات للاختيار العشوائي
            available_captions = captions_list.copy()
            used_captions = []
            
            # إرسال لكل مجموعة
            for idx, group_obj in enumerate(groups_data):
                if not users[user_id_str].get("posting"):
                    break
                
                group_id = group_obj["id"]
                invite_link = group_obj.get("link")
                
                # اختيار كليشة عشوائية (تجنب التكرار في نفس الدورة)
                if len(available_captions) == 0:
                    available_captions = captions_list.copy()
                    used_captions = []
                
                chosen_caption = random.choice(available_captions)
                available_captions.remove(chosen_caption)
                used_captions.append(chosen_caption)
                
                # إرسال الرسالة
                await send_to_group(client, user_id, group_id, chosen_caption, invite_link)
                
                # انتظار الفرق الزمني قبل المجموعة التالية
                if idx < len(delays) - 1:
                    await sleep(delays[idx])
            
            # انتظار المدة الإجمالية قبل الدورة التالية
            await sleep(total_time)
            
    finally:
        await client.stop()

# =================== أوامر المستخدم ===================
@app.on_message(filters.command("start") & filters.private)
async def start(_: Client, message: Message):
    user_id = message.from_user.id
    
    # التحقق من الإشتراك
    subscribed = await subscription(message)
    if isinstance(subscribed, str):
        return await message.reply(f"- عذرا عليك الإشتراك بقناة البوت أولاً\n- القناة: @{subscribed}\n- اشترك ثم ارسل /start")
    
    # إنشاء حساب جديد
    if str(user_id) not in users:
        users[str(user_id)] = {
            "vip": True if user_id == owner else False,
            "smart_delay": True,
            "captions": [],
            "groups": [],
            "distribution_method": "random",
            "delete_after": 0
        }
        write(users_db, users)
    
    # التحقق من الـ VIP
    if user_id != owner and not users[str(user_id)].get("vip", False):
        return await message.reply(f"- لا يمكنك استخدام هذا البوت.\n- تواصل مع [المطور](tg://openmessage?user_id={owner}) لتفعيل الإشتراك")
    
    fname = message.from_user.first_name
    caption = f"- مرحبا بك [{fname}](tg://settings) في بوت النشر التلقائي\n- تحكم في البوت من الأزرار التالية:"
    await message.reply(caption, reply_markup=get_home_markup(user_id))

@app.on_callback_query(filters.regex(r"^(toHome)$"))
async def toHome(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    fname = callback.from_user.first_name
    caption = f"- مرحبا بك [{fname}](tg://settings) في بوت النشر التلقائي"
    await callback.message.edit_text(caption, reply_markup=get_home_markup(user_id))

# =================== إدارة الحساب ===================
@app.on_callback_query(filters.regex(r"^(account)$"))
async def account(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    caption = "🗂️ قسم الحساب\n\nاستخدم الأزرار التالية:"
    markup = Markup([
        [Button("- تسجيل حساب -", callback_data="login"), Button("- تغيير الحساب -", callback_data="changeAccount")],
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
            text="- أرسل رقم هاتفك مع رمز الدولة\n- مثال: +966512345678\n- أو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="account")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء")
    
    await registration(ask)

async def registration(message: Message):
    """تسجيل حساب المستخدم"""
    user_id = message.from_user.id
    phone = message.text.strip()
    
    msg = await message.reply("- جاري تسجيل الدخول...")
    
    client = Client("temp", in_memory=True, api_id=app.api_id, api_hash=app.api_hash)
    await client.connect()
    
    try:
        sent_code = await client.send_code(phone)
    except PhoneNumberInvalid:
        return await msg.edit("- رقم الهاتف غير صحيح")
    
    try:
        code = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- تم إرسال الكود. أرسله الآن:",
            reply_markup=ForceReply(selective=True),
            timeout=120
        )
    except exceptions.TimeOut:
        return await msg.edit("- انتهى وقت الكود")
    
    try:
        await client.sign_in(phone, sent_code.phone_code_hash, code.text)
    except SessionPasswordNeeded:
        try:
            password = await listener.listen(
                from_id=user_id, chat_id=user_id,
                text="- حسابك مفعل بالتحقق بخطوتين\n- أرسل كلمة المرور:",
                reply_markup=ForceReply(selective=True),
                timeout=60
            )
        except exceptions.TimeOut:
            return await msg.edit("- انتهى الوقت")
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
            text="- أرسل رابط أو معرف المجموعة\n- مثال: @username أو t.me/username\n- أو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء")
    
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
            return await ask.reply("- لم يتم العثور على المجموعة")
    
    # معالجة الرابط
    elif "t.me/" in input_text:
        username = input_text.split("t.me/")[-1]
        try:
            chat = await app.get_chat(username)
            group_id = chat.id
            invite_link = input_text
        except:
            return await ask.reply("- رابط غير صالح")
    
    # معالجة الأيدي
    elif input_text.lstrip("-").isdigit():
        group_id = int(input_text)
    
    else:
        return await ask.reply("- صيغة غير صالحة")
    
    if group_id:
        if "groups" not in users[str(user_id)]:
            users[str(user_id)]["groups"] = []
        
        users[str(user_id)]["groups"].append({"id": group_id, "link": invite_link})
        write(users_db, users)
        await ask.reply("✅ تم إضافة المجموعة", reply_markup=Markup([[Button("- الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(currentSupers)$"))
async def currentSupers(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    groups = users[str(user_id)].get("groups", [])
    
    if not groups:
        return await callback.answer("لا توجد مجموعات", show_alert=True)
    
    markup = []
    for g in groups:
        try:
            chat = await app.get_chat(g["id"])
            title = chat.title[:30]
        except:
            title = str(g["id"])
        markup.append([Button(title, callback_data=f"super_{g['id']}"), 
                      Button("🗑️", callback_data=f"delSuper_{g['id']}")])
    
    markup.append([Button("- الرئيسيه -", callback_data="toHome")])
    await callback.message.edit_text("📋 قائمة المجموعات:", reply_markup=Markup(markup))

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
        markup.append([Button(short, callback_data=f"viewCap_{idx}"), 
                      Button("🗑️", callback_data=f"delCap_{idx}")])
    
    markup.append([Button("➕ إضافة كليشة", callback_data="addCaption")])
    markup.append([Button("- الرئيسيه -", callback_data="toHome")])
    
    if not captions:
        await callback.message.edit_text("📝 لا توجد كليشات. أضف كليشة جديدة:", reply_markup=Markup(markup))
    else:
        await callback.message.edit_text(f"📝 الكليشات ({len(captions)}):", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addCaption)$"))
async def addCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- أرسل نص الكليشة الجديدة\n- أو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=120
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="manageCaptions")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء")
    
    captions = users[str(user_id)].get("captions", [])
    captions.append(ask.text)
    users[str(user_id)]["captions"] = captions
    write(users_db, users)
    
    await ask.reply("✅ تم إضافة الكليشة", reply_markup=Markup([[Button("- العوده -", callback_data="manageCaptions")]]))

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
        await callback.message.reply(f"**النص:**\n{captions[idx]}", 
                                    reply_markup=Markup([[Button("- العوده -", callback_data="manageCaptions")]]))

# =================== إعدادات النشر ===================
@app.on_callback_query(filters.regex(r"^(waitTime)$"))
async def waitTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- أرسل المدة بين كل دورة نشر (بالثواني)\n- مثال: 200\n- أو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء")
    
    try:
        wait = int(ask.text)
        if wait < 10:
            return await ask.reply("- المدة يجب أن تكون 10 ثوانٍ على الأقل")
        users[str(user_id)]["waitTime"] = wait
        write(users_db, users)
        await ask.reply(f"✅ تم تعيين المدة: {wait} ثانية", 
                       reply_markup=Markup([[Button("- الرئيسيه -", callback_data="toHome")]]))
    except ValueError:
        await ask.reply("- أرسل رقماً صحيحاً")

@app.on_callback_query(filters.regex(r"^(deleteTime)$"))
async def deleteTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- أرسل مدة بقاء الرسائل (بالثواني)\n- 0 = تعطيل الحذف التلقائي\n- مثال: 1500\n- أو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(selective=True),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("- تم الإلغاء")
    
    try:
        delete_after = int(ask.text)
        users[str(user_id)]["delete_after"] = delete_after
        write(users_db, users)
        status = "معطل" if delete_after == 0 else f"{delete_after} ثانية"
        await ask.reply(f"✅ تم تعيين مدة الحذف: {status}", 
                       reply_markup=Markup([[Button("- الرئيسيه -", callback_data="toHome")]]))
    except ValueError:
        await ask.reply("- أرسل رقماً صحيحاً")

@app.on_callback_query(filters.regex(r"^(distributionMethod)$"))
async def distributionMethod(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text("📊 اختر طريقة توزيع الفروق الزمنية بين المجموعات:", 
                                    reply_markup=get_distribution_markup(user_id))

@app.on_callback_query(filters.regex(r"^setDist_"))
async def setDistribution(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    method = callback.data.split("_")[1]
    
    users[str(user_id)]["distribution_method"] = method
    write(users_db, users)
    
    method_names = {"equal": "المتساوي", "random": "العشوائي", "fibonacci": "المتزايد"}
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

@app.on_callback_query(filters.regex(r"^(startPosting)$"))
async def startPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # التحقق من التسجيل
    if users[str(user_id)].get("session") is None:
        return await callback.answer("❌ يجب تسجيل حساب أولاً", show_alert=True)
    
    # التحقق من وجود مجموعات
    if not users[str(user_id)].get("groups"):
        return await callback.answer("❌ يجب إضافة مجموعات أولاً", show_alert=True)
    
    # التحقق من وجود كليشات
    if not users[str(user_id)].get("captions"):
        return await callback.answer("❌ يجب إضافة كليشات أولاً", show_alert=True)
    
    if users[str(user_id)].get("posting"):
        return await callback.answer("⚠️ النشر مفعل بالفعل", show_alert=True)
    
    users[str(user_id)]["posting"] = True
    write(users_db, users)
    
    task = create_task(posting(user_id))
    active_tasks.add(str(user_id))
    task.add_done_callback(lambda t: active_tasks.discard(str(user_id)))
    
    await callback.message.edit_text("🚀 بدأ النشر التلقائي", 
                                    reply_markup=Markup([[Button("⏹️ إيقاف النشر", callback_data="stopPosting"), 
                                                         Button("🏠 الرئيسيه", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(stopPosting)$"))
async def stopPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not users[str(user_id)].get("posting"):
        return await callback.answer("⚠️ النشر معطل بالفعل", show_alert=True)
    
    users[str(user_id)]["posting"] = False
    write(users_db, users)
    
    await callback.message.edit_text("🛑 تم إيقاف النشر التلقائي", 
                                    reply_markup=Markup([[Button("▶️ بدء النشر", callback_data="startPosting"), 
                                                         Button("🏠 الرئيسيه", callback_data="toHome")]]))

# =================== قسم المالك ===================
async def isOwner(_, __, message: Message) -> bool:
    return message.from_user.id == owner

owner_filter = filters.create(isOwner)

@app.on_message(filters.command("admin") & filters.private & owner_filter)
async def adminPanel(_: Client, message: Message):
    await message.reply("👑 لوحة تحكم المالك", reply_markup=Markup([
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
            text="- أرسل ايدي المستخدم",
            reply_markup=ForceReply(selective=True),
            timeout=30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت")
    
    try:
        user_id = int(ask.text)
    except:
        return await ask.reply("- ايدي غير صالح")
    
    try:
        days = await listener.listen(
            from_id=owner, chat_id=owner,
            text="- أرسل عدد الأيام",
            reply_markup=ForceReply(selective=True),
            timeout=30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت")
    
    try:
        limit_days = int(days.text)
    except:
        return await days.reply("- أرسل رقماً صحيحاً")
    
    if str(user_id) not in users:
        users[str(user_id)] = {"vip": True, "smart_delay": True, "captions": [], "groups": []}
    else:
        users[str(user_id)]["vip"] = True
    
    end_date = datetime.now(_timezone) + timedelta(days=limit_days)
    users[str(user_id)]["limitation"] = {
        "days": limit_days,
        "endDate": end_date.strftime("%Y-%m-%d"),
        "endTime": end_date.strftime("%H:%M")
    }
    write(users_db, users)
    
    await days.reply(f"✅ تم تفعيل VIP للمستخدم {user_id} لمدة {limit_days} يوم",
                    reply_markup=Markup([[Button("- العوده -", callback_data="admin")]]))

@app.on_callback_query(filters.regex("cancelVIP") & owner_filter)
async def cancelVIP(_: Client, callback: CallbackQuery):
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=owner, chat_id=owner,
            text="- أرسل ايدي المستخدم",
            reply_markup=ForceReply(selective=True),
            timeout=30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت")
    
    user_id = ask.text
    if user_id in users:
        users[user_id]["vip"] = False
        write(users_db, users)
        await ask.reply(f"✅ تم الغاء VIP للمستخدم {user_id}",
                       reply_markup=Markup([[Button("- العوده -", callback_data="admin")]]))
    else:
        await ask.reply("- المستخدم غير موجود")

@app.on_callback_query(filters.regex("statics") & owner_filter)
async def statics(_: Client, callback: CallbackQuery):
    total = len(users)
    vip = sum(1 for u in users.values() if u.get("vip", False))
    posting = sum(1 for u in users.values() if u.get("posting", False))
    
    await callback.message.edit_text(
        f"📊 **الإحصائيات**\n\n"
        f"👥 إجمالي المستخدمين: {total}\n"
        f"⭐ مستخدمي VIP: {vip}\n"
        f"🚀 النشر مفعل: {posting}",
        reply_markup=Markup([[Button("- العوده -", callback_data="admin")]])
    )

@app.on_callback_query(filters.regex("channels") & owner_filter)
async def channelsControl(_: Client, callback: CallbackQuery):
    markup = []
    for ch in channels:
        markup.append([Button(f"@{ch}", url=f"https://t.me/{ch}"), 
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
            text="- أرسل معرف القناة (بدون @)\n- مثال: channelusername",
            reply_markup=ForceReply(selective=True),
            timeout=30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى الوقت")
    
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
    create_task(restartPosting())
    create_task(checkVIPExpiry())
    await app.start()
    print("✅ البوت يعمل بنجاح!")
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(main())
