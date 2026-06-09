"""
بوت النشر التلقائي للمجموعات
جميع الحقوق محفوظة للمطور
"""

from pyrogram import Client, filters, idle
from pyrogram.types import Message, CallbackQuery, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, PeerIdInvalid, ChatWriteForbidden, UserNotParticipant
import asyncio
import json
import os
import random
from datetime import datetime
import re

# =================== إعدادات البوت ===================
API_ID = 34923196
API_HASH = "b3f6e47ecd3231186f8f7e01ab41938e"
BOT_TOKEN = "8860124031:AAE2LpN2aoz9wTDtKEx_B9KtBgrSHWtfTrY"
OWNER_ID = 8310839908

app = Client("auto_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# =================== إدارة الملفات ===================
USERS_FILE = "users.json"
CHANNELS_FILE = "channels.json"

def load_data(file):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump({} if file == USERS_FILE else [], f, ensure_ascii=False, indent=2)
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = load_data(USERS_FILE)
channels = load_data(CHANNELS_FILE)

# =================== دوال مساعدة ===================
def get_main_menu(user_id):
    user_data = users.get(str(user_id), {})
    groups_count = len(user_data.get("groups", []))
    captions_count = len(user_data.get("captions", []))
    is_active = user_data.get("active", False)
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📁 جروباتي ({groups_count})", callback_data="show_groups"),
         InlineKeyboardButton("➕ إضافة جروب", callback_data="add_group")],
        [InlineKeyboardButton(f"📝 كليشاتي ({captions_count})", callback_data="show_captions"),
         InlineKeyboardButton("➕ إضافة كليشة", callback_data="add_caption")],
        [InlineKeyboardButton("⏱ تعيين المدة", callback_data="set_interval"),
         InlineKeyboardButton("🗑 حذف تلقائي", callback_data="set_auto_delete")],
        [InlineKeyboardButton("🔄 ترتيب عشوائي", callback_data="toggle_random")],
        [InlineKeyboardButton("▶️ بدء النشر" if not is_active else "⏹ إيقاف النشر", callback_data="toggle_posting")],
        [InlineKeyboardButton("📊 الحالة", callback_data="show_status"),
         InlineKeyboardButton("❌ مسح الكل", callback_data="clear_all")]
    ])

def format_number(num):
    return f"{num:,}"

# =================== أوامر البوت ===================
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = str(message.from_user.id)
    
    # التحقق من الاشتراك الإجباري
    for channel in channels:
        try:
            member = await client.get_chat_member(channel, message.from_user.id)
            if member.status == "left":
                return await message.reply(f"⚠️ اشترك أولاً في قناة @{channel}\nثم أعد إرسال /start")
        except:
            return await message.reply(f"⚠️ اشترك أولاً في قناة @{channel}\nثم أعد إرسال /start")
    
    # إنشاء مستخدم جديد
    if user_id not in users:
        users[user_id] = {
            "groups": [],
            "captions": [],
            "session": None,
            "interval": 60,
            "auto_delete": 0,
            "active": False,
            "random_order": True,
            "last_post": None
        }
        save_data(USERS_FILE, users)
    
    await message.reply(
        f"✨ **مرحباً {message.from_user.first_name}** ✨\n\n"
        f"📌 **بوت النشر التلقائي للمجموعات**\n\n"
        f"🔹 **المميزات:**\n"
        f"• إضافة جروبات متعددة\n"
        f"• إضافة كليشات متعددة\n"
        f"• نشر تلقائي حسب المدة المحددة\n"
        f"• ترتيب عشوائي للجروبات والكليشات\n"
        f"• حذف تلقائي للرسائل\n\n"
        f"📖 **الخطوات:**\n"
        f"1️⃣ أضف جروبات\n"
        f"2️⃣ أضف كليشات\n"
        f"3️⃣ اضبط المدة\n"
        f"4️⃣ ابدأ النشر\n\n"
        f"⚠️ **ملاحظة:** يجب تسجيل الدخول أولاً باستخدام أمر /login",
        reply_markup=get_main_menu(user_id)
    )

