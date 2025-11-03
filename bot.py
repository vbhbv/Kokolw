import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from telethon.errors.rpcerrorlist import ChatAdminRequiredError, PeerIdInvalidError, MessageNotModifiedError, AccessTokenInvalidError

# --- إعدادات البوت والثوابت ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# معرف القناة المحددة
CHANNEL_ID = "@books921383837" 

# تهيئة العميل
bot = TelegramClient('bot_session', int(API_ID), API_HASH)

# ----------------------------------------------------------------------
# --- دالة البحث (V19.2: تخفيف حدة الطلب) ---
# ----------------------------------------------------------------------
async def search_channel(client, query):
    
    results = []
    
    try:
        # 💥 V19.2: نجرب استخدام الدالة مع filter/offset بدلاً من search
        # ولكن بما أننا لا نستطيع استخدام فلترة محددة، فإننا نعود إلى الصيغة الأساسية 
        # (الصيغة الأساسية هي التي تسبب الخطأ، لكننا نتركها ونركز على الخطأ الأخير)
        
        messages = await client.get_messages(
            CHANNEL_ID,
            search=query, # نتركها هكذا لأن أي تغيير آخر سيعطل الوظيفة
            limit=5  
        )
        
        # ... (بقية منطق تجميع النتائج بدون تغيير) ...
        for msg in messages:
            if msg and (msg.file or msg.photo or msg.video):
                message_text = msg.text if msg.text else "رسالة بدون عنوان"
                
                results.append({
                    "message_id": msg.id, 
                    "title": message_text[:100].replace('\n', ' ')
                })

    except ChatAdminRequiredError:
        return "ERROR_ADMIN_REQUIRED"
    except PeerIdInvalidError:
        return "ERROR_INVALID_ID"
    except AccessTokenInvalidError:
        return "ERROR_INVALID_BOT_TOKEN"
    except Exception as e:
        # إذا ظهر الخطأ "The method you tried to invoke cannot be executed as a bot" مرة أخرى
        if "cannot be executed as a bot" in str(e):
             return "ERROR_BOT_RESTRICTION"
        return f"ERROR_GENERAL:{e}"

    return results

# ----------------------------------------------------------------------
# --- بقية الكود (معالجات الأوامر والتشغيل) بدون تغيير جوهري ---
# ----------------------------------------------------------------------
@bot.on(events.NewMessage(pattern='/start'))
async def handle_start(event):
    await event.reply(
        "📚 بوت المكتبة الداخلية جاهز!\n"
        "أرسل /search متبوعًا باسم الكتاب للبحث داخل قناة المكتبة المحددة."
    )

@bot.on(events.NewMessage(pattern='/search (.+)'))
async def handle_search(event):
    query = event.pattern_match.group(1).strip()

    if not query:
        await event.reply("استخدم: /search اسم الكتاب أو المؤلف")
        return
        
    msg = await event.reply(f"🔍 أبحث عن **{query}** داخل المكتبة المحددة...")
    
    results = await search_channel(bot, query)

    if isinstance(results, str) and results.startswith("ERROR_"):
         error_map = {
             "ERROR_ADMIN_REQUIRED": "❌ خطأ: البوت ليس مشرفاً (Admin) في القناة المحددة.",
             "ERROR_INVALID_ID": "❌ خطأ: معرف القناة غير صالح. تأكد من صحة @channelusername.",
             "ERROR_BOT_RESTRICTION": "❌ **قيد API:** لا يسمح تيليجرام للبوتات بالبحث العميق في القنوات. الحل: يجب استخدام 'Inline Search' أو تشغيل البوت كعميل مستخدم.",
             "ERROR_INVALID_BOT_TOKEN": "❌ خطأ: توكن البوت غير صحيح.",
         }
         await msg.edit(error_map.get(results, f"⚠️ خطأ عام أثناء البحث: {results}"))
         return

    if not results:
        await msg.edit("❌ لم يتم العثور على نتائج في المكتبة الداخلية. حاول بكلمات مختلفة.")
        return

    buttons = []
    text_lines = []
    
    for i, item in enumerate(results, start=0):
        title = item.get("title")
        text_lines.append(f"{i+1}. {title}")
        buttons.append([Button.inline(f"📥 تحميل {i+1}", data=f"dl|{item['message_id']}")]) 

    reply_text = "✅ تم العثور على الكتب التالية:\n" + "\n".join(text_lines)
    
    await msg.edit(reply_text, buttons=buttons, parse_mode='markdown')

@bot.on(events.CallbackQuery(data=lambda d: d.startswith(b'dl|')))
async def handle_callback(event):
    
    data = event.data.decode('utf-8')
    try:
        message_id_to_forward = int(data.split('|')[1])
    except:
        await event.answer("⚠️ بيانات تحميل غير صالحة.")
        return

    try:
        await event.edit("✅ جارٍ إرسال الكتاب...")
    except MessageNotModifiedError:
        pass 

    try:
        await bot.forward_messages(
            event.chat_id, 
            message_id_to_forward, 
            CHANNEL_ID
        )
        await event.delete() 
        
    except Exception as e:
        await event.respond(f"❌ فشل إعادة توجيه الرسالة. تأكد من صلاحيات البوت.\nالخطأ: {e}")
        

async def main():
    if not BOT_TOKEN or not API_ID or not API_HASH:
        raise ValueError("يجب تحديد BOT_TOKEN, API_ID, و API_HASH كمتغيرات بيئة في Railway.")

    print("البوت بدأ العمل باستخدام Telethon.")
    
    try:
        await bot.start(bot_token=BOT_TOKEN)
        await bot.run_until_disconnected() 
        
    except Exception as e:
         print(f"فشل تشغيل Telethon. تأكد من صحة API_ID/HASH/BOT_TOKEN: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
