import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import ReplyInlineMarkup, InlineKeyboardButton
from telethon.errors.rpcerrorlist import ChatAdminRequiredError, PeerIdInvalidError, MessageNotModifiedError

# --- إعدادات البوت والثوابت ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# معرف القناة المحددة
CHANNEL_ID = "@books921383837" 

# تهيئة العميل
# نستخدم اسم البوت (البادئة) كاسم للجلسة
bot = TelegramClient('bot_session', int(API_ID), API_HASH)

# ----------------------------------------------------------------------
# --- دالة البحث (Telethon) ---
# ----------------------------------------------------------------------
async def search_channel(client, query):
    
    results = []
    
    try:
        messages = await client.get_messages(
            CHANNEL_ID,
            search=query,
            limit=5  
        )
        
        for msg in messages:
            # نتجاهل الرسائل النصية البحتة
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
    except Exception as e:
        print(f"Telethon general search error: {e}")
        return f"ERROR_GENERAL:{e}"

    return results

# ----------------------------------------------------------------------
# --- معالج أمر /start ---
# ----------------------------------------------------------------------
@bot.on(events.NewMessage(pattern='/start'))
async def handle_start(event):
    await event.reply(
        "📚 بوت المكتبة الداخلية جاهز!\n"
        "أرسل /search متبوعًا باسم الكتاب للبحث داخل قناة المكتبة المحددة."
    )

# ----------------------------------------------------------------------
# --- معالج أمر /search ---
# ----------------------------------------------------------------------
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
             "ERROR_INVALID_ID": "❌ خطأ: معرف القناة غير صالح. تأكد من صحة @channelusername."
         }
         await msg.edit(error_map.get(results, f"⚠️ خطأ عام أثناء البحث: {results}"))
         return

    if not results:
        await msg.edit("❌ لم يتم العثور على نتائج في المكتبة الداخلية. حاول بكلمات مختلفة.")
        return

    # بناء الأزرار والرد
    buttons = []
    text_lines = []
    
    for i, item in enumerate(results, start=0):
        title = item.get("title")
        text_lines.append(f"{i+1}. {title}")
        # استخدام صيغة callback_data لـ Telethon
        buttons.append([InlineKeyboardButton(f"📥 تحميل {i+1}", data=f"dl|{item['message_id']}")]) 

    reply_text = "✅ تم العثور على الكتب التالية:\n" + "\n".join(text_lines)
    
    await msg.edit(reply_text, buttons=buttons, parse_mode='markdown')


# ----------------------------------------------------------------------
# --- معالج أزرار التحميل (Callback) ---
# ----------------------------------------------------------------------
@bot.on(events.CallbackQuery(data=lambda d: d.startswith(b'dl|')))
async def handle_callback(event):
    
    data = event.data.decode('utf-8')
    try:
        # استخراج message_id مباشرة من الـ callback data
        message_id_to_forward = int(data.split('|')[1])
    except:
        await event.answer("⚠️ بيانات تحميل غير صالحة.")
        return

    try:
        await event.edit("✅ جارٍ إرسال الكتاب...")
    except MessageNotModifiedError:
        pass # تجاهل إذا لم تتغير الرسالة

    try:
        # Telethon: إعادة توجيه الرسالة
        await bot.forward_messages(
            event.chat_id, 
            message_id_to_forward, 
            CHANNEL_ID
        )
        # حذف رسالة "جارٍ الإرسال"
        await event.delete() 
        
    except Exception as e:
        await event.respond(f"❌ فشل إعادة توجيه الرسالة. تأكد من صلاحيات البوت.\nالخطأ: {e}")
        

# ----------------------------------------------------------------------
# --- دالة التشغيل الرئيسية ---
# ----------------------------------------------------------------------
async def main():
    if not BOT_TOKEN or not API_ID or not API_HASH:
        raise ValueError("يجب تحديد BOT_TOKEN, API_ID, و API_HASH كمتغيرات بيئة في Railway.")

    print("البوت بدأ العمل باستخدام Telethon.")
    
    # Telethon client start
    try:
        # يجب تمرير bot_token ليتصل كبوت، وليس كمستخدم عادي
        await bot.start(bot_token=BOT_TOKEN)
        await bot.run_until_disconnected() # تشغيل حتى يتم إيقافه
        
    except Exception as e:
         print(f"فشل تشغيل Telethon. تأكد من صحة API_ID/HASH/BOT_TOKEN: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
