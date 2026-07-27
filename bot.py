import os
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set!")
    exit(1)

# Store reminders
user_reminders = {}

def parse_time(text):
    text = text.lower().strip()
    now = datetime.now()
    
    if text.endswith('s') and text[:-1].isdigit():
        return now + timedelta(seconds=int(text[:-1]))
    elif text.endswith('m') and text[:-1].isdigit():
        return now + timedelta(minutes=int(text[:-1]))
    elif text.endswith('h') and text[:-1].isdigit():
        return now + timedelta(hours=int(text[:-1]))
    elif text.endswith('d') and text[:-1].isdigit():
        return now + timedelta(days=int(text[:-1]))
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Commands:\n"
        "/remind <time> <message> - Set reminder\n"
        "/list - View reminders\n"
        "/clear - Clear all\n\n"
        "Examples:\n"
        "/remind 10s Hello\n"
        "/remind 5m Call mom"
    )

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("❌ Use: /remind <time> <message>")
            return
        
        time_str = context.args[0]
        message = ' '.join(context.args[1:])
        
        remind_time = parse_time(time_str)
        if not remind_time:
            await update.message.reply_text("❌ Invalid time. Use: 10s, 5m, 2h, 1d")
            return
        
        if remind_time < datetime.now():
            await update.message.reply_text("❌ That time is in the past!")
            return
        
        user_id = update.effective_user.id
        
        if user_id not in user_reminders:
            user_reminders[user_id] = []
        
        reminder = {
            'time': remind_time,
            'message': message,
            'user_id': user_id
        }
        user_reminders[user_id].append(reminder)
        
        await update.message.reply_text(
            f"✅ Reminder set!\n"
            f"⏰ {remind_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📝 {message}"
        )
        
        delay = (remind_time - datetime.now()).total_seconds()
        asyncio.create_task(send_reminder(reminder, delay, context.bot))
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Error occurred")

async def send_reminder(reminder, delay, bot):
    try:
        await asyncio.sleep(delay)
        await bot.send_message(
            chat_id=reminder['user_id'],
            text=f"⏰ REMINDER!\n\n{reminder['message']}"
        )
        user_id = reminder['user_id']
        if user_id in user_reminders and reminder in user_reminders[user_id]:
            user_reminders[user_id].remove(reminder)
    except Exception as e:
        logger.error(f"Reminder error: {e}")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_reminders or not user_reminders[user_id]:
        await update.message.reply_text("📭 No reminders set.")
        return
    
    reminders = sorted(user_reminders[user_id], key=lambda x: x['time'])
    text = "📋 Your Reminders:\n\n"
    for i, r in enumerate(reminders, 1):
        text += f"{i}. {r['time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"   {r['message']}\n\n"
    
    await update.message.reply_text(text)

async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_reminders and user_reminders[user_id]:
        user_reminders[user_id] = []
        await update.message.reply_text("🗑️ All reminders cleared!")
    else:
        await update.message.reply_text("📭 No reminders to clear.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ Error occurred")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("clear", clear_all))
    app.add_error_handler(error_handler)
    
    logger.info("✅ Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