@app.on_message(filters.command("login") & filters.private)
async def login_command(client, message):
    user_id = str(message.from_user.id)
    
    await message.reply(
        "🔐 **تسجيل الدخول إلى حساب التليجرام**\n\n"
        "أرسل رقم هاتفك مع رمز البلد\n"
        "مثال: +9647700000000\n\n"
        "أو ارسل /cancel للإلغاء"
    )
    
    try:
        phone_msg = await client.listen(message.chat.id, timeout=60)
        if phone_msg.text == "/cancel":
            return await phone_msg.reply("❌ تم الإلغاء")
        
        phone = phone_msg.text.strip()
        
        # إنشاء عميل مؤقت
        temp_client = Client("temp", api_id=API_ID, api_hash=API_HASH, in_memory=True)
        await temp_client.connect()
        
        try:
            sent_code = await temp_client.send_code(phone)
        except Exception as e:
            await temp_client.disconnect()
            return await phone_msg.reply(f"❌ خطأ: {str(e)}")
        
        await phone_msg.reply("📨 تم إرسال الكود. أرسله الآن:")
        
        code_msg = await client.listen(message.chat.id, timeout=120)
        if code_msg.text == "/cancel":
            await temp_client.disconnect()
            return await code_msg.reply("❌ تم الإلغاء")
        
        try:
            await temp_client.sign_in(phone, sent_code.phone_code_hash, code_msg.text)
        except Exception as e:
            if "PASSWORD" in str(e):
                await code_msg.reply("🔐 أدخل كلمة مرور التحقق بخطوتين:")
                password_msg = await client.listen(message.chat.id, timeout=60)
                if password_msg.text == "/cancel":
                    await temp_client.disconnect()
                    return await password_msg.reply("❌ تم الإلغاء")
                await temp_client.check_password(password_msg.text)
            else:
                await temp_client.disconnect()
                return await code_msg.reply(f"❌ خطأ: {str(e)}")
        
        # حفظ الجلسة
        session_string = await temp_client.export_session_string()
        await temp_client.disconnect()
        
        users[user_id]["session"] = session_string
        save_data(USERS_FILE, users)
        
        await client.send_message(message.chat.id, "✅ **تم تسجيل الدخول بنجاح!**", reply_markup=get_main_menu(user_id))
        
    except asyncio.TimeoutError:
        await message.reply("⏰ انتهى الوقت")

