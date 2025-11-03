import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import InputWebDocument, InputBotInlineResult, InputBotInlineMessageMediaAuto, InlineQueryResult, InlineQueryResultArticle
from telethon.errors.rpcerrorlist import ChatAdminRequiredError, PeerIdInvalidError

# --- إعدادات البوت والثوابت ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# معرف القناة المحددة
CHANNEL_ID = "@books921383837" 

# تهيئة العميل
bot = TelegramClient('bot_session', int(API_ID), API_HASH)

# ----------------------------------------------------------------------
# --- دالة البحث (Telethon) - بقيت كما هي ---
# ----------------------------------------------------------------------
# هذه الدالة كانت تسبب خطأ القيد، لكننا سنحاول استخدامها هنا
# لأن البحث المضمن قد يعطيها صلاحيات مختلفة.
async def search_channel(client, query):
    
    results = []
    try:
        messages = await client.get_messages(
            CHANNEL_ID,
            search=query,
            limit=5  
        )
        for msg in messages:
            if msg and (msg.file or msg.photo or msg.video):
                message_text = msg.text if msg.text else (msg.file.name if msg.file else "رسالة بدون عنوان")
                
                results.append({
                    "message_id": msg.id, 
                    "title": message_text[:100].replace('\n', ' ')
                })

    except Exception as e:
        if "cannot be executed as a bot" in str(e):
             return "ERROR_BOT_RESTRICTION"
        return f"ERROR_GENERAL:{e}"
    
    return results

# ----------------------------------------------------------------------
# --- معالج أمر /start (بدون تغيير) ---
# ----------------------------------------------------------------------
@bot.on(events.NewMessage(pattern='/start'))
async def handle_start(event):
    await event.reply(
        "📚 بوت المكتبة الداخلية جاهز!\n"
        "للبحث، استخدم البحث المضمن (Inline Search) في أي محادثة، على النحو التالي:\n"
        "`@yourbotusername اسم الكتاب`"
    )

# ----------------------------------------------------------------------
# --- 💥 V20.0: معالج البحث المضمن (Inline Query) ---
# ----------------------------------------------------------------------
@bot.on(events.InlineQuery)
async def handle_inline_query(event):
    query = event.text
    
    if not query:
        # إذا كانت الاستعلام فارغة، قدم رسالة تعليمية
        await event.answer([
            InlineQueryResultArticle(
                title="🔍 ابدأ البحث",
                description="أدخل اسم الكتاب أو المؤلف للبحث في المكتبة.",
                input_message=InputBotInlineMessageMediaAuto("الرجاء إدخال نص البحث.")
            )
        ])
        return
    
    # تنفيذ البحث (نستخدم نفس الدالة التي كانت تسبب خطأ القيد)
    search_results = await search_channel(bot, query)
    
    if isinstance(search_results, str):
        # معالجة أخطاء البحث داخل Inline
        title = "❌ فشل البحث"
        description = "حدث خطأ في الوصول للقناة أو بسبب قيود تيليجرام."
        if "ERROR_BOT_RESTRICTION" in search_results:
             description = "البحث العميق محظور على البوتات. الرجاء التأكد من صلاحيات البوت."
        
        await event.answer([
             InlineQueryResultArticle(
                title=title,
                description=description,
                input_message=InputBotInlineMessageMediaAuto(description)
            )
        ])
        return

    if not search_results:
        await event.answer([
            InlineQueryResultArticle(
                title="❌ لا توجد نتائج",
                description=f"لم يتم العثور على '{query}' في المكتبة.",
                input_message=InputBotInlineMessageMediaAuto(f"لم يتم العثور على '{query}'.")
            )
        ])
        return

    # بناء نتائج Inline
    results = []
    for item in search_results:
        
        # لـ Inline Search، يجب أن تكون النتيجة هي رسالة يمكن إرسالها.
        # هنا سننشئ نتيجة ترسل رسالة تحتوي على الكتاب (عن طريق إعادة توجيه الرسالة).
        # هذا الجزء معقد لأنه لا يمكن إعادة توجيه ملف مباشرة في نتيجة Inline.
        # الحل الأسهل هو إرسال رابط توجيه إلى البوت.
        
        # نستخدم رسالة Article التي تطلب من المستخدم الضغط للذهاب إلى البوت
        results.append(
            InlineQueryResultArticle(
                title=item['title'],
                description="اضغط للتحميل المباشر",
                # النص الذي سيظهر بعد اختيار النتيجة
                input_message=InputBotInlineMessageMediaAuto(
                    f"✅ تم العثور على '{item['title']}'. لتحميل الكتاب، اضغط على الزر أدناه."
                ),
                # الزر الذي يظهر أسفل النتيجة
                reply_markup=bot.build_reply_markup([
                    [Button.url('📥 تحميل مباشر', f'https://t.me/yourbotusername?start=get_{item["message_id"]}')]
                ])
            )
        )
        
    await event.answer(results)

# ----------------------------------------------------------------------
# --- معالج الأوامر العميقة (Deep Linking) للتحميل ---
# ----------------------------------------------------------------------
@bot.on(events.NewMessage(pattern='/start get_(\d+)'))
async def handle_deep_link_download(event):
    # يستخدم هذا المعالج عندما يضغط المستخدم على زر التحميل في Inline Result
    try:
        message_id_to_forward = int(event.pattern_match.group(1))
    except:
        await event.reply("❌ رابط تحميل غير صالح.")
        return

    await event.reply("✅ جارٍ إرسال الكتاب...")
    
    try:
        # إعادة توجيه الرسالة مباشرة
        await bot.forward_messages(
            event.chat_id, 
            message_id_to_forward, 
            CHANNEL_ID
        )
        
    except Exception as e:
        await event.reply(f"❌ فشل إعادة توجيه الرسالة. تأكد من صلاحيات البوت.\nالخطأ: {e}")
        

# ----------------------------------------------------------------------
# --- دالة التشغيل الرئيسية ---
# ----------------------------------------------------------------------
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
