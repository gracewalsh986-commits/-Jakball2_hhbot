import logging
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Configuration ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN set in environment variables")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store reminders
user_reminders = {}

# --- Helper Functions ---
def parse_time_input(text):
    """Parse time input like '10m', '2h', '30s'"""
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
    elif ':' in text:
        try:
            hour, minute = map(int, text.split(':'))
            return datetime(now.year, now.month, now.day, hour, minute)
        except:
            pass
    return None

def format_reminder_time(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⏰ Set Reminder", callback_data='set_reminder')],
        [InlineKeyboardButton("📋 My Reminders", callback_data='list_reminders')],
        [InlineKeyboardButton("🗑️ Clear All", callback_data='clear_all')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Welcome to Reminder Bot!\n\n"
        "Commands:\n"
        "/remind <time> <message> - Set a reminder\n"
        "/list - View your reminders\n"
        "/clear - Clear all reminders\n\n"
        "Examples:\n"
        "/remind 10m Call mom\n"
        "/remind 15:30 Take a break",
        reply_markup=reply_markup
    )

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: /remind <time> <message>\n"
                "Example: /remind 10m Call mom"
            )
            return
        
        time_str = context.args[0]
        message = ' '.join(context.args[1:])
        
        reminder_time = parse_time_input(time_str)
        if not reminder_time:
            await update.message.reply_text(
                "❌ Invalid time format.\n"
                "Use: 10s, 5m, 2h, 1d, or 15:30"
            )
            return
        
        if reminder_time < datetime.now():
            await update.message.reply_text("❌ That time is in the past!")
            return
        
        user_id = update.effective_user.id
        
        if user_id not in user_reminders:
            user_reminders[user_id] = []
        
        reminder = {
            'time': reminder_time,
            'message': message,
            'user_id': user_id
        }
        user_reminders[user_id].append(reminder)
        
        await update.message.reply_text(
            f"✅ Reminder set!\n"
            f"⏰ {format_reminder_time(reminder_time)}\n"
            f"📝 {message}"
        )
        
        delay = (reminder_time - datetime.now()).total_seconds()
        asyncio.create_task(send_reminder(reminder, delay, context.bot))
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Error setting reminder")

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
        logger.error(f"Error sending reminder: {e}")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_reminders or not user_reminders[user_id]:
        await update.message.reply_text("📭 No reminders set.")
        return
    
    reminders = sorted(user_reminders[user_id], key=lambda x: x['time'])
    text = "📋 Your Reminders:\n\n"
    for i, r in enumerate(reminders, 1):
        text += f"{i}. {format_reminder_time(r['time'])}\n"
        text += f"   {r['message']}\n\n"
    
    await update.message.reply_text(text)

async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_reminders and user_reminders[user_id]:
        user_reminders[user_id] = []
        await update.message.reply_text("🗑️ All reminders cleared!")
    else:
        await update.message.reply_text("📭 No reminders to clear.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    if action == 'set_reminder':
        await query.edit_message_text(
            "📝 To set a reminder:\n"
            "/remind <time> <message>\n\n"
            "Examples:\n"
            "/remind 10m Call mom\n"
            "/remind 2h Meeting\n"
            "/remind 15:30 Take a break"
        )
    elif action == 'list_reminders':
        user_id = query.from_user.id
        if user_id not in user_reminders or not user_reminders[user_id]:
            await query.edit_message_text("📭 No reminders set.")
            return
        
        reminders = sorted(user_reminders[user_id], key=lambda x: x['time'])
        text = "📋 Your Reminders:\n\n"
        for i, r in enumerate(reminders, 1):
            text += f"{i}. {format_reminder_time(r['time'])}\n"
            text += f"   {r['message']}\n\n"
        await query.edit_message_text(text)
        
    elif action == 'clear_all':
        user_id = query.from_user.id
        if user_id in user_reminders:
            user_reminders[user_id] = []
            await query.edit_message_text("🗑️ All reminders cleared!")
        else:
            await query.edit_message_text("📭 No reminders to clear.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ An error occurred.")

# --- Main ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("clear", clear_all))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