# =================== أزرار التحكم ===================
@app.on_callback_query()
async def handle_callback(client, callback):
    user_id = str(callback.from_user.id)
    data = callback.data
    
    if data == "show_groups":
        groups = users[user_id].get("groups", [])
        if not groups:
            text = "📁 **لا توجد جروبات مضافه**\n\nاضغط على 'إضافة جروب' لإضافة مجموعة جديدة"
        else:
            text = "📁 **قائمة الجروبات:**\n\n"
            for i, group in enumerate(groups, 1):
                text += f"{i}. `{group}`\n"
            text += f"\n📊 المجموع: {len(groups)} جروب"
        
        await callback.message.edit_text(text, reply_markup=get_main_menu(user_id))
        await callback.answer()
    
    elif data == "add_group":
        await callback.message.edit_text(
            "➕ **إضافة جروب جديد**\n\n"
            "أرسل معرف الجروب (يبدأ بـ -100)\n"
            "مثال: -1001234567890\n\n"
            "أو أرسل رابط الدعوة\n"
            "مثال: https://t.me/joinchat/xxxxx\n\n"
            "أو ارسل /cancel للإلغاء"
        )
        await callback.answer()
        
        try:
            group_msg = await client.listen(callback.from_user.id, timeout=60)
            if group_msg.text == "/cancel":
                return await group_msg.reply("❌ تم الإلغاء", reply_markup=get_main_menu(user_id))
            
            group_id = None
            text = group_msg.text.strip()
            
            if text.startswith("-") and text[1:].isdigit():
                group_id = text
            elif "t.me/" in text:
                try:
                    username = text.split("t.me/")[-1].split("?")[0]
                    chat = await client.get_chat(username)
                    group_id = str(chat.id)
                except:
                    pass
            
            if group_id:
                if group_id not in users[user_id]["groups"]:
                    users[user_id]["groups"].append(group_id)
                    save_data(USERS_FILE, users)
                    await group_msg.reply(f"✅ تم إضافة الجروب `{group_id}`", reply_markup=get_main_menu(user_id))
                else:
                    await group_msg.reply("⚠️ هذا الجروب مضاف بالفعل", reply_markup=get_main_menu(user_id))
            else:
                await group_msg.reply("❌ المعرف غير صالح", reply_markup=get_main_menu(user_id))
        except asyncio.TimeoutError:
            await callback.message.reply("⏰ انتهى الوقت", reply_markup=get_main_menu(user_id))
    
    elif data == "show_captions":
        captions = users[user_id].get("captions", [])
        if not captions:
            text = "📝 **لا توجد كليشات**\n\nاضغط على 'إضافة كليشة' لإضافة كليشة جديدة"
        else:
            text = "📝 **قائمة الكليشات:**\n\n"
            for i, cap in enumerate(captions, 1):
                short = cap[:50] + "..." if len(cap) > 50 else cap
                text += f"{i}. {short}\n"
            text += f"\n📊 المجموع: {len(captions)} كليشة"
        
        await callback.message.edit_text(text, reply_markup=get_main_menu(user_id))
        await callback.answer()
    
    elif data == "add_caption":
        await callback.message.edit_text(
            "📝 **إضافة كليشة جديدة**\n\n"
            "أرسل النص الذي تريد نشره\n"
            "يمكنك استخدام HTML و Emoji\n\n"
            "أو ارسل /cancel للإلغاء"
        )
        await callback.answer()
        
        try:
            caption_msg = await client.listen(callback.from_user.id, timeout=120)
            if caption_msg.text == "/cancel":
                return await caption_msg.reply("❌ تم الإلغاء", reply_markup=get_main_menu(user_id))
            
            caption_text = caption_msg.text
            users[user_id]["captions"].append(caption_text)
            save_data(USERS_FILE, users)
            
            await caption_msg.reply(f"✅ تم إضافة الكليشة #{len(users[user_id]['captions'])}", reply_markup=get_main_menu(user_id))
        except asyncio.TimeoutError:
            await callback.message.reply("⏰ انتهى الوقت", reply_markup=get_main_menu(user_id))
    
    elif data == "set_interval":
        await callback.message.edit_text(
            "⏱ **تعيين المدة بين الرسائل**\n\n"
            "أرسل المدة بالثواني\n"
            "الحد الأدنى: 10 ثوانٍ\n"
            "الحد الأقصى: 3600 ثانية (ساعة)\n\n"
            "مثال: 60 (دقيقة واحدة)\n\n"
            "أو ارسل /cancel للإلغاء"
        )
        await callback.answer()
        
        try:
            time_msg = await client.listen(callback.from_user.id, timeout=60)
            if time_msg.text == "/cancel":
                return await time_msg.reply("❌ تم الإلغاء", reply_markup=get_main_menu(user_id))
            
            interval = int(time_msg.text)
            if interval < 10:
                interval = 10
            elif interval > 3600:
                interval = 3600
            
            users[user_id]["interval"] = interval
            save_data(USERS_FILE, users)
            
            await time_msg.reply(f"✅ تم تعيين المدة إلى {interval} ثانية", reply_markup=get_main_menu(user_id))
        except ValueError:
            await callback.message.reply("❌ رقم غير صالح", reply_markup=get_main_menu(user_id))
        except asyncio.TimeoutError:
            await callback.message.reply("⏰ انتهى الوقت", reply_markup=get_main_menu(user_id))
    
    elif data == "set_auto_delete":
        current = users[user_id].get("auto_delete", 0)
        await callback.message.edit_text(
            f"🗑 **تعيين الحذف التلقائي**\n\n"
            f"الوضع الحالي: {'معطل' if current == 0 else f'{current} ثانية'}\n\n"
            "أرسل المدة بالثواني\n"
            "0 لتعطيل الحذف\n"
            "مثال: 1800 (نصف ساعة)\n\n"
            "أو ارسل /cancel للإلغاء"
        )
        await callback.answer()
        
        try:
            delete_msg = await client.listen(callback.from_user.id, timeout=60)
            if delete_msg.text == "/cancel":
                return await delete_msg.reply("❌ تم الإلغاء", reply_markup=get_main_menu(user_id))
            
            auto_delete = int(delete_msg.text)
            if auto_delete < 0:
                auto_delete = 0
            elif auto_delete > 86400:
                auto_delete = 86400
            
            users[user_id]["auto_delete"] = auto_delete
            save_data(USERS_FILE, users)
            
            if auto_delete == 0:
                await delete_msg.reply("✅ تم تعطيل الحذف التلقائي", reply_markup=get_main_menu(user_id))
            else:
                await delete_msg.reply(f"✅ سيتم حذف الرسائل بعد {auto_delete} ثانية", reply_markup=get_main_menu(user_id))
        except ValueError:
            await callback.message.reply("❌ رقم غير صالح", reply_markup=get_main_menu(user_id))
        except asyncio.TimeoutError:
            await callback.message.reply("⏰ انتهى الوقت", reply_markup=get_main_menu(user_id))
    
    elif data == "toggle_random":
        current = users[user_id].get("random_order", True)
        users[user_id]["random_order"] = not current
        save_data(USERS_FILE, users)
        
        status = "مفعل ✅" if not current else "معطل ❌"
        await callback.answer(f"تم {status} الترتيب العشوائي", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=get_main_menu(user_id))
    
    elif data == "toggle_posting":
        groups = users[user_id].get("groups", [])
        captions = users[user_id].get("captions", [])
        session = users[user_id].get("session")
        
        if not users[user_id].get("active"):
            # بدء النشر
            if not groups:
                return await callback.answer("❌ أضف جروباً أولاً!", show_alert=True)
            if not captions:
                return await callback.answer("❌ أضف كليشة أولاً!", show_alert=True)
            if not session:
                return await callback.answer("❌ سجل دخولك أولاً!\nاستخدم أمر /login", show_alert=True)
            
            users[user_id]["active"] = True
            save_data(USERS_FILE, users)
            
            await callback.answer("✅ تم بدء النشر", show_alert=True)
            await callback.message.edit_text("✅ **تم بدء النشر التلقائي**\n\nجارٍ الإرسال...", reply_markup=get_main_menu(user_id))
            
            # بدء مهمة النشر
            asyncio.create_task(posting_loop(client, int(user_id)))
        else:
            # إيقاف النشر
            users[user_id]["active"] = False
            save_data(USERS_FILE, users)
            await callback.answer("⏹ تم إيقاف النشر", show_alert=True)
            await callback.message.edit_text("⏹ **تم إيقاف النشر التلقائي**", reply_markup=get_main_menu(user_id))
    
    elif data == "show_status":
        user_data = users[user_id]
        groups = user_data.get("groups", [])
        captions = user_data.get("captions", [])
        
        status_text = f"📊 **حالة البوت**\n\n"
        status_text += f"📁 الجروبات: {len(groups)}\n"
        status_text += f"📝 الكليشات: {len(captions)}\n"
        status_text += f"⏱ المدة: {user_data.get('interval', 60)} ثانية\n"
        status_text += f"🗑 حذف: {user_data.get('auto_delete', 0)} ثانية\n"
        status_text += f"🔄 عشوائي: {'مفعل ✅' if user_data.get('random_order', True) else 'معطل ❌'}\n"
        status_text += f"🔐 حساب: {'مسجل ✅' if user_data.get('session') else 'غير مسجل ❌'}\n"
        status_text += f"▶️ النشر: {'يعمل 🟢' if user_data.get('active') else 'متوقف 🔴'}\n"
        
        if user_data.get("last_post"):
            status_text += f"\n📅 آخر نشر: {user_data['last_post']}"
        
        await callback.message.edit_text(status_text, reply_markup=get_main_menu(user_id))
        await callback.answer()
    
    elif data == "clear_all":
        await callback.message.edit_text(
            "⚠️ **تحذير!**\n\n"
            "هل أنت متأكد من حذف جميع الجروبات والكليشات؟\n\n"
            "هذا الإجراء لا يمكن التراجع عنه.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ نعم، احذف الكل", callback_data="confirm_clear")],
                [InlineKeyboardButton("❌ لا، إلغاء", callback_data="cancel_clear")]
            ])
        )
        await callback.answer()
    
    elif data == "confirm_clear":
        users[user_id]["groups"] = []
        users[user_id]["captions"] = []
        save_data(USERS_FILE, users)
        await callback.message.edit_text("✅ **تم حذف جميع الجروبات والكليشات**", reply_markup=get_main_menu(user_id))
        await callback.answer()
    
    elif data == "cancel_clear":
        await callback.message.edit_text("❌ تم الإلغاء", reply_markup=get_main_menu(user_id))
        await callback.answer()

