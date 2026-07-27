import logging
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import pytz

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

# Store reminders in memory (will be lost on restart)
# Structure: {user_id: [{'time': datetime, 'message': str, 'chat_id': int}]}
user_reminders = {}

# --- Helper Functions ---
def parse_time_input(text):
    """Parse time input like '10m', '2h', '30s', '1d', or '2024-12-25 15:30'"""
    text = text.lower().strip()
    now = datetime.now()
    
    # Check for relative time (e.g., "10m", "2h", "30s", "1d")
    if text.endswith('s') and text[:-1].isdigit():
        seconds = int(text[:-1])
        return now + timedelta(seconds=seconds)
    elif text.endswith('m') and text[:-1].isdigit():
        minutes = int(text[:-1])
        return now + timedelta(minutes=minutes)
    elif text.endswith('h') and text[:-1].isdigit():
        hours = int(text[:-1])
        return now + timedelta(hours=hours)
    elif text.endswith('d') and text[:-1].isdigit():
        days = int(text[:-1])
        return now + timedelta(days=days)
    
    # Check for absolute date/time
    try:
        # Try formats: "2024-12-25 15:30" or "15:30" (today) or "12/25 15:30"
        if ' ' in text:
            parts = text.split(' ')
            if '-' in parts[0]:  # YYYY-MM-DD HH:MM
                date_part = parts[0]
                time_part = parts[1] if len(parts) > 1 else '00:00'
                year, month, day = map(int, date_part.split('-'))
                hour, minute = map(int, time_part.split(':'))
                return datetime(year, month, day, hour, minute)
            elif '/' in parts[0]:  # MM/DD HH:MM
                date_part = parts[0]
                time_part = parts[1] if len(parts) > 1 else '00:00'
                month, day = map(int, date_part.split('/'))
                year = now.year
                hour, minute = map(int, time_part.split(':'))
                return datetime(year, month, day, hour, minute)
        else:
            # Try just time "15:30" (today)
            if ':' in text:
                hour, minute = map(int, text.split(':'))
                return datetime(now.year, now.month, now.day, hour, minute)
    except:
        pass
    
    return None

def format_reminder_time(dt):
    """Format datetime for display"""
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
        "I can help you remember important things. Here's how:\n"
        "• /remind <time> <message> - Set a reminder\n"
        "• /list - View all your reminders\n"
        "• /clear - Clear all your reminders\n"
        "• /help - Show this help message\n\n"
        "Examples:\n"
        "• /remind 10m Call mom\n"
        "• /remind 2h Meeting with team\n"
        "• /remind 2024-12-25 15:30 Christmas party\n"
        "• /remind 15:30 Take a break"
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
        "• `15:30` - Today at 3:30 PM\n"
        "• `2024-12-25 15:30` - Specific date and time\n\n"
        "*Examples:*\n"
        "• `/remind 10m Call mom`\n"
        "• `/remind 2h Meeting`\n"
        "• `/remind 15:30 Take a break`\n\n"
        "*Other commands:*\n"
        "• `/list` - View all reminders\n"
        "• `/clear` - Clear all reminders"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get the command arguments
        args = context.args
        if not args or len(args) < 2:
            await update.message.reply_text(
                "❌ Please provide a time and message.\n"
                "Example: `/remind 10m Call mom`",
                parse_mode='Markdown'
            )
            return
        
        # First argument is time, rest is message
        time_str = args[0]
        message = ' '.join(args[1:])
        
        # Parse the time
        reminder_time = parse_time_input(time_str)
        if not reminder_time:
            await update.message.reply_text(
                "❌ Invalid time format.\n"
                "Use: `10s`, `5m`, `2h`, `1d`, `15:30`, or `2024-12-25 15:30`",
                parse_mode='Markdown'
            )
            return
        
        # Check if time is in the past
        if reminder_time < datetime.now():
            await update.message.reply_text("❌ That time is in the past!")
            return
        
        # Store the reminder
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if user_id not in user_reminders:
            user_reminders[user_id] = []
        
        reminder_data = {
            'time': reminder_time,
            'message': message,
            'chat_id': chat_id
        }
        user_reminders[user_id].append(reminder_data)
        
        # Confirm to user
        await update.message.reply_text(
            f"✅ Reminder set!\n"
            f"⏰ Time: {format_reminder_time(reminder_time)}\n"
            f"📝 Message: {message}"
        )
        
        # Calculate delay in seconds
        delay = (reminder_time - datetime.now()).total_seconds()
        
        # Schedule the reminder using asyncio
        asyncio.create_task(schedule_reminder(update.effective_user.id, reminder_data, delay, context.bot))
        
    except Exception as e:
        logger.error(f"Error in set_reminder: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def schedule_reminder(user_id, reminder_data, delay, bot):
    """Schedule a reminder using asyncio sleep"""
    try:
        await asyncio.sleep(delay)
        
        # Send the reminder
        await bot.send_message(
            chat_id=user_id,
            text=f"⏰ *REMINDER!*\n\n{reminder_data['message']}",
            parse_mode='Markdown'
        )
        
        # Remove the reminder from storage
        if user_id in user_reminders and reminder_data in user_reminders[user_id]:
            user_reminders[user_id].remove(reminder_data)
            
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_reminders or not user_reminders[user_id]:
        await update.message.reply_text("📭 You have no reminders set.")
        return
    
    # Sort reminders by time
    reminders = sorted(user_reminders[user_id], key=lambda x: x['time'])
    
    text = "📋 *Your Reminders:*\n\n"
    for i, reminder in enumerate(reminders, 1):
        time_str = format_reminder_time(reminder['time'])
        text += f"{i}. ⏰ {time_str}\n   📝 {reminder['message']}\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_reminders and user_reminders[user_id]:
        user_reminders[user_id] = []
        await update.message.reply_text("🗑️ All reminders cleared!")
    else:
        await update.message.reply_text("📭 You have no reminders to clear.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
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
            time_str = format_reminder_time(reminder['time'])
            text += f"{i}. ⏰ {time_str}\n   📝 {reminder['message']}\n\n"
        await query.edit_message_text(text, parse_mode='Markdown')
        
    elif action == 'clear_all':
        user_id = query.from_user.id
        if user_id in user_reminders:
            user_reminders[user_id] = []
            await query.edit_message_text("🗑️ All reminders cleared!")
        else:
            await query.edit_message_text("📭 You have no reminders to clear.")
            
    elif action == 'help':
        help_text = (
            "📖 *How to use Reminder Bot*\n\n"
            "*Set a reminder:*\n"
            "`/remind <time> <message>`\n\n"
            "*Time formats:*\n"
            "• `10s` - 10 seconds\n"
            "• `5m` - 5 minutes\n"
            "• `2h` - 2 hours\n"
            "• `1d` - 1 day\n"
            "• `15:30` - Today at 3:30 PM\n"
            "• `2024-12-25 15:30` - Specific date and time\n\n"
            "*Examples:*\n"
            "• `/remind 10m Call mom`\n"
            "• `/remind 2h Meeting`\n"
            "• `/remind 15:30 Take a break`"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again later."
        )

# --- Main Function ---
def main():
    """Start the bot"""
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("remind", set_reminder))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("clear", clear_all))
    
    # Add callback handler for buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
