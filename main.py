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
    api_id="34923166",
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
    delete_text = f"🗑 حذف بعد {delete_after} ث" if delete_after > 0 else "🗑 حذف معطل"
    smart_delay_text = "✅ توزيع ذكي" if user_data.get("smart_delay", True) else "❌ توزيع عادي"
    
    accounts_count = len(user_data.get("accounts", []))
    groups_count = len(user_data.get("groups", []))
    captions_count = len(user_data.get("captions", []))
    
    return Markup([
        [Button(f"👤 حسابي ({accounts_count})", callback_data="account")],
        [Button(f"📁 الجروبات ({groups_count})", callback_data="currentSupers"), Button(f"➕ إضافة جروب", callback_data="newSuper")],
        [Button(f"📝 الكليشات ({captions_count})", callback_data="manageCaptions")],
        [Button(smart_delay_text, callback_data="toggleSmartDelay")],
        [Button(f"⏱ المدة الإجمالية: {user_data.get('cycle_time', 60)}ث", callback_data="setCycleTime")],
        [Button(delete_text, callback_data="setDeleteAfter")],
        [Button("▶️ بدء النشر", callback_data="startPosting"), Button("⏹ إيقاف", callback_data="stopPosting")],
        [Button("📊 الحالة", callback_data="status")]
    ])

def get_accounts_markup(user_id):
    accounts = users.get(str(user_id), {}).get("accounts", [])
    markup = []
    for idx, acc in enumerate(accounts):
        phone = acc.get("phone", "رقم غير معروف")
        is_active = "✅" if users[str(user_id)].get("active_account") == idx else "⚪"
        markup.append([Button(f"{is_active} {phone}", callback_data=f"selectAcc_{idx}"), Button("🗑", callback_data=f"delAcc_{idx}")])
    markup.append([Button("➕ إضافة حساب", callback_data="addAccount")])
    markup.append([Button("🔙 رجوع", callback_data="toHome")])
    return Markup(markup)

def get_groups_markup(user_id):
    groups = users.get(str(user_id), {}).get("groups", [])
    markup = []
    for idx, g in enumerate(groups):
        gid = g["id"]
        try:
            chat = app.get_chat(gid)
            name = chat.title if hasattr(chat, 'title') else str(gid)
        except:
            name = str(gid)
        name = name[:25] + ".." if len(name) > 25 else name
        markup.append([Button(f"📌 {name}", callback_data=f"ignore"), Button("🗑", callback_data=f"delGroup_{idx}")])
    if not markup:
        markup.append([Button("❌ لا توجد جروبات", callback_data="ignore")])
    markup.append([Button("🔙 رجوع", callback_data="toHome")])
    return Markup(markup)

def get_captions_markup(user_id):
    captions = users.get(str(user_id), {}).get("captions", [])
    markup = []
    for idx, cap in enumerate(captions):
        short = cap[:20] + ".." if len(cap) > 20 else cap
        markup.append([Button(f"📄 {short}", callback_data=f"viewCap_{idx}"), Button("🗑", callback_data=f"delCap_{idx}")])
    if not markup:
        markup.append([Button("❌ لا توجد كليشات", callback_data="ignore")])
    markup.append([Button("➕ إضافة كليشه", callback_data="addCaption")])
    markup.append([Button("🔙 رجوع", callback_data="toHome")])
    return Markup(markup)

async def delete_message_after_delay(client, chat_id, message_id, delay_seconds):
    await sleep(delay_seconds)
    try:
        await client.delete_messages(chat_id, message_id)
    except:
        pass

def calculate_delays(num_groups: int, cycle_time: int) -> list:
    """
    حساب الفواصل الزمنية بين الجروبات
    المبدأ: المدة الإجمالية / عدد الجروبات = متوسط الفاصل
    مع إضافة عشوائية لتجنب النمطية
    """
    if num_groups <= 1:
        return []
    
    # متوسط الفاصل بين كل جروب وآخر
    avg_interval = cycle_time / num_groups
    
    delays = []
    remaining_time = cycle_time
    
    for i in range(num_groups - 1):
        # عشوائية بين -30% و +30% من متوسط الفاصل
        variation = random.uniform(-0.3, 0.3) * avg_interval
        delay = max(2, avg_interval + variation)  # لا تقل عن 2 ثانية
        
        if i == num_groups - 2:
            # آخر فاصل - نضبطه ليتناسب مع الوقت المتبقي
            delay = max(2, remaining_time)
        else:
            remaining_time -= delay
        
        delays.append(delay)
    
    return delays

