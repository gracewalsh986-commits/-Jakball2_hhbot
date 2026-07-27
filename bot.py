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

# Store reminders in memory
user_reminders = {}

# --- Helper Functions ---
def parse_time_input(text):
    """Parse time input like '10m', '2h', '30s', '1d'"""
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
        [InlineKeyboardButton("🗑️ Clear All", callback_data='clear_all')],
        [InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "👋 Welcome to Reminder Bot!\n\n"
        "I can help you remember important things.\n\n"
        "Examples:\n"
        "• /remind 10m Call mom\n"
        "• /remind 2h Meeting with team\n"
        "• /remind 15:30 Take a break\n\n"
        "Use the buttons below or type /help for more info."
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *How to use Reminder Bot*\n\n"
        "*Set a reminder:*\n"
        "`/remind <time> <message>`\n\n"
        "*Time formats:*\n"
        "• `10s` - 10 seconds\n"
        "• `5m` - 5 minutes\n"
        "• `2h` - 2 hours\n"
        "• `1d` - 1 day\n"
        "• `15:30` - Today at 3:30 PM\n\n"
        "*Other commands:*\n"
        "• `/list` - View all reminders\n"
        "• `/clear` - Clear all reminders"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args or len(args) < 2:
            await update.message.reply_text(
                "❌ Please provide a time and message.\n"
                "Example: `/remind 10m Call mom`",
                parse_mode='Markdown'
            )
            return
        
        time_str = args[0]
        message = ' '.join(args[1:])
        
        reminder_time = parse_time_input(time_str)
        if not reminder_time:
            await update.message.reply_text(
                "❌ Invalid time format.\n"
                "Use: `10s`, `5m`, `2h`, `1d`, or `15:30`",
                parse_mode='Markdown'
            )
            return
        
        if reminder_time < datetime.now():
            await update.message.reply_text("❌ That time is in the past!")
            return
        
        user_id = update.effective_user.id
        
        if user_id not in user_reminders:
            user_reminders[user_id] = []
        
        reminder_data = {
            'time': reminder_time,
            'message': message,
            'user_id': user_id
        }
        user_reminders[user_id].append(reminder_data)
        
        await update.message.reply_text(
            f"✅ Reminder set!\n"
            f"⏰ Time: {format_reminder_time(reminder_time)}\n"
            f"📝 Message: {message}"
        )
        
        delay = (reminder_time - datetime.now()).total_seconds()
        asyncio.create_task(schedule_reminder(reminder_data, delay, context.bot))
        
    except Exception as e:
        logger.error(f"Error in set_reminder: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def schedule_reminder(reminder_data, delay, bot):
    try:
        await asyncio.sleep(delay)
        
        await bot.send_message(
            chat_id=reminder_data['user_id'],
            text=f"⏰ *REMINDER!*\n\n{reminder_data['message']}",
            parse_mode='Markdown'
        )
        
        user_id = reminder_data['user_id']
        if user_id in user_reminders and reminder_data in user_reminders[user_id]:
            user_reminders[user_id].remove(reminder_data)
            
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_reminders or not user_reminders[user_id]:
        await update.message.reply_text("📭 You have no reminders set.")
        return
    
    reminders = sorted(user_reminders[user_id], key=lambda x: x['time'])
    text = "📋 *Your Reminders:*\n\n"
    for i, reminder in enumerate(reminders, 1):
        text += f"{i}. ⏰ {format_reminder_time(reminder['time'])}\n"
        text += f"   📝 {reminder['message']}\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_reminders and user_reminders[user_id]:
        user_reminders[user_id] = []
        await update.message.reply_text("🗑️ All reminders cleared!")
    else:
        await update.message.reply_text("📭 You have no reminders to clear.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    if action == 'set_reminder':
        await query.edit_message_text(
            "📝 To set a reminder, use:\n"
            "`/remind <time> <message>`\n\n"
            "Examples:\n"
            "• `/remind 10m Call mom`\n"
            "• `/remind 2h Meeting`\n"
            "• `/remind 15:30 Take a break`",
            parse_mode='Markdown'
        )
    elif action == 'list_reminders':
        user_id = query.from_user.id
        if user_id not in user_reminders or not user_reminders[user_id]:
            await query.edit_message_text("📭 You have no reminders set.")
            return
        
        reminders = sorted(user_reminders[user_id], key=lambda x: x['time'])
        text = "📋 *Your Reminders:*\n\n"
        for i, reminder in enumerate(reminders, 1):
            text += f"{i}. ⏰ {format_reminder_time(reminder['time'])}\n"
            text += f"   📝 {reminder['message']}\n\n"
        await query.edit_message_text(text, parse_mode='Markdown')
        
    elif action == 'clear_all':
        user_id = query.from_user.id
        if user_id in user_reminders:
            user_reminders[user_id] = []
            await query.edit_message_text("🗑️ All reminders cleared!")
        else:
            await query.edit_message_text("📭 You have no reminders to clear.")
            
    elif action == 'help':
        await query.edit_message_text(
            "📖 *How to use Reminder Bot*\n\n"
            "*Set a reminder:*\n"
            "`/remind <time> <message>`\n\n"
            "*Time formats:*\n"
            "• `10s` - seconds\n"
            "• `5m` - minutes\n"
            "• `2h` - hours\n"
            "• `1d` - days\n"
            "• `15:30` - today at 3:30 PM",
            parse_mode='Markdown'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again later."
        )

# --- Main Function ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("remind", set_reminder))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("clear", clear_all))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
