import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes 
from telegram.constants import ParseMode
from telegram import error as TelegramError

# Telethon Imports
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import ChatAdminRequiredError, PeerIdInvalidError

# --- إعدادات البوت والثوابت ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")    
API_HASH = os.getenv("API_HASH") 

# V17.0: معرف القناة المحددة
CHANNEL_ID = "@books921383837" 

TEMP_RESULTS_KEY = "current_search_results"

# تهيئة عميل Telethon (سيتم تهيئته في دالة main)
telethon_client = None

# ----------------------------------------------------------------------
# --- دالة البحث بواسطة Telethon (V18.0) ---
# ----------------------------------------------------------------------
async def search_telethon_channel(query: str):
    
    if telethon_client is None:
        # لا ينبغي أن يحدث هذا إذا تم التشغيل بشكل صحيح
        return "ERROR_CLIENT_UNINITIALIZED"
    
    results = []
    
    try:
        messages = await telethon_client.get_messages(
            CHANNEL_ID,
            search=query,
            limit=5  
        )
        
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
    except Exception as e:
        print(f"Telethon general search error: {e}")
        return f"ERROR_GENERAL:{e}"

    return results


# ----------------------------------------------------------------------
# --- دالة Callback وبقية الأوامر (بدون تغيير) ---
# ----------------------------------------------------------------------

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    
    if data.startswith("dl|"):
        try:
            index_str = data.split("|", 1)[1]
            index = int(index_str)
            message_id_to_forward = context.user_data[TEMP_RESULTS_KEY][index]["message_id"]

        except Exception:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ حدث خطأ أثناء معالجة زر التحميل (نتيجة غير صالحة).")
            return
            
        await query.edit_message_text("✅ جارٍ إرسال الكتاب...")
        
        try:
            await context.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=CHANNEL_ID, 
                message_id=message_id_to_forward 
            )
            await query.message.delete()
            
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ فشل إعادة توجيه الرسالة. تأكد من أن البوت مشرف في القناة.\nالخطأ: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 بوت المكتبة الداخلية جاهز!\n"
        "أرسل /search متبوعًا باسم الكتاب للبحث داخل قناة المكتبة المحددة."
    )

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("استخدم: /search اسم الكتاب أو المؤلف")
        return

    msg = await update.message.reply_text(f"🔍 أبحث عن **{query}** داخل المكتبة المحددة...")
    
    try:
        results = await search_telethon_channel(query)

        if isinstance(results, str) and results.startswith("ERROR_"):
             if results == "ERROR_ADMIN_REQUIRED":
                  await msg.edit_text("❌ خطأ: البوت ليس مشرفاً (Admin) في القناة المحددة.")
             elif results == "ERROR_INVALID_ID":
                 await msg.edit_text("❌ خطأ: معرف القناة غير صالح. تأكد من صحة @channelusername.")
             elif results == "ERROR_CLIENT_UNINITIALIZED":
                 await msg.edit_text("❌ خطأ تهيئة: فشل بدء تشغيل Telethon. تأكد من صحة API_ID/HASH.")
             else:
                  await msg.edit_text(f"⚠️ خطأ عام أثناء البحث: {results}")
             return

        if not results:
            await msg.edit_text("❌ لم يتم العثور على نتائج في المكتبة الداخلية. حاول بكلمات مختلفة.")
            return

        buttons = []
        text_lines = []
        
        context.user_data[TEMP_RESULTS_KEY] = results
        
        for i, item in enumerate(results, start=0):
            title = item.get("title")
            text_lines.append(f"{i+1}. {title}")
            buttons.append([InlineKeyboardButton(f"📥 تحميل {i+1}", callback_data=f"dl|{i}")])
            
        reply = "✅ تم العثور على الكتب التالية:\n" + "\n".join(text_lines)
        await msg.edit_text(reply, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
         await msg.edit_text(f"⚠️ حدث خطأ أثناء التشغيل: {e}")

# ----------------------------------------------------------------------
# --- دالة التشغيل الرئيسية (V18.2: تصحيح run_polling) ---
# ----------------------------------------------------------------------
async def main():
    if not BOT_TOKEN or not API_ID or not API_HASH:
        raise ValueError("يجب تحديد BOT_TOKEN, API_ID, و API_HASH كمتغيرات بيئة.")

    global telethon_client
    # إنشاء وربط Telethon بحلقة الحدث الحالية
    telethon_client = TelegramClient('bot_session', int(API_ID), API_HASH)
    
    try:
        await telethon_client.start(bot_token=BOT_TOKEN)
        print("Telethon client started successfully.")
    except Exception as e:
         raise Exception(f"فشل تشغيل Telethon. تحقق من API_ID و API_HASH: {e}")

    # تهيئة PTB
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("PTB is starting polling...")
    # 💥 V18.2: العودة إلى run_polling() المتوفرة في الإصدارات القديمة لديك.
    # بما أننا داخل دالة async، سنستخدم وظيفة asyncio.get_event_loop() لتشغيلها.
    # Note: run_polling is blocking, running it inside a future.
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, app.run_polling)
    
    # لجعل حلقة الأحداث مستمرة حتى تعمل polling
    while True:
        await asyncio.sleep(60) 

if __name__ == "__main__":
    try:
        # 🚨 V18.2: نقوم بتشغيل الدالة main غير المتزامنة
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error outside main: {e}")
