# Telegram Reminder Bot

A simple Telegram bot that helps users set and manage reminders.

## Features

- ⏰ Set reminders with natural language
- 📋 View all active reminders
- 🗑️ Clear all reminders
- 📱 Interactive keyboard buttons
- ⚡ Fast and responsive

## Commands

- `/start` - Start the bot and show main menu
- `/help` - Show help information
- `/remind <time> <message>` - Set a reminder
- `/list` - View all your reminders
- `/clear` - Clear all reminders

## Time Formats

- `10s` - 10 seconds
- `5m` - 5 minutes
- `2h` - 2 hours
- `1d` - 1 day
- `15:30` - Today at 3:30 PM
- `2024-12-25 15:30` - Specific date and time

## Deployment

This bot is designed to be deployed on Railway:

1. Push this repository to GitHub
2. Create a new project on Railway
3. Connect your GitHub repository
4. Add `TELEGRAM_BOT_TOKEN` to environment variables
5. Deploy!

## Environment Variables

- `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather

## License

MIT