# =================== أوامر المستخدم ===================
@app.on_message(filters.command("start") & filters.private)
async def start(_: Client, message: Message):
    user_id = message.from_user.id
    
    # التحقق من الاشتراك
    for channel in channels:
        try:
            await app.get_chat_member(channel, user_id)
        except UserNotParticipant:
            return await message.reply(f"⚠️ اشترك أولاً في قناة @{channel}\nثم أعد إرسال /start")
    
    # إنشاء حساب جديد للمستخدم
    if str(user_id) not in users:
        users[str(user_id)] = {
            "vip": (user_id == owner),
            "accounts": [],
            "active_account": None,
            "groups": [],
            "captions": [],
            "cycle_time": 60,  # المدة الإجمالية للدورة بالثواني
            "smart_delay": True,  # تفعيل التوزيع الذكي
            "delete_after": 0,
            "posting": False
        }
        write(users_db, users)
    
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await message.reply("❌ هذا البوت خاص بالمطور فقط.\nتواصل مع @A_A_H_H")
    
    await message.reply(
        f"✨ **مرحباً {message.from_user.first_name}** ✨\n\n"
        f"📌 **كيف يعمل التوزيع الذكي؟**\n"
        f"🔹 إذا حددت مدة إجمالية 200 ثانية\n"
        f"🔹 ولديك 10 جروبات\n"
        f"🔹 فسيتم التوزيع كالتالي:\n"
        f"   • 200 ÷ 10 = 20 ثانية متوسط بين كل جروب\n"
        f"   • مع إضافة عشوائية ±30% لتجنب النمطية\n"
        f"   • ترتيب الجروبات عشوائي\n"
        f"   • كليشات عشوائية لكل إرسال\n\n"
        f"📖 **الخطوات:**\n"
        f"1️⃣ أضف حساباً عبر 'حسابي'\n"
        f"2️⃣ أضف الجروبات عبر 'إضافة جروب'\n"
        f"3️⃣ أضف كليشات عبر 'الكليشات'\n"
        f"4️⃣ اضبط المدة الإجمالية\n"
        f"5️⃣ اضغط 'بدء النشر'",
        reply_markup=get_home_markup(user_id)
    )

@app.on_callback_query(filters.regex(r"^(toHome)$"))
async def toHome(_: Client, callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 **القائمة الرئيسية**\n\n"
        "📌 التوزيع الذكي: المدة الإجمالية تقسم على عدد الجروبات",
        reply_markup=get_home_markup(callback.from_user.id)
    )

