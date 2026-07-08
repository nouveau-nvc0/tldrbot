"""Help plugin."""
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from plugins import Plugin
import logging

logger = logging.getLogger(__name__)

HELP_TEMPLATE = """🙄 *Oh, you need help? Shocking.* Here's what I can do:

*Commands:*
• `/tldr [n]` — Summarize the last n messages (default: 50, max: 400)
• `/help` — You're looking at it, genius

*Auto Features:*
{auto_download_line}
• 💬 @ mention me and I'll grace you with a response

*Rate Limit:*
You get 10 AI requests per day. Use them wisely, or don't. I'll judge you either way.

_I'm here to help, but I reserve the right to be sarcastic about it._ ✨"""


class HelpPlugin(Plugin):
    def __init__(self, auto_download_enabled: bool = True):
        self.auto_download_enabled = auto_download_enabled

    @property
    def name(self) -> str:
        return "help"
    
    @property
    def commands(self):
        return [("help", "Get help (if you really need it)")]
    
    def register(self, app: Application) -> None:
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("start", self.help_command))
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return

        auto_download_line = (
            "• 🎬 Drop a TikTok/Reels/Shorts link and I'll download it for you"
            if self.auto_download_enabled
            else "• 🎬 Video auto-download is disabled"
        )
        
        await update.message.reply_text(
            HELP_TEMPLATE.format(auto_download_line=auto_download_line),
            parse_mode="Markdown"
        )
        logger.info(f"Help shown to user {update.effective_user.id if update.effective_user else 'unknown'}")