# =================== دالة النشر الرئيسية ===================
async def posting_loop(client, user_id):
    user_id_str = str(user_id)
    
    while users[user_id_str].get("active", False):
        groups = users[user_id_str].get("groups", []).copy()
        captions = users[user_id_str].get("captions", []).copy()
        interval = users[user_id_str].get("interval", 60)
        auto_delete = users[user_id_str].get("auto_delete", 0)
        random_order = users[user_id_str].get("random_order", True)
        session_string = users[user_id_str].get("session")
        
        if not groups or not captions:
            users[user_id_str]["active"] = False
            save_data(USERS_FILE, users)
            await client.send_message(user_id, "⚠️ توقف النشر: لا توجد جروبات أو كليشات")
            break
        
        # ترتيب عشوائي
        if random_order:
            groups = random.sample(groups, len(groups))
            captions = random.sample(captions, len(captions))
        
        success_count = 0
        fail_count = 0
        
        # إنشاء عميل النشر
        try:
            user_client = Client(f"user_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session_string)
            await user_client.start()
        except Exception as e:
            await client.send_message(user_id, f"❌ فشل تسجيل الدخول: {str(e)[:100]}")
            users[user_id_str]["active"] = False
            save_data(USERS_FILE, users)
            break
        
        # إرسال لكل مجموعة
        for group_id in groups:
            if not users[user_id_str].get("active", False):
                break
            
            # اختيار كليشة عشوائية
            caption = random.choice(captions)
            
            try:
                # إرسال الرسالة
                msg = await user_client.send_message(int(group_id), caption)
                success_count += 1
                await client.send_message(user_id, f"✅ تم الإرسال إلى {group_id}")
                
                # حذف تلقائي
                if auto_delete > 0:
                    asyncio.create_task(delete_message_after(msg, auto_delete))
                
            except FloodWait as e:
                await client.send_message(user_id, f"⏳ انتظر {e.value} ثانية (FloodWait)")
                await asyncio.sleep(e.value)
                continue
            except (PeerIdInvalid, ChatWriteForbidden, UserNotParticipant) as e:
                fail_count += 1
                await client.send_message(user_id, f"❌ فشل الإرسال إلى {group_id}: {type(e).__name__}")
            except Exception as e:
                fail_count += 1
                await client.send_message(user_id, f"❌ خطأ: {str(e)[:50]}")
            
            # انتظار المدة
            await asyncio.sleep(interval)
        
        await user_client.stop()
        
        # تحديث آخر نشر
        users[user_id_str]["last_post"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_data(USERS_FILE, users)
        
        # إرسال تقرير
        await client.send_message(
            user_id,
            f"📊 **تقرير الدورة**\n\n"
            f"✅ نجح: {success_count}\n"
            f"❌ فشل: {fail_count}\n"
            f"📈 المجموع: {success_count + fail_count}\n"
            f"⏱ الوقت: {interval} ثانية"
        )
        
        # انتظار بين الدورات
        await asyncio.sleep(5)

async def delete_message_after(msg, delay):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass

# =================== إدارة المالك ===================
@app.on_message(filters.command("admin") & filters.user(OWNER_ID))
async def admin_command(client, message):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats"),
         InlineKeyboardButton("📢 قنوات", callback_data="admin_channels")],
        [InlineKeyboardButton("👑 إضافة VIP", callback_data="admin_add_vip"),
         InlineKeyboardButton("👑 حذف VIP", callback_data="admin_remove_vip")],
        [InlineKeyboardButton("📋 المستخدمين", callback_data="admin_users")]
    ])
    await message.reply("👑 **لوحة تحكم المالك**", reply_markup=markup)