@app.on_callback_query(filters.regex(r"^(toggleSmartDelay)$"))
async def toggleSmartDelay(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    current = users[str(user_id)].get("smart_delay", True)
    users[str(user_id)]["smart_delay"] = not current
    write(users_db, users)
    
    status = "مفعل ✅" if not current else "معطل ❌"
    await callback.answer(f"تم {status} التوزيع الذكي", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=get_home_markup(user_id))

@app.on_callback_query(filters.regex(r"^(setCycleTime)$"))
async def setCycleTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="⏱ **تعيين المدة الإجمالية للدورة**\n\n"
                 "🔹 **كيف يعمل؟**\n"
                 "المدة الإجمالية ÷ عدد الجروبات = الفاصل بين كل جروب\n\n"
                 "مثال: 200 ثانية ÷ 10 جروبات = 20 ثانية بين كل إرسال\n\n"
                 "📝 **أرسل المدة بالثواني:**\n"
                 "(الحد الأدنى: 30 ثانية)\n\n"
                 "أو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("❌ تم الإلغاء", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    
    try:
        cycle_time = int(ask.text)
        if cycle_time < 30:
            return await ask.reply("⚠️ المدة يجب أن تكون 30 ثانية على الأقل", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
        
        users[str(user_id)]["cycle_time"] = cycle_time
        write(users_db, users)
        
        # شرح للمستخدم كيف سيتم التوزيع
        groups_count = len(users[str(user_id)].get("groups", []))
        if groups_count > 0:
            avg_delay = cycle_time / groups_count
            await ask.reply(
                f"✅ **تم تعيين المدة الإجمالية إلى {cycle_time} ثانية**\n\n"
                f"📊 **حسب الوضع الحالي:**\n"
                f"• عدد الجروبات: {groups_count}\n"
                f"• متوسط الفاصل بين الجروبات: {avg_delay:.1f} ثانية\n"
                f"• مع عشوائية ±30% لتجنب النمطية\n"
                f"• ترتيب الجروبات عشوائي\n"
                f"• كليشات عشوائية لكل إرسال",
                reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]])
            )
        else:
            await ask.reply(f"✅ **تم تعيين المدة الإجمالية إلى {cycle_time} ثانية**\n\n⚠️ أضف جروبات أولاً لتفعيل التوزيع الذكي",
                          reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    except:
        await ask.reply("❌ رقم غير صالح", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(status)$"))
async def show_status(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = users.get(str(user_id), {})
    groups_count = len(data.get('groups', []))
    cycle_time = data.get('cycle_time', 60)
    avg_delay = cycle_time / groups_count if groups_count > 0 else 0
    
    status_text = f"📊 **حالة البوت**\n\n"
    status_text += f"👤 **الحسابات:** {len(data.get('accounts', []))}\n"
    if data.get('active_account') is not None:
        accounts = data.get('accounts', [])
        if data['active_account'] < len(accounts):
            status_text += f"   ✅ النشط: {accounts[data['active_account']].get('phone', 'غير معروف')}\n"
    status_text += f"📁 **الجروبات:** {groups_count}\n"
    status_text += f"📝 **الكليشات:** {len(data.get('captions', []))}\n\n"
    status_text += f"⏱ **المدة الإجمالية:** {cycle_time} ثانية\n"
    status_text += f"📊 **متوسط الفاصل:** {avg_delay:.1f} ثانية\n"
    status_text += f"🔄 **توزيع ذكي:** {'✅ مفعل' if data.get('smart_delay', True) else '❌ معطل'}\n"
    status_text += f"🗑 **حذف تلقائي:** {data.get('delete_after', 0)} ثانية\n"
    status_text += f"▶️ **حالة النشر:** {'🟢 يعمل' if data.get('posting') else '🔴 متوقف'}\n\n"
    status_text += f"📌 **آلية التوزيع:**\n"
    status_text += f"• المدة الإجمالية ÷ عدد الجروبات = الفاصل\n"
    status_text += f"• ترتيب عشوائي للجروبات\n"
    status_text += f"• كليشات عشوائية لكل إرسال\n"
    status_text += f"• عشوائية ±30% على الفواصل"
    
    await callback.message.edit_text(status_text, reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))

# =================== إدارة الحسابات ===================
@app.on_callback_query(filters.regex(r"^(account)$"))
async def account(_: Client, callback: CallbackQuery):
    await callback.message.edit_text(
        "👤 **إدارة الحسابات**\n\n"
        "📌 يمكنك إضافة عدة حسابات واختيار أي منها للنشر",
        reply_markup=get_accounts_markup(callback.from_user.id)
    )

@app.on_callback_query(filters.regex(r"^(addAccount)$"))
async def addAccount(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="📱 **أرسل رقم هاتفك**\nمثال: +9647700000000\n\nأو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("❌ تم الإلغاء", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
    
    phone = ask.text.strip()
    await add_account_step2(ask, user_id, phone)

async def add_account_step2(msg: Message, user_id: int, phone: str):
    temp_client = Client("temp", in_memory=True, api_id=app.api_id, api_hash=app.api_hash)
    await temp_client.connect()
    
    try:
        sent_code = await temp_client.send_code(phone)
    except PhoneNumberInvalid:
        await msg.reply("❌ رقم الهاتف غير صحيح", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
        await temp_client.disconnect()
        return
    
    try:
        code = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="📨 **أرسل الكود المرسل إليك**\n\nأو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(),
            timeout=120
        )
    except exceptions.TimeOut:
        await msg.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
        await temp_client.disconnect()
        return
    
    if code.text == "/cancel":
        await code.reply("❌ تم الإلغاء", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
        await temp_client.disconnect()
        return
    
    try:
        await temp_client.sign_in(phone, sent_code.phone_code_hash, code.text)
    except PhoneCodeInvalid:
        await code.reply("❌ الكود غير صحيح", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
        await temp_client.disconnect()
        return
    except PhoneCodeExpired:
        await code.reply("❌ الكود منتهي الصلاحية", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
        await temp_client.disconnect()
        return
    except SessionPasswordNeeded:
        try:
            password = await listener.listen(
                from_id=user_id, chat_id=user_id,
                text="🔐 **أدخل كلمة مرور التحقق بخطوتين**\n\nأو ارسل /cancel للإلغاء",
                reply_markup=ForceReply(),
                timeout=60
            )
        except exceptions.TimeOut:
            await msg.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
            await temp_client.disconnect()
            return
        
        if password.text == "/cancel":
            await password.reply("❌ تم الإلغاء", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
            await temp_client.disconnect()
            return
        
        try:
            await temp_client.check_password(password.text)
        except PasswordHashInvalid:
            await password.reply("❌ كلمة المرور غير صحيحة", reply_markup=Markup([[Button("🔙 رجوع", callback_data="account")]]))
            await temp_client.disconnect()
            return
    
    session_string = await temp_client.export_session_string()
    await temp_client.disconnect()
    
    # حفظ الحساب
    accounts = users[str(user_id)].get("accounts", [])
    accounts.append({
        "phone": phone,
        "session": session_string
    })
    users[str(user_id)]["accounts"] = accounts
    
    # إذا كان أول حساب، اجعله نشطاً
    if users[str(user_id)].get("active_account") is None:
        users[str(user_id)]["active_account"] = len(accounts) - 1
    
    write(users_db, users)
    
    await app.send_message(user_id, f"✅ **تم إضافة الحساب بنجاح!**\n📱 {phone}\n\n" + 
                          ("🔵 هذا الحساب هو النشط حالياً" if users[str(user_id)]["active_account"] == len(accounts)-1 else ""),
                          reply_markup=Markup([[Button("🔙 رجوع للحسابات", callback_data="account")]]))

@app.on_callback_query(filters.regex(r"^(selectAcc_)(\d+)$"))
async def selectAccount(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    accounts = users[str(user_id)].get("accounts", [])
    
    if idx < len(accounts):
        users[str(user_id)]["active_account"] = idx
        write(users_db, users)
        await callback.answer(f"✅ تم اختيار الحساب {accounts[idx]['phone']}", show_alert=True)
    
    await account(_, callback)

@app.on_callback_query(filters.regex(r"^(delAcc_)(\d+)$"))
async def deleteAccount(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    accounts = users[str(user_id)].get("accounts", [])
    
    if idx < len(accounts):
        removed = accounts.pop(idx)
        users[str(user_id)]["accounts"] = accounts
        
        active = users[str(user_id)].get("active_account")
        if active == idx:
            users[str(user_id)]["active_account"] = None if len(accounts) == 0 else 0
        elif active is not None and active > idx:
            users[str(user_id)]["active_account"] = active - 1
        
        write(users_db, users)
        await callback.answer(f"✅ تم حذف الحساب {removed['phone']}", show_alert=True)
    
    await account(_, callback)

# =================== إدارة الجروبات ===================
@app.on_callback_query(filters.regex(r"^(newSuper)$"))
async def newSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="📌 **أضف مجموعة جديدة**\n\n"
                 "أرسل معرف المجموعة (يبدأ بـ -100)\n"
                 "أو رابط الدعوة\n\n"
                 "مثال: -1001234567890\n"
                 "أو: https://t.me/joinchat/xxxx\n\n"
                 "أو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("❌ تم الإلغاء", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    
    group_id = None
    invite_link = None
    input_text = ask.text.strip()
    
    if input_text.startswith("-") and input_text.lstrip("-").isdigit():
        group_id = int(input_text)
    elif "t.me/" in input_text:
        invite_link = input_text
        try:
            parts = input_text.split("/")
            username = parts[-1]
            chat = await app.get_chat(username)
            group_id = chat.id
        except Exception as e:
            return await ask.reply(f"❌ الرابط غير صالح: {str(e)[:50]}", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    else:
        return await ask.reply("❌ المعرف أو الرابط غير صالح", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    
    groups = users[str(user_id)].get("groups", [])
    
    for g in groups:
        if g["id"] == group_id:
            return await ask.reply("⚠️ هذه المجموعة مضافة بالفعل", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    
    groups.append({
        "id": group_id,
        "link": invite_link
    })
    users[str(user_id)]["groups"] = groups
    write(users_db, users)
    
    await ask.reply(f"✅ **تم إضافة المجموعة بنجاح!**\n🆔 المعرف: {group_id}", 
                    reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(currentSupers)$"))
async def currentSupers(_: Client, callback: CallbackQuery):
    await callback.message.edit_text(
        "📁 **الجروبات المضافة**\n\n"
        "اضغط على 🗑 لحذف أي مجموعة",
        reply_markup=get_groups_markup(callback.from_user.id)
    )

@app.on_callback_query(filters.regex(r"^(delGroup_)(\d+)$"))
async def delGroup(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    groups = users[str(user_id)].get("groups", [])
    
    if idx < len(groups):
        removed = groups.pop(idx)
        users[str(user_id)]["groups"] = groups
        write(users_db, users)
        await callback.answer(f"✅ تم حذف المجموعة {removed['id']}", show_alert=True)
    
    await currentSupers(_, callback)

# =================== إدارة الكليشات ===================
@app.on_callback_query(filters.regex(r"^(manageCaptions)$"))
async def manageCaptions(_: Client, callback: CallbackQuery):
    await callback.message.edit_text(
        "📝 **الكليشات المحفوظة**\n\n"
        "اضغط على 🗑 لحذف أي كليشة\n"
        "اضغط على أي كليشة لعرضها كاملة",
        reply_markup=get_captions_markup(callback.from_user.id)
    )

@app.on_callback_query(filters.regex(r"^(addCaption)$"))
async def addCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="📝 **أضف كليشة جديدة**\n\n"
                 "أرسل النص الذي تريد نشره\n"
                 "يمكنك استخدام HTML و Emoji\n\n"
                 "أو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(),
            timeout=120
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("🔙 رجوع", callback_data="manageCaptions")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("❌ تم الإلغاء", reply_markup=Markup([[Button("🔙 رجوع", callback_data="manageCaptions")]]))
    
    captions = users[str(user_id)].get("captions", [])
    captions.append(ask.text)
    users[str(user_id)]["captions"] = captions
    write(users_db, users)
    
    await ask.reply(f"✅ **تم إضافة الكليشة #{len(captions)}**\n\n📄 {ask.text[:100]}{'...' if len(ask.text) > 100 else ''}",
                    reply_markup=Markup([[Button("🔙 رجوع", callback_data="manageCaptions")]]))

@app.on_callback_query(filters.regex(r"^(viewCap_)(\d+)$"))
async def viewCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    captions = users[str(user_id)].get("captions", [])
    
    if idx < len(captions):
        await callback.answer("📄 معاينة الكليشة", show_alert=True)
        await callback.message.reply(
            f"📄 **الكليشة #{idx+1}**\n\n{captions[idx]}\n\n"
            f"📏 طول النص: {len(captions[idx])} حرف",
            reply_markup=Markup([[Button("🔙 رجوع", callback_data="manageCaptions")]])
        )

@app.on_callback_query(filters.regex(r"^(delCap_)(\d+)$"))
async def delCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    captions = users[str(user_id)].get("captions", [])
    
    if idx < len(captions):
        removed = captions.pop(idx)
        users[str(user_id)]["captions"] = captions
        write(users_db, users)
        await callback.answer(f"✅ تم حذف الكليشة: {removed[:30]}", show_alert=True)
    
    await manageCaptions(_, callback)

# =================== إعدادات أخرى ===================
@app.on_callback_query(filters.regex(r"^(setDeleteAfter)$"))
async def setDeleteAfter(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="🗑 **تعيين مدة حذف الرسائل**\n\n"
                 "أرسل المدة بالثواني\n"
                 "مثال: 1800 (نصف ساعة)\n"
                 "0 لتعطيل الحذف التلقائي\n\n"
                 "أو ارسل /cancel للإلغاء",
            reply_markup=ForceReply(),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("⏰ انتهى الوقت", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    
    if ask.text == "/cancel":
        return await ask.reply("❌ تم الإلغاء", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    
    try:
        seconds = int(ask.text)
        if seconds < 0:
            raise ValueError
        users[str(user_id)]["delete_after"] = seconds
        write(users_db, users)
        if seconds == 0:
            await ask.reply(f"✅ **تم تعطيل الحذف التلقائي**", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
        else:
            await ask.reply(f"✅ **سيتم حذف الرسائل بعد {seconds} ثانية**", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))
    except:
        await ask.reply("❌ رقم غير صالح", reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]]))

# =================== بدء وإيقاف النشر ===================
active_tasks = set()

@app.on_callback_query(filters.regex(r"^(startPosting)$"))
async def startPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = users.get(str(user_id), {})
    
    # التحقق من وجود حساب نشط
    active_idx = user_data.get("active_account")
    if active_idx is None or len(user_data.get("accounts", [])) == 0:
        return await callback.answer("❌ لا يوجد حساب! أضف حساباً أولاً", show_alert=True)
    
    groups = user_data.get("groups", [])
    if not groups:
        return await callback.answer("❌ لا توجد جروبات! أضف جروباً أولاً", show_alert=True)
    
    captions = user_data.get("captions", [])
    if not captions:
        return await callback.answer("❌ لا توجد كليشات! أضف كليشة أولاً", show_alert=True)
    
    if user_data.get("posting"):
        return await callback.answer("⚠️ النشر مفعل بالفعل", show_alert=True)
    
    if str(user_id) in active_tasks:
        return await callback.answer("⚠️ يتم التشغيل حالياً", show_alert=True)
    
    # حساب الإحصائيات
    cycle_time = user_data.get("cycle_time", 60)
    groups_count = len(groups)
    avg_delay = cycle_time / groups_count
    smart_delay = user_data.get("smart_delay", True)
    
    summary = f"🚀 **بدء النشر التلقائي**\n\n"
    summary += f"👤 **الحساب النشط:** {user_data['accounts'][active_idx]['phone']}\n"
    summary += f"📁 **عدد الجروبات:** {groups_count}\n"
    summary += f"📝 **عدد الكليشات:** {len(captions)}\n\n"
    summary += f"⏱ **المدة الإجمالية للدورة:** {cycle_time} ثانية\n"
    
    if smart_delay and groups_count > 1:
        summary += f"📊 **آلية التوزيع الذكي:**\n"
        summary += f"   • متوسط الفاصل: {avg_delay:.1f} ثانية\n"
        summary += f"   • ترتيب الجروبات: عشوائي\n"
        summary += f"   • كليشات: عشوائية لكل إرسال\n"
        summary += f"   • عشوائية ±30% على الفواصل\n"
    else:
        summary += f"📊 **آلية التوزيع العادي:**\n"
        summary += f"   • انتظار {cycle_time} ثانية بين كل رسالة\n"
    
    summary += f"\n🗑 **حذف تلقائي:** {user_data.get('delete_after', 0)} ثانية\n\n"
    summary += f"✅ جارٍ البدء..."
    
    await callback.message.edit_text(summary)
    
    users[str(user_id)]["posting"] = True
    write(users_db, users)
    
    task = create_task(posting(user_id))
    active_tasks.add(str(user_id))
    task.add_done_callback(lambda t: active_tasks.discard(str(user_id)))

@app.on_callback_query(filters.regex(r"^(stopPosting)$"))
async def stopPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if not users.get(str(user_id), {}).get("posting"):
        return await callback.answer("⚠️ النشر متوقف بالفعل", show_alert=True)
    
    users[str(user_id)]["posting"] = False
    write(users_db, users)
    
    await callback.message.edit_text(
        "⏹ **تم إيقاف النشر التلقائي**\n\n"
        "يمكنك استئنافه لاحقاً من القائمة الرئيسية",
        reply_markup=Markup([[Button("🔙 رجوع", callback_data="toHome")]])
    )

# =================== دالة النشر الرئيسية (مع التوزيع الذكي) ===================
async def send_to_group(client, group_id, caption, delete_after):
    """إرسال رسالة إلى مجموعة واحدة"""
    try:
        msg = await client.send_message(group_id, caption)
        if delete_after > 0:
            create_task(delete_message_after_delay(client, group_id, msg.id, delete_after))
        return True, None
    except FloodWait as e:
        return False, f"FloodWait: انتظر {e.value} ثانية"
    except (PeerIdInvalid, UserNotParticipant, ChatWriteForbidden) as e:
        return False, f"خطأ في الوصول: {type(e).__name__}"
    except Exception as e:
        return False, str(e)[:100]

async def posting(user_id):
    user_id_str = str(user_id)
    user_data = users.get(user_id_str, {})
    
    if not user_data.get("posting"):
        return
    
    # الحصول على الحساب النشط
    active_idx = user_data.get("active_account")
    accounts = user_data.get("accounts", [])
    if active_idx is None or active_idx >= len(accounts):
        await app.send_message(user_id, "❌ لا يوجد حساب نشط! الرجاء اختيار حساب")
        user_data["posting"] = False
        write(users_db, users)
        return
    
    active_account = accounts[active_idx]
    session_string = active_account.get("session")
    
    if not session_string:
        await app.send_message(user_id, "❌ جلسة الحساب غير صالحة! الرجاء إعادة تسجيل الدخول")
        user_data["posting"] = False
        write(users_db, users)
        return
    
    client = Client(f"user_{user_id}", api_id=app.api_id, api_hash=app.api_hash, session_string=session_string)
    
    try:
        await client.start()
        await app.send_message(user_id, f"✅ تم تسجيل الدخول إلى {active_account.get('phone', 'الحساب')}")
    except Exception as e:
        await app.send_message(user_id, f"❌ فشل تسجيل الدخول: {str(e)[:100]}")
        user_data["posting"] = False
        write(users_db, users)
        return
    
    try:
        while user_data.get("posting"):
            cycle_time = user_data.get("cycle_time", 60)
            groups = user_data.get("groups", []).copy()
            captions = user_data.get("captions", [])
            delete_after = user_data.get("delete_after", 0)
            smart_delay = user_data.get("smart_delay", True)
            
            if not groups or not captions:
                user_data["posting"] = False
                write(users_db, users)
                await app.send_message(user_id, "⚠️ توقف النشر: لا توجد جروبات أو كليشات")
                break
            
            # خلط ترتيب الجروبات عشوائياً
            shuffled_groups = groups.copy()
            random.shuffle(shuffled_groups)
            
            num_groups = len(shuffled_groups)
            
            # حساب الفواصل الزمنية (فقط إذا كان التوزيع الذكي مفعلاً)
            if smart_delay and num_groups > 1:
                delays = calculate_delays(num_groups, cycle_time)
            else:
                # الوضع العادي: نفس المدة بين كل رسالة
                delays = [cycle_time] * (num_groups - 1)
            
            success_count = 0
            fail_count = 0
            
            # إرسال الرسائل مع الفواصل المحسوبة
            for idx, group in enumerate(shuffled_groups):
                if not user_data.get("posting"):
                    break
                
                group_id = group["id"]
                # اختيار كليشة عشوائية
                caption = random.choice(captions)
                
                # محاكاة الكتابة البشرية (تأخير قصير عشوائي)
                await sleep(random.uniform(0.5, 2.0))
                
                success, error = await send_to_group(client, group_id, caption, delete_after)
                
                if success:
                    success_count += 1
                    # إرسال تقرير كل 5 رسائل ناجحة
                    if success_count % 5 == 0:
                        await app.send_message(user_id, f"✅ تم إرسال {success_count} رسالة بنجاح")
                else:
                    fail_count += 1
                    if "FloodWait" not in error:
                        await app.send_message(user_id, f"❌ فشل الإرسال إلى {group_id}: {error}")
                
                # انتظار الفاصل الزمني قبل الإرسال التالي (ما عدا آخر رسالة)
                if idx < len(delays) and user_data.get("posting"):
                    delay = delays[idx]
                    # إضافة عشوائية إضافية صغيرة
                    extra_jitter = random.uniform(0, 2)
                    await sleep(delay + extra_jitter)
            
            # إرسال تقرير الدورة الكامل
            total_sent = success_count + fail_count
            await app.send_message(
                user_id, 
                f"📊 **تقرير الدورة:**\n"
                f"• الوقت الإجمالي: {cycle_time} ثانية\n"
                f"• عدد الجروبات: {num_groups}\n"
                f"• ✅ نجح: {success_count}\n"
                f"• ❌ فشل: {fail_count}\n"
                f"• 📈 نسبة النجاح: {success_count * 100 // total_sent if total_sent > 0 else 0}%"
            )
            
            # انتظار قصير بين الدورات (اختياري، لمنع النمطية)
            if user_data.get("posting"):
                await sleep(random.uniform(3, 8))
            
    except Exception as e:
        await app.send_message(user_id, f"⚠️ خطأ في البوت: {str(e)[:200]}")
    
    finally:
        await client.stop()
        if user_data.get("posting"):
            user_data["posting"] = False
            write(users_db, users)
            await app.send_message(user_id, "⚠️ توقف النشر بسبب خطأ غير متوقع")

# =================== قسم المالك ===================
@app.on_message(filters.command("admin") & filters.user(owner))
async def admin_panel(_, message: Message):
    markup = Markup([
        [Button("📊 إحصائيات", callback_data="admin_stats"), Button("📢 قنوات الاشتراك", callback_data="admin_channels")],
        [Button("👑 تفعيل VIP", callback_data="admin_addvip"), Button("👑 إلغاء VIP", callback_data="admin_removevip")],
        [Button("📋 عرض المستخدمين", callback_data="admin_users")]
    ])
    await message.reply("👑 **لوحة تحكم المالك**", reply_markup=markup)

@app.on_callback_query(filters.user(owner))
async def admin_callbacks(_, callback: CallbackQuery):
    data = callback.data
    
    if data == "admin_stats":
        total = len(users)
        vip = sum(1 for u in users.values() if u.get("vip", False))
        posting = sum(1 for u in users.values() if u.get("posting", False))
        total_accounts = sum(len(u.get("accounts", [])) for u in users.values())
        total_groups = sum(len(u.get("groups", [])) for u in users.values())
        
        await callback.message.edit_text(
            f"📊 **إحصائيات البوت**\n\n"
            f"👥 المستخدمين: {total}\n"
            f"⭐ VIP: {vip}\n"
            f"🔄 يعملون: {posting}\n\n"
            f"👤 إجمالي الحسابات: {total_accounts}\n"
            f"📁 إجمالي الجروبات: {total_groups}",
            reply_markup=Markup([[Button("🔙 رجوع", callback_data="admin_back")]])
        )
    
    elif data == "admin_users":
        user_list = ""
        for uid, u in users.items():
            vip = "⭐" if u.get("vip") else "○"
            posting = "🟢" if u.get("posting") else "⚪"
            accounts = len(u.get("accounts", []))
            user_list += f"{vip}{posting} `{uid}` (حسابات: {accounts})\n"
        
        if len(user_list) > 4000:
            user_list = user_list[:4000] + "\n..."
        
        await callback.message.edit_text(
            f"📋 **قائمة المستخدمين**\n\n{user_list}",
            reply_markup=Markup([[Button("🔙 رجوع", callback_data="admin_back")]])
        )
    
    elif data == "admin_channels":
        markup = []
        for ch in channels:
            markup.append([Button(f"@{ch}", url=f"https://t.me/{ch}"), Button("🗑", callback_data=f"admin_delch_{ch}")])
        markup.append([Button("➕ إضافة قناة", callback_data="admin_addch")])
        markup.append([Button("🔙 رجوع", callback_data="admin_back")])
        await callback.message.edit_text("📢 **قنوات الاشتراك الإجباري**", reply_markup=Markup(markup))
    
    elif data == "admin_addch":
        await callback.message.delete()
        try:
            ask = await listener.listen(
                from_id=owner, chat_id=owner,
                text="أرسل معرف القناة بدون @\nمثال: channel_username",
                reply_markup=ForceReply(),
                timeout=30
            )
        except:
            return await callback.message.reply("انتهى الوقت")
        
        channels.append(ask.text)
        write(channels_db, channels)
        await ask.reply("✅ تم إضافة القناة", reply_markup=Markup([[Button("🔙 رجوع", callback_data="admin_back")]]))
    
    elif data.startswith("admin_delch_"):
        ch = data.replace("admin_delch_", "")
        if ch in channels:
            channels.remove(ch)
            write(channels_db, channels)
        await callback.answer("✅ تم الحذف")
        await admin_callbacks(_, callback)
    
    elif data == "admin_addvip":
        await callback.message.delete()
        try:
            ask = await listener.listen(
                from_id=owner, chat_id=owner,
                text="أرسل معرف المستخدم",
                reply_markup=ForceReply(),
                timeout=30
            )
        except:
            return await callback.message.reply("انتهى الوقت")
        
        target = ask.text
        try:
            days = await listener.listen(
                from_id=owner, chat_id=owner,
                text="أرسل عدد الأيام",
                reply_markup=ForceReply(),
                timeout=30
            )
            days_int = int(days.text)
        except:
            return await callback.message.reply("رقم غير صالح")
        
        if target not in users:
            users[target] = {"vip": True, "accounts": [], "groups": [], "captions": [], "cycle_time": 60, "smart_delay": True, "delete_after": 0, "posting": False}
        else:
            users[target]["vip"] = True
        
        write(users_db, users)
        await ask.reply(f"✅ تم تفعيل VIP للمستخدم {target} لمدة {days_int} يوم")
        try:
            await app.send_message(int(target), f"🎉 تم تفعيل VIP لك لمدة {days_int} يوم!")
        except:
            pass
    
    elif data == "admin_removevip":
        await callback.message.delete()
        try:
            ask = await listener.listen(
                from_id=owner, chat_id=owner,
                text="أرسل معرف المستخدم",
                reply_markup=ForceReply(),
                timeout=30
            )
        except:
            return await callback.message.reply("انتهى الوقت")
        
        target = ask.text
        if target in users:
            users[target]["vip"] = False
            write(users_db, users)
            await ask.reply(f"✅ تم إلغاء VIP للمستخدم {target}")
        else:
            await ask.reply("❌ المستخدم غير موجود")
    
    elif data == "admin_back":
        await admin_panel(_, callback.message)

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
    for uid, data in users.items():
        if data.get("posting") and str(uid) not in active_tasks:
            task = create_task(posting(int(uid)))
            active_tasks.add(str(uid))
            task.add_done_callback(lambda t, u=str(uid): active_tasks.discard(u))

@app.on_callback_query(filters.regex(r"^ignore$"))
async def ignore_callback(_, callback: CallbackQuery):
    await callback.answer()

async def main():
    create_task(reStartPosting())
    await app.start()
    print("✅ البوت يعمل بنجاح!")
    print(f"📊 عدد المستخدمين: {len(users)}")
    print(f"📢 قنوات الاشتراك: {channels}")
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(main())
