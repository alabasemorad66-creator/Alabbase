import os
import json
import asyncio
from datetime import datetime, timedelta
from pytz import timezone
from asyncio import sleep, create_task

from pyrogram import Client, filters, idle
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup as Markup, InlineKeyboardButton as Button, ForceReply
from pyrogram.errors import (
    PhoneNumberInvalid, 
    PhoneCodeInvalid, 
    PhoneCodeExpired, 
    SessionPasswordNeeded, 
    PasswordHashInvalid,
    ChatWriteForbidden,
    UserNotParticipant,
    BotMethodInvalid
)
from pyromod import listen, exceptions
from typing import Union

# --- CONFIGURATION ---
# Replace these with your actual values or set them as environment variables
API_ID = int(os.getenv("API_ID", "34923196"))
API_HASH = os.getenv("API_HASH", "b3f6e47ecd3231186f8f7e01ab41938e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8091669494:AAFgMcJKNweaLjkpotwgBPpCLSpwJqs4BsA")
owner = int(os.getenv("OWNER_ID", "8310839908"))

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=None
)

# Initialize database files
users_db = "users.json"
channels_db = "channels.json"

def write(fp, data):
    with open(fp, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

def read(fp):
    if not os.path.exists(fp):
        initial_data = [] if fp == channels_db else {}
        write(fp, initial_data)
        return initial_data
    with open(fp, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return [] if fp == channels_db else {}

users = read(users_db)
channels = read(channels_db)

# --- FILTERS ---
async def Owner(_, __: Client, message: Message):
    return (message.from_user.id == owner)

isOwner = filters.create(Owner)

# --- KEYBOARDS ---
adminMarkup = Markup([
    [
        Button("- الغاء VIP -", callback_data="cancelVIP"),
        Button("- تفعيل VIP -", callback_data="addVIP")
    ],
    [
        Button("- الاحصائيات -", callback_data="statics"),
        Button("- قنوات الإشتراك -", callback_data="channels")
    ]
])

# --- FUNCTIONS ---
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
        user_str = str(user_id)
        if user_str not in users or not users[user_str].get("vip"): 
            break
        
        limitation = users[user_str].get("limitation", {})
        end_date_str = limitation.get("endDate")
        end_time_str = limitation.get("endTime")
        
        if not end_date_str or not end_time_str:
            break
            
        target_dt_str = f"{end_date_str} {end_time_str}"
        current_dt = datetime.now(_timezone)
        current_dt_str = current_dt.strftime("%Y-%m-%d %H:%M")
        
        if current_dt_str >= target_dt_str:
            users[user_str]["vip"] = False
            users[user_str]["limitation"] = {}
            write(users_db, users)
            try:
                await app.send_message(
                    user_id,
                    "- انتهى اشتراك VIP الخاص بك.\n- راسل المطور اذا كنت تريد تجديد اشتراكك."
                )
            except:
                pass
            break
        await sleep(60)

async def posting(user_id):
    user_str = str(user_id)
    if users[user_str].get("posting"):
        client = Client(
            user_str,
            api_id = API_ID,
            api_hash = API_HASH,
            session_string = users[user_str]["session"],
            in_memory=True
        )
        try:
            await client.start()
        except Exception as e:
            users[user_str]["posting"] = False
            write(users_db, users)
            await app.send_message(int(user_id), f"- فشل تشغيل الحساب: {str(e)}")
            return

    while users[user_str].get("posting"):
        try:
            sleepTime = users[user_str].get("waitTime", 60)
            groups = users[user_str].get("groups", [])
            caption = users[user_str].get("caption")
            
            if not caption:
                users[user_str]["posting"] = False
                write(users_db, users)
                await app.send_message(int(user_id), "- تم إيقاف النشر بسبب عدم اضافة كليشة.", reply_markup=Markup([[Button("- إضافة كليشه -", callback_data="newCaption")]]))
                break

            for group in groups:
                if not users[user_str].get("posting"): break
                try:
                    target_group = int(group) if str(group).startswith("-") or str(group).isdigit() else group
                    await client.send_message(target_group, caption)
                except ChatWriteForbidden:
                    try:
                        await client.join_chat(group)
                        await client.send_message(group, caption)
                    except Exception as e:
                        await app.send_message(int(user_id), f"- خطأ في النشر بمجموعة {group}: {str(e)}")
                except Exception as e:
                    try:
                        chat = await client.join_chat(group)
                        await client.send_message(chat.id, caption)
                        # Update group ID if it changed
                        if chat.id not in groups:
                            groups.append(chat.id)
                            if group in groups: groups.remove(group)
                            write(users_db, users)
                    except Exception as ex:
                        await app.send_message(int(user_id), f"- تعذر النشر في {group}: {str(ex)}")
                await sleep(2) # Small delay between groups
            
            # Wait for the specified time before next round
            for _ in range(sleepTime):
                if not users[user_str].get("posting"): break
                await sleep(1)
        except Exception as e:
            print(f"Error in posting loop for {user_id}: {e}")
            await sleep(10)
            
    try:
        await client.stop()
    except:
        pass

async def subscription(user_id):
    for channel in channels:
        try:
            await app.get_chat_member(channel, user_id)
        except UserNotParticipant:
            return channel
        except:
            continue
    return True

# --- HANDLERS ---

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_: Client, message: Message):
    user_id = message.from_user.id
    if str(user_id) not in users:
        users[str(user_id)] = {"vip": False, "groups": [], "posting": False}
        write(users_db, users)
    
    sub = await subscription(user_id)
    if sub is not True:
        return await message.reply(f"- عذراً عزيزي، عليك الاشتراك في قناة البوت أولاً لتتمكن من استخدامه.\n- القناة: @{sub}")

    fname = message.from_user.first_name
    caption = f"- مرحبا عزيزي [{fname}](tg://settings) في بوت النشر التلقائي\n\n- استخدم الازرار التاليه للتحكم:"
    markup = Markup([
        [Button("- قسم الحساب -", callback_data="account")],
        [Button("- إعدادات النشر -", callback_data="posting_settings")],
        [Button("- بدء النشر -", callback_data="startPosting"), Button("- إيقاف النشر -", callback_data="stopPosting")]
    ])
    await message.reply(caption, reply_markup=markup)

@app.on_callback_query(filters.regex("^toHome$"))
async def toHome(_: Client, callback: CallbackQuery):
    fname = callback.from_user.first_name
    caption = f"- مرحبا عزيزي [{fname}](tg://settings) في بوت النشر التلقائي\n\n- استخدم الازرار التاليه للتحكم:"
    markup = Markup([
        [Button("- قسم الحساب -", callback_data="account")],
        [Button("- إعدادات النشر -", callback_data="posting_settings")],
        [Button("- بدء النشر -", callback_data="startPosting"), Button("- إيقاف النشر -", callback_data="stopPosting")]
    ])
    await callback.message.edit_text(caption, reply_markup=markup)

@app.on_callback_query(filters.regex("^account$"))
async def account_menu(_: Client, callback: CallbackQuery):
    fname = callback.from_user.first_name
    caption = f"- مرحبا عزيزي [{fname}](tg://settings) في قسم الحساب\n\n- استخدم الازرار التاليه للتحكم بحسابك:"
    markup = Markup([
        [Button("- تسجيل حسابك -", callback_data="login"), Button("- تغيير الحساب -", callback_data="changeAccount")],
        [Button("- العوده -", callback_data="toHome")]
    ])
    await callback.message.edit_text(caption, reply_markup=markup)

@app.on_callback_query(filters.regex("^posting_settings$"))
async def posting_settings(_: Client, callback: CallbackQuery):
    markup = Markup([
        [Button("- إضافة سوبر -", callback_data="newSuper"), Button("- السوبرات المضافة -", callback_data="currentSupers")],
        [Button("- تعيين الكليشة -", callback_data="newCaption"), Button("- وقت الانتظار -", callback_data="waitTime")],
        [Button("- العوده -", callback_data="toHome")]
    ])
    await callback.message.edit_text("- إعدادات النشر التلقائي:", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(login|changeAccount)$"))
async def login_handler(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_str = str(user_id)
    if user_id != owner and not users.get(user_str, {}).get("vip"):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    
    if callback.data == "changeAccount" and not users.get(user_str, {}).get("session"):
        return await callback.answer("- لم تقم بالتسجيل بعد.", show_alert=True)
    
    await callback.message.delete()
    try:
        ask = await app.listen(user_id, filters=filters.text, timeout=60)
        if ask.text == "/cancel": return await ask.reply("- تم إلغاء العمليه.")
        
        _number = ask.text
        lmsg = await ask.reply(f"- جارٍ تسجيل الدخول إلى حسابك...")
        
        client = Client("temp_reg", api_id=API_ID, api_hash=API_HASH, in_memory=True)
        await client.connect()
        
        try:
            p_code_hash = await client.send_code(_number)
        except Exception as e:
            return await lmsg.edit_text(f"- خطأ: {str(e)}")
            
        code_msg = await app.listen(user_id, filters=filters.text, timeout=120)
        try:
            await client.sign_in(_number, p_code_hash.phone_code_hash, code_msg.text.replace(" ", ""))
        except SessionPasswordNeeded:
            pwd_msg = await app.listen(user_id, filters=filters.text, timeout=120)
            await client.check_password(pwd_msg.text)
            
        session = await client.export_session_string()
        await client.disconnect()
        
        if user_str not in users: users[user_str] = {"vip": (user_id == owner)}
        users[user_str]["session"] = session
        write(users_db, users)
        
        await app.send_message(user_id, "- تم تسجيل الدخول بنجاح!", reply_markup=Markup([[Button("الصفحه الرئيسيه", callback_data="toHome")]]))
    except exceptions.TimeOut:
        await app.send_message(user_id, "- انتهى الوقت، حاول مجدداً.")
    except Exception as e:
        await app.send_message(user_id, f"- حدث خطأ: {str(e)}")

@app.on_callback_query(filters.regex("^newSuper$"))
async def newSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != owner and not users.get(str(user_id), {}).get("vip"):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    
    await callback.message.delete()
    try:
        ask = await app.listen(user_id, filters=filters.text, timeout=60)
        if ask.text == "/cancel": return await ask.reply("- تم إلغاء العمليه.")
        
        chat_id = ask.text
        if not chat_id.startswith("-") and not chat_id.isdigit():
            try:
                chat = await app.get_chat(chat_id.replace("https://t.me/", "").split("/")[-1])
                chat_id = chat.id
            except:
                pass
        
        if "groups" not in users[str(user_id)]: users[str(user_id)]["groups"] = []
        users[str(user_id)]["groups"].append(chat_id)
        write(users_db, users)
        await ask.reply("- تمت إضافة السوبر بنجاح.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))
    except:
        await app.send_message(user_id, "- فشل في إضافة السوبر.")

@app.on_callback_query(filters.regex("^currentSupers$"))
async def currentSupers(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    groups = users.get(str(user_id), {}).get("groups", [])
    if not groups: return await callback.answer("- لم يتم إضافة اي سوبر", show_alert=True)
    
    markup = []
    for g in groups:
        markup.append([Button(f"{g}", callback_data="none"), Button("🗑", callback_data=f"delSuper {g}")])
    markup.append([Button("- الصفحه الرئيسيه -", callback_data="toHome")])
    await callback.message.edit_text("- السوبرات المضافة:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^delSuper (.*)"))
async def delSuper_handler(_: Client, callback: CallbackQuery):
    group = callback.data.split(None, 1)[1]
    user_id = str(callback.from_user.id)
    if group in users[user_id]["groups"]:
        users[user_id]["groups"].remove(group)
        write(users_db, users)
        await callback.answer("- تم الحذف", show_alert=True)
    await currentSupers(_, callback)

@app.on_callback_query(filters.regex("^newCaption$"))
async def newCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    try:
        ask = await app.listen(user_id, filters=filters.text, timeout=120)
        if ask.text == "/cancel": return await ask.reply("- تم إلغاء العمليه.")
        users[str(user_id)]["caption"] = ask.text
        write(users_db, users)
        await ask.reply("- تم حفظ الكليشة.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))
    except:
        pass

@app.on_callback_query(filters.regex("^waitTime$"))
async def waitTime_handler(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    try:
        ask = await app.listen(user_id, filters=filters.text, timeout=60)
        users[str(user_id)]["waitTime"] = int(ask.text)
        write(users_db, users)
        await ask.reply("- تم حفظ مدة الانتظار.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))
    except:
        await app.send_message(user_id, "- خطأ في القيمة.")

@app.on_callback_query(filters.regex("^startPosting$"))
async def startPosting_handler(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_str = str(user_id)
    if not users.get(user_str, {}).get("session"): return await callback.answer("- سجل حسابك أولاً", show_alert=True)
    if not users.get(user_str, {}).get("groups"): return await callback.answer("- أضف سوبرات أولاً", show_alert=True)
    if users[user_str].get("posting"): return await callback.answer("- النشر مفعل بالفعل", show_alert=True)
    
    users[user_str]["posting"] = True
    write(users_db, users)
    create_task(posting(user_id))
    await callback.message.edit_text("- تم بدء النشر التلقائي", reply_markup=Markup([[Button("- إيقاف النشر -", callback_data="stopPosting"), Button("- عوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex("^stopPosting$"))
async def stopPosting_handler(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    users[str(user_id)]["posting"] = False
    write(users_db, users)
    await callback.message.edit_text("- تم إيقاف النشر التلقائي", reply_markup=Markup([[Button("- بدء النشر -", callback_data="startPosting"), Button("- عوده -", callback_data="toHome")]]))

# --- ADMIN HANDLERS ---

@app.on_message(filters.command("admin") & filters.private & isOwner)
@app.on_callback_query(filters.regex("toAdmin") & isOwner)
async def admin_panel(_: Client, message: Union[Message, CallbackQuery]):
    func = message.reply if isinstance(message, Message) else message.message.edit_text
    await func("- لوحة التحكم للمالك:", reply_markup=adminMarkup)

@app.on_callback_query(filters.regex("addVIP") & isOwner)
async def addVIP_handler(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    try:
        ask = await app.listen(user_id, filters=filters.text, timeout=60)
        target_id = ask.text
        days_ask = await app.listen(user_id, filters=filters.text, timeout=60)
        days = int(days_ask.text)
        
        vipDate = timeCalc(days)
        users[target_id] = {
            "vip": True,
            "limitation": {
                "days": days,
                "startDate": vipDate["current_date"],
                "endDate": vipDate["end_date"],
                "endTime": vipDate["endTime"],
            }
        }
        write(users_db, users)
        create_task(vipCanceler(int(target_id)))
        await app.send_message(user_id, f"- تم تفعيل VIP للمستخدم {target_id}")
    except:
        await app.send_message(user_id, "- فشل في التفعيل.")

@app.on_callback_query(filters.regex("statics") & isOwner)
async def statics_handler(_: Client, callback: CallbackQuery):
    total = len(users)
    vip = sum(1 for u in users.values() if u.get("vip"))
    await callback.message.edit_text(f"- المستخدمين: {total}\n- VIP: {vip}", reply_markup=Markup([[Button("- عوده -", callback_data="toAdmin")]]))

# --- MAIN ---

async def main():
    await app.start()
    # Restart posting tasks for users who had it enabled
    for user_id in users:
        if users[user_id].get("posting"):
            create_task(posting(int(user_id)))
        if users[user_id].get("vip") and user_id != str(owner):
            create_task(vipCanceler(int(user_id)))
    print("Bot Started!")
    await idle()
    await app.stop()
if __name__ == "__main__":
    asyncio.run(main())
    