@app.on_callback_query(filters.user(OWNER_ID))
async def admin_callback(client, callback):
    data = callback.data
    
    if data == "admin_stats":
        total_users = len(users)
        active_users = sum(1 for u in users.values() if u.get("active", False))
        total_groups = sum(len(u.get("groups", [])) for u in users.values())
        total_captions = sum(len(u.get("captions", [])) for u in users.values())
        
        await callback.message.edit_text(
            f"📊 **إحصائيات البوت**\n\n"
            f"👥 المستخدمين: {total_users}\n"
            f"🟢 النشطاء: {active_users}\n"
            f"📁 الجروبات: {total_groups}\n"
            f"📝 الكليشات: {total_captions}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]])
        )
    
    elif data == "admin_channels":
        markup = []
        for ch in channels:
            markup.append([InlineKeyboardButton(f"@{ch}", url=f"https://t.me/{ch}"), 
                          InlineKeyboardButton("🗑", callback_data=f"del_ch_{ch}")])
        markup.append([InlineKeyboardButton("➕ إضافة", callback_data="admin_add_channel")])
        markup.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
        await callback.message.edit_text("📢 **قنوات الاشتراك الإجباري**", reply_markup=InlineKeyboardMarkup(markup))
    
    elif data == "admin_add_channel":
        await callback.message.edit_text("أرسل معرف القناة (بدون @):")
        try:
            ch_msg = await client.listen(callback.from_user.id, timeout=30)
            channels.append(ch_msg.text)
            save_data(CHANNELS_FILE, channels)
            await ch_msg.reply("✅ تم إضافة القناة")
        except asyncio.TimeoutError:
            await callback.message.reply("⏰ انتهى الوقت")
    
    elif data.startswith("del_ch_"):
        ch = data.replace("del_ch_", "")
        if ch in channels:
            channels.remove(ch)
            save_data(CHANNELS_FILE, channels)
        await callback.answer("✅ تم الحذف")
        await admin_callback(client, callback)
    
    elif data == "admin_users":
        text = "📋 **قائمة المستخدمين**\n\n"
        for uid, u in list(users.items())[:50]:
            vip = "⭐" if uid == OWNER_ID else "○"
            active = "🟢" if u.get("active") else "⚪"
            groups = len(u.get("groups", []))
            text += f"{vip}{active} `{uid}` (ج: {groups})\n"
        
        if len(users) > 50:
            text += f"\n... و {len(users) - 50} آخرين"
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]]))
    
    elif data == "admin_add_vip":
        await callback.message.edit_text("أرسل معرف المستخدم:")
        try:
            uid_msg = await client.listen(callback.from_user.id, timeout=30)
            uid = uid_msg.text
            if uid not in users:
                users[uid] = {"groups": [], "captions": [], "session": None, "interval": 60, "auto_delete": 0, "active": False, "random_order": True}
            users[uid]["vip"] = True
            save_data(USERS_FILE, users)
            await uid_msg.reply(f"✅ تم تفعيل VIP للمستخدم {uid}")
        except asyncio.TimeoutError:
            await callback.message.reply("⏰ انتهى الوقت")
    
    elif data == "admin_remove_vip":
        await callback.message.edit_text("أرسل معرف المستخدم:")
        try:
            uid_msg = await client.listen(callback.from_user.id, timeout=30)
            uid = uid_msg.text
            if uid in users:
                users[uid]["vip"] = False
                save_data(USERS_FILE, users)
                await uid_msg.reply(f"✅ تم إلغاء VIP للمستخدم {uid}")
            else:
                await uid_msg.reply("❌ المستخدم غير موجود")
        except asyncio.TimeoutError:
            await callback.message.reply("⏰ انتهى الوقت")
    
    elif data == "admin_back":
        await admin_command(client, callback.message)

# =================== تشغيل البوت ===================
async def main():
    print("🤖 **بوت النشر التلقائي**")
    print("=" * 40)
    print(f"✅ البوت يعمل!")
    print(f"👤 معرف المطور: {OWNER_ID}")
    print(f"📊 عدد المستخدمين: {len(users)}")
    print(f"📢 قنوات الاشتراك: {channels}")
    print("=" * 40)
    await app.start()
    await idle()
    print("🛑 تم إيقاف البوت")

if __name__ == "__main__":
    asyncio.run(main())
